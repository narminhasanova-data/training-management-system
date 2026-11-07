"""Agendas: the timetable students receive for a teaching week, a midterm, a final or a career day.

A day is ``{"heading"?, "date", "free", "tracks": [{"course", "color"}], "rows": [{"time", "text", "track"}]}``.
Teaching days follow a fixed slot template with a morning and an afternoon course ("tracks");
"free" days (exams, career day, the week's optional extra section) have typed-in times and rows
that can be added or removed.
"""

from datetime import date, timedelta
from html import escape

from django.conf import settings
from django.utils import timezone

from integrations import email as mail
from integrations import whatsapp

from ..models import PALETTE, Agenda, Cohort, Course, Lesson, Week
from . import recipients
from .common import ServiceError

KINDS = [k.value for k in Agenda.Kind]
CLASS_DAYS = 2
BREAK, LUNCH = "Break", "Lunch break"
# (time, track index or None for a pause, fixed text for pauses)
WEEK_SLOTS = [
    ("09:30–10:20", 0, ""),
    ("10:20–10:30", None, BREAK),
    ("10:30–11:20", 0, ""),
    ("11:20–11:30", None, BREAK),
    ("11:30–12:20", 0, ""),
    ("12:20–13:20", None, LUNCH),
    ("13:20–14:10", 1, ""),
    ("14:10–14:20", None, BREAK),
    ("14:20–15:10", 1, ""),
    ("15:10–15:20", None, BREAK),
    ("15:20–16:10", 1, ""),
]
FREE_TEMPLATES = {
    "midterm": [("amber", [("", ""), ("15 min", BREAK), ("", "")]), ("sky", [("", ""), ("15 min", BREAK), ("", "")])],
    "final": [(c, [("", ""), ("15 min", BREAK), ("", "")]) for c in ("amber", "rose", "sky")],
    "career": [(c, [("", ""), ("10 min", BREAK), ("", ""), ("10 min", BREAK), ("", "")]) for c in ("indigo", "lime")],
}
EXTRA_SECTION = [("", ""), ("10 min", BREAK), ("", "")]
TITLES = {
    "week": "Week {week} timetable",
    "midterm": "Midterm exam schedule",
    "final": "Final exam schedule",
    "career": "Career day schedule",
}
PRACTICE_ROWS = ["Guided practice", "Case study in small groups", "Homework review and Q&A"]
FILLERS = {"", BREAK, LUNCH}
LIMITS = {"days": 8, "rows": 24, "text": 240, "time": 24, "heading": 120}


def title(agenda_or_kind, week: int | None = None) -> str:
    kind = agenda_or_kind.kind if isinstance(agenda_or_kind, Agenda) else agenda_or_kind
    week = agenda_or_kind.week if isinstance(agenda_or_kind, Agenda) else week
    return TITLES[kind].format(week=week)


def course_color(name: str) -> str:
    position = Course.objects.filter(name=name).values_list("position", flat=True).first()
    return PALETTE[(position or 0) % len(PALETTE)]


def _template_day(day_date: date | None, courses: list[str], texts: list[list[str]]) -> dict:
    tracks = [{"course": c, "color": course_color(c)} for c in courses[:2]]
    while len(tracks) < 2:
        tracks.append({"course": "", "color": PALETTE[len(tracks) + 1]})
    rows, filled = [], [0, 0]
    for time_label, track, fixed in WEEK_SLOTS:
        if track is None:
            rows.append({"time": time_label, "text": fixed, "track": None})
            continue
        slots = sum(1 for _, t, _ in WEEK_SLOTS if t == track)
        source = texts[track] if track < len(texts) else []
        i = filled[track]
        if i < slots - 1:
            text = source[i] if i < len(source) else ""
        else:  # the last slot of a track takes everything left
            text = "; ".join(source[i:])
        filled[track] += 1
        rows.append({"time": time_label, "text": text, "track": track})
    return {"date": day_date.isoformat() if day_date else "", "free": False, "tracks": tracks, "rows": rows}


def _free_day(color: str, rows: list[tuple[str, str]], heading: str | None = None) -> dict:
    day = {
        "date": "",
        "free": True,
        "tracks": [{"course": "", "color": color}],
        "rows": [{"time": t, "text": x, "track": 0} for t, x in rows],
    }
    if heading is not None:
        day["heading"] = heading
    return day


def _class_dates(cohort: Cohort, week: int, lessons: list[Lesson]) -> list[date | None]:
    dates = sorted({lesson.date for lesson in lessons if lesson.date})[:CLASS_DAYS]
    if cohort.start_date:
        first = cohort.start_date + timedelta(weeks=week - 1)
        while len(dates) < CLASS_DAYS:
            dates.append(first + timedelta(days=len(dates)))
    return dates + [None] * (CLASS_DAYS - len(dates))


def draft(cohort: Cohort, week: int, kind: str) -> list[dict]:
    """A new agenda, prefilled from the week's lessons and topics (or from Classroom coursework)."""
    if kind != "week":
        return [_free_day(color, rows) for color, rows in FREE_TEMPLATES[kind]]
    lessons = list(Lesson.objects.filter(cohort=cohort, week=week).order_by("date", "start_time"))
    topics = (Week.objects.filter(cohort=cohort, number=week).values_list("topics", flat=True).first()) or {}
    days = []
    for i, day_date in enumerate(_class_dates(cohort, week, lessons)):
        todays = [x for x in lessons if x.date == day_date] if day_date else []
        if not lessons:  # no timetable yet: the courses Classroom has work for this week
            from .classroom import week_courses

            todays_courses = [c for c, _, _ in week_courses(cohort, week)]
            kinds = ["lecture" if i == 0 else "practice"] * len(todays_courses)
        else:
            seen = {}
            for x in todays:
                seen.setdefault(x.course, x.kind)
            todays_courses, kinds = list(seen), list(seen.values())
        texts = [
            list(topics.get(c, [])) if k == "lecture" else list(PRACTICE_ROWS)
            for c, k in zip(todays_courses, kinds, strict=True)
        ]
        days.append(_template_day(day_date, todays_courses, texts))
    days.append(_free_day("lime", EXTRA_SECTION, heading=""))
    days.append(_free_day("lime", EXTRA_SECTION))
    return days


def _text(value, limit) -> str:
    return str(value or "").strip()[:limit]


def clean(days) -> list[dict]:
    """Validate an agenda posted by the web app and keep only known fields."""
    if not isinstance(days, list) or not days or len(days) > LIMITS["days"]:
        raise ServiceError("An agenda needs between 1 and 8 days.")
    out = []
    for day in days:
        if not isinstance(day, dict):
            raise ServiceError("Invalid day.")
        day_date = _text(day.get("date"), 10)
        if day_date:
            try:
                date.fromisoformat(day_date)
            except ValueError as exc:
                raise ServiceError(f"Invalid date: {day_date}") from exc
        tracks = []
        for t in (day.get("tracks") or [])[:3]:
            color = t.get("color") if t.get("color") in PALETTE else PALETTE[0]
            tracks.append({"course": _text(t.get("course"), 80), "color": color})
        rows = []
        for r in (day.get("rows") or [])[: LIMITS["rows"]]:
            track = r.get("track")
            rows.append(
                {
                    "time": _text(r.get("time"), LIMITS["time"]),
                    "text": _text(r.get("text"), LIMITS["text"]),
                    "track": track if isinstance(track, int) and 0 <= track < len(tracks) else None,
                }
            )
        cleaned = {"date": day_date, "free": bool(day.get("free")), "tracks": tracks, "rows": rows}
        if "heading" in day:
            cleaned["heading"] = _text(day.get("heading"), LIMITS["heading"])
        out.append(cleaned)
    return out


def get(cohort: Cohort, week: int, kind: str) -> Agenda | None:
    return Agenda.objects.filter(cohort=cohort, week=week, kind=kind).first()


def payload(cohort: Cohort, week: int, kind: str) -> dict:
    agenda = get(cohort, week, kind)
    return {
        "cohort": cohort.number,
        "week": week,
        "kind": kind,
        "title": title(kind, week),
        "saved": bool(agenda),
        "days": agenda.days if agenda else draft(cohort, week, kind),
        "updated_at": agenda.updated_at if agenda else None,
        "updated_by": agenda.updated_by if agenda else "",
        "emailed_at": agenda.emailed_at if agenda else None,
        "emailed_count": agenda.emailed_count if agenda else 0,
        "whatsapp_at": agenda.whatsapp_at if agenda else None,
        "whatsapp_count": agenda.whatsapp_count if agenda else 0,
    }


def save(cohort: Cohort, week: int, kind: str, days, by: str) -> Agenda:
    agenda, _ = Agenda.objects.update_or_create(
        cohort=cohort, week=week, kind=kind, defaults={"days": clean(days), "updated_by": by}
    )
    return agenda


# --------------------------------------------------------------------------- output
def shown_days(agenda: Agenda) -> list[dict]:
    """Days worth sending: a day without a date and without real content is left out (its heading
    moves to the next day that is shown)."""
    out, pending_heading = [], ""
    for day in agenda.days:
        has_content = any(r["text"] not in FILLERS for r in day["rows"])
        if not day["date"] and not has_content:
            pending_heading = pending_heading or day.get("heading", "")
            continue
        day = dict(day)
        if pending_heading and not day.get("heading"):
            day["heading"] = pending_heading
        pending_heading = ""
        out.append(day)
    return out


def day_label(value: str) -> str:
    if not value:
        return ""
    d = date.fromisoformat(value)
    return d.strftime("%A, %-d %B %Y")


def _email(agenda: Agenda, name: str) -> tuple[str, str, str]:
    cohort, label = agenda.cohort, title(agenda)
    subject = f"{cohort.name}: {label}"
    hello = f"Hi {name}," if name else "Hello,"
    text_lines = [hello, "", f"Here is the {label.lower()} for {cohort.name}. The PDF is attached.", ""]
    html_days = []
    for day in shown_days(agenda):
        if day.get("heading"):
            text_lines.append(day["heading"].upper())
            html_days.append(f'<h3 style="margin:20px 0 6px;font-size:15px">{escape(day["heading"])}</h3>')
        text_lines.append(day_label(day["date"]) or "Date to be confirmed")
        rows_html = []
        for r in day["rows"]:
            if not r["time"] and not r["text"]:
                continue
            course = day["tracks"][r["track"]]["course"] if r["track"] is not None and day["tracks"] else ""
            text_lines.append(f"  {r['time']:<14} {r['text']}{f' ({course})' if course else ''}")
            rows_html.append(
                f'<tr><td style="padding:6px 10px;color:#475569;white-space:nowrap">{escape(r["time"])}</td>'
                f'<td style="padding:6px 10px">{escape(r["text"])}'
                f"{f' <span style=color:#64748B>· {escape(course)}</span>' if course else ''}</td></tr>"
            )
        text_lines.append("")
        html_days.append(
            f'<p style="margin:16px 0 6px;font-weight:600">'
            f"{escape(day_label(day['date']) or 'Date to be confirmed')}</p>"
            f'<table style="border-collapse:collapse;width:100%;font-size:14px;background:#F8FAFC">'
            f"{''.join(rows_html)}</table>"
        )
    org = settings.TMS["ORG_NAME"]
    text_lines += ["See you in class!", f"{org} training office"]
    html = (
        f'<div style="font-family:system-ui,Segoe UI,Arial,sans-serif;color:#1E1B4B;max-width:640px">'
        f'<p style="font-size:12px;letter-spacing:.08em;color:#4338CA;font-weight:700">{escape(org.upper())}</p>'
        f'<h2 style="margin:0 0 8px">{escape(label)}</h2><p>{escape(hello)}<br>'
        f"Here is the {escape(label.lower())} for {escape(cohort.name)}. The PDF is attached.</p>"
        f'{"".join(html_days)}<p style="margin-top:20px">See you in class!<br>{escape(org)} training office</p></div>'
    )
    return subject, "\n".join(text_lines), html


def send(agenda: Agenda, channel: str, student_ids: list[int] | None = None, test_to: str = "") -> dict:
    from .agenda_pdf import filename, render

    if not shown_days(agenda):
        raise ServiceError("The agenda is empty. Add a date or some content first.")
    pdf = render(agenda)
    name = filename(agenda)
    context = f"agenda:{agenda.cohort.number}:{agenda.week}:{agenda.kind}"
    if channel == "email":
        if not mail.ready():
            raise ServiceError("Connect the sender mailbox first.")
        if test_to:
            subject, text, html = _email(agenda, "")
            return _result(
                *mail.send_many(
                    [mail.Email(test_to, "[Test] " + subject, text, html, [(name, pdf, "application/pdf")])],
                    context=context + ":test",
                )
            )
        people = recipients.students(student_ids or [], "email")
        messages = []
        for s in people:
            subject, text, html = _email(agenda, s.first_name)
            messages.append(mail.Email(s.email, subject, text, html, [(name, pdf, "application/pdf")]))
        sent, failed = mail.send_many(messages, context=context)
        if sent:
            agenda.emailed_at, agenda.emailed_count = timezone.now(), sent
            agenda.save(update_fields=["emailed_at", "emailed_count"])
        return _result(sent, failed)
    if channel == "whatsapp":
        if not whatsapp.ready():
            raise ServiceError("WhatsApp is not available.")
        document = whatsapp.Document(name, pdf)
        label = title(agenda)
        if test_to:
            return _result(
                *whatsapp.send_many(
                    [(test_to, test_to, ["there", label, agenda.cohort.name])],
                    "agenda_notice",
                    document,
                    context + ":test",
                )
            )
        people = recipients.students(student_ids or [], "whatsapp")
        sent, failed = whatsapp.send_many(
            [(s.full_name, s.phone, [s.first_name, label, agenda.cohort.name]) for s in people],
            "agenda_notice",
            document,
            context,
        )
        if sent:
            agenda.whatsapp_at, agenda.whatsapp_count = timezone.now(), sent
            agenda.save(update_fields=["whatsapp_at", "whatsapp_count"])
        return _result(sent, failed)
    raise ServiceError("Unknown channel.")


def _result(sent: int, failed: list[dict]) -> dict:
    return {"sent": sent, "failed": failed}
