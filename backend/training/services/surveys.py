"""Weekly surveys: built per cohort and week, sent as personal links, answered on a public form.

A survey has one block per course taught that week (an understanding question and a comment),
then rating grids for trainers, mentors and materials, and a free-text note. Each grid can ask
about its own week (``grid_weeks``), e.g. mentors of the previous week.
"""

from html import escape

from django.conf import settings
from django.core import signing
from django.db.models import Max

from integrations import email as mail
from integrations import whatsapp

from ..models import Cohort, Course, Lesson, MentoringSession, Student, Survey, SurveyInvite
from . import recipients
from .common import ServiceError, average

UNDERSTANDING = ["Not at all", "A little", "Partly", "Mostly", "Completely"]
AGREEMENT = ["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"]
NOT_APPLICABLE = "Did not work with them"
DEFAULT_MATERIALS = ["Slides", "Exercises", "Datasets"]
GRIDS = ("trainers", "mentors", "materials")
PREVIEW_SALT = "surveys.preview"
PREVIEW_DAYS = 14


# --------------------------------------------------------------------------- building
def default_title(cohort: Cohort, week: int) -> str:
    return f"{cohort.name} · Week {week} feedback"


def _course_week(cohort: Cohort, course: str, week: int) -> int:
    weeks = Lesson.objects.filter(cohort=cohort, course=course, week__lte=week).values_list("week", flat=True)
    return len(set(weeks)) or 1


def _blocks_for(course_name: str, course_week: int, trainer: str, week: int) -> list[dict]:
    course = Course.objects.filter(name=course_name).first()
    days = course.days_in_week(course_week) if course else []
    return [
        {"course": course_name, "course_week": course_week, "day": d, "trainer": trainer, "week": week}
        for d in (days or [0])
    ]


def draft(cohort: Cohort, week: int) -> dict:
    blocks, trainers = [], []
    lectures = Lesson.objects.filter(cohort=cohort, week=week, kind=Lesson.Kind.LECTURE).order_by("date", "start_time")
    seen = []
    for lesson in lectures:
        if lesson.course not in seen:
            seen.append(lesson.course)
            blocks += _blocks_for(lesson.course, _course_week(cohort, lesson.course, week), lesson.trainer, week)
            if lesson.trainer and lesson.trainer not in trainers:
                trainers.append(lesson.trainer)
    if not blocks:
        from .classroom import week_courses

        for course, course_week, teachers in week_courses(cohort, week):
            trainer = teachers[0] if teachers else ""
            blocks += _blocks_for(course, course_week, trainer, week)
            trainers += [t for t in teachers if t not in trainers]
    previous = Survey.objects.filter(cohort=cohort, week__lt=week).order_by("-week").first()
    if not blocks and previous:  # nothing scheduled yet: carry last survey forward a week
        for b in previous.blocks:
            course = Course.objects.filter(name=b["course"]).first()
            cw = min(b["course_week"] + 1, course.weeks if course else 52)
            if b.get("day", 0) in (0, 1):
                blocks += _blocks_for(b["course"], cw, b.get("trainer", ""), week)
        trainers = list(previous.trainers)
    if previous and previous.mentors:
        mentors = list(previous.mentors)
    else:
        mentors = sorted(set(MentoringSession.objects.filter(cohort=cohort).values_list("mentor", flat=True)))
        mentors = mentors or sorted(
            {m for m in Lesson.objects.filter(cohort=cohort).values_list("mentor", flat=True) if m}
        )
    return {
        "title": default_title(cohort, week),
        "blocks": blocks,
        "trainers": trainers,
        "mentors": mentors,
        "materials": list(DEFAULT_MATERIALS),
        "grid_weeks": {},
    }


def clean(data: dict) -> dict:
    """Validate a survey posted by the web app (shapes already checked by the serializer)."""
    blocks = []
    for b in data.get("blocks", [])[:16]:
        course = str(b.get("course", "")).strip()[:80]
        if not course:
            raise ServiceError("Every block needs a course.")
        try:
            block = {
                "course": course,
                "course_week": max(1, min(52, int(b.get("course_week") or 1))),
                "day": int(b.get("day") or 0),
                "trainer": str(b.get("trainer", "")).strip()[:120],
                "week": max(1, min(52, int(b.get("week") or 1))),
            }
        except (TypeError, ValueError) as exc:
            raise ServiceError("Invalid block.") from exc
        if block["day"] not in (0, 1, 2):
            raise ServiceError("Day must be 0, 1 or 2.")
        blocks.append(block)
    out = {"title": str(data.get("title", "")).strip()[:200], "blocks": blocks}
    if not out["title"]:
        raise ServiceError("The survey needs a title.")
    for grid in GRIDS:
        names = []
        for name in data.get(grid, []):
            name = str(name).strip()[:120]
            if name and name.lower() not in {n.lower() for n in names}:
                names.append(name)
        out[grid] = names[:20]
    weeks = data.get("grid_weeks") or {}
    out["grid_weeks"] = {k: max(1, min(52, int(v))) for k, v in weeks.items() if k in GRIDS and str(v).isdigit()}
    return out


def save(cohort: Cohort, week: int, data: dict, by: str) -> Survey:
    values = clean(data)
    survey, _ = Survey.objects.update_or_create(cohort=cohort, week=week, defaults={**values, "updated_by": by})
    return survey


# --------------------------------------------------------------------------- the form
def block_label(b: dict) -> str:
    label = b["course"] + (f" · Day {b['day']}" if b.get("day") else "")
    return label + (f" ({b['trainer']})" if b.get("trainer") else "")


def grid_week(survey: Survey, grid: str) -> int:
    return survey.grid_weeks.get(grid) or survey.week


def questions(survey: Survey) -> list[dict]:
    """The form in order: [{id, kind: choice | text | grid, text, required, options | rows + columns}]."""
    out = []
    for i, b in enumerate(survey.blocks):
        course = Course.objects.filter(name=b["course"]).first()
        of = f" of {course.weeks}" if course else ""
        out.append(
            {
                "id": f"b{i}",
                "kind": "choice",
                "required": True,
                "options": UNDERSTANDING,
                "text": f"Week {b['week']}: how well did you understand the {block_label(b)} topics "
                f"(course week {b['course_week']}{of})?",
            }
        )
        out.append(
            {
                "id": f"b{i}c",
                "kind": "text",
                "required": False,
                "text": f"Anything to add about {block_label(b)}? What worked, what should change?",
            }
        )
    texts = {
        "trainers": "Week {w}: the trainer explained the topics clearly, knew the subject well "
        "and kept the class engaged.",
        "mentors": "Week {w}: my mentor's support was helpful.",
        "materials": "Week {w}: these materials were useful and of good quality.",
    }
    for grid in GRIDS:
        rows = getattr(survey, grid)
        if rows:
            columns = AGREEMENT + ([NOT_APPLICABLE] if grid == "mentors" else [])
            out.append(
                {
                    "id": grid,
                    "kind": "grid",
                    "required": True,
                    "rows": rows,
                    "columns": columns,
                    "text": texts[grid].format(w=grid_week(survey, grid)),
                }
            )
    out.append(
        {
            "id": "notes",
            "kind": "text",
            "required": False,
            "text": "Anything else you would like the training team to know?",
        }
    )
    return out


def parse(survey: Survey, data) -> tuple[dict, list[str]]:
    """(answers, ids of unanswered required questions) from a submitted form (a QueryDict or dict)."""
    answers = {"blocks": [], "trainers": {}, "mentors": {}, "materials": {}, "notes": ""}
    missing = []
    for q in questions(survey):
        if q["kind"] == "choice":
            value = data.get(q["id"], "")
            if value not in q["options"]:
                missing.append(q["id"])
                value = ""
            answers["blocks"].append({"level": value, "comment": ""})
        elif q["kind"] == "text":
            text = str(data.get(q["id"], "")).strip()[:3000]
            if q["id"] == "notes":
                answers["notes"] = text
            elif answers["blocks"]:
                answers["blocks"][-1]["comment"] = text
        else:
            for idx, row in enumerate(q["rows"]):
                value = data.get(f"{q['id']}:{idx}", "")
                if value in q["columns"]:
                    answers[q["id"]][row] = value
                elif q["id"] not in missing:
                    missing.append(q["id"])
    return answers, missing


def _score(value: str, scale: list[str]) -> int | None:
    return scale.index(value) + 1 if value in scale else None


def scores(answers: dict) -> dict:
    return {
        "understanding": average(_score(b["level"], UNDERSTANDING) for b in answers.get("blocks", [])),
        "trainer_score": average(_score(v, AGREEMENT) for v in answers.get("trainers", {}).values()),
        "mentor_score": average(_score(v, AGREEMENT) for v in answers.get("mentors", {}).values()),
        "materials_score": average(_score(v, AGREEMENT) for v in answers.get("materials", {}).values()),
    }


# --------------------------------------------------------------------------- results
def _distribution(values: list[str], columns: list[str], scale: list[str]) -> dict:
    """Answer counts per column and the 1–5 average (answers outside `scale`, like "not applicable", don't score)."""
    return {"counts": [values.count(c) for c in columns], "average": average(_score(v, scale) for v in values)}


def results(survey: Survey) -> dict:
    responses = list(survey.responses.select_related("student"))
    blocks = []
    for i, b in enumerate(survey.blocks):
        levels, comments = [], []
        for r in responses:
            given = r.answers.get("blocks", [])
            if i < len(given):
                levels.append(given[i]["level"])
                if given[i].get("comment"):
                    comments.append({"name": r.student.full_name if r.student else "", "text": given[i]["comment"]})
        blocks.append(
            {"label": block_label(b), **_distribution(levels, UNDERSTANDING, UNDERSTANDING), "comments": comments}
        )
    grids = {}
    for grid in GRIDS:
        columns = AGREEMENT + ([NOT_APPLICABLE] if grid == "mentors" else [])
        grids[grid] = [
            {
                "label": row,
                **_distribution(
                    [r.answers.get(grid, {}).get(row) for r in responses if r.answers.get(grid, {}).get(row)],
                    columns,
                    AGREEMENT,
                ),
            }
            for row in getattr(survey, grid)
        ]
    invites = survey.invites.select_related("student", "response").exclude(sent_at=None)
    people = [
        {
            "id": inv.student_id,
            "name": inv.student.full_name,
            "sent_at": inv.sent_at,
            "channels": inv.channels,
            "answered_at": inv.response.submitted_at if hasattr(inv, "response") else None,
        }
        for inv in invites.order_by("student__full_name")
    ]
    return {
        "invited": len(people),
        "answered": sum(1 for p in people if p["answered_at"]),
        "blocks": blocks,
        **grids,
        "notes": [
            {"name": r.student.full_name if r.student else "", "text": r.answers["notes"]}
            for r in responses
            if r.answers.get("notes")
        ],
        "people": people,
    }


# --------------------------------------------------------------------------- links and sending
def public_url(token: str) -> str:
    return f"{settings.TMS['PUBLIC_BASE_URL']}/s/{token}/"


def preview_url(survey: Survey) -> str:
    return f"{settings.TMS['PUBLIC_BASE_URL']}/s/preview/{signing.dumps(survey.pk, salt=PREVIEW_SALT)}/"


def survey_from_preview(signature: str) -> Survey:
    try:
        pk = signing.loads(signature, salt=PREVIEW_SALT, max_age=PREVIEW_DAYS * 86400)
    except signing.BadSignature as exc:
        raise ServiceError("This preview link is invalid or has expired.", status=404) from exc
    return Survey.objects.select_related("cohort").get(pk=pk)


def invite(survey: Survey, student: Student) -> SurveyInvite:
    return SurveyInvite.objects.get_or_create(survey=survey, student=student)[0]


def payload(cohort: Cohort, week: int) -> dict:
    survey = Survey.objects.filter(cohort=cohort, week=week).first()
    body = (
        {
            "title": survey.title,
            "blocks": survey.blocks,
            "trainers": survey.trainers,
            "mentors": survey.mentors,
            "materials": survey.materials,
            "grid_weeks": survey.grid_weeks,
        }
        if survey
        else draft(cohort, week)
    )
    known_trainers = sorted(
        {t for t in Lesson.objects.values_list("trainer", flat=True) if t}
        | {t for s in Survey.objects.all() for t in s.trainers}
    )
    known_mentors = sorted(
        set(MentoringSession.objects.values_list("mentor", flat=True))
        | {m for s in Survey.objects.all() for m in s.mentors}
    )
    return {
        "cohort": cohort.number,
        "week": week,
        "saved": bool(survey),
        **body,
        "updated_at": survey.updated_at if survey else None,
        "updated_by": survey.updated_by if survey else "",
        "preview_url": preview_url(survey) if survey else "",
        "scales": {"understanding": UNDERSTANDING, "agreement": AGREEMENT, "not_applicable": NOT_APPLICABLE},
        "courses": [
            {"name": c.name, "weeks": c.weeks, "day_split": c.day_split, "split_weeks": c.split_weeks}
            for c in Course.objects.all()
        ],
        "known_trainers": known_trainers,
        "known_mentors": known_mentors,
        "default_materials": DEFAULT_MATERIALS,
        "results": results(survey) if survey else None,
    }


def _email(survey: Survey, to: str, name: str, link: str, test: bool = False) -> mail.Email:
    org = settings.TMS["ORG_NAME"]
    hello = f"Hi {name}," if name else "Hello,"
    intro = (
        "This is a preview: answers given through this link are not saved."
        if test
        else ("Please tell us how this week went. It takes about three minutes and helps us improve the course.")
    )
    text = f"{hello}\n\n{intro}\n\n{survey.title}\n{link}\n\nThank you!\n{org} training office"
    html = (
        f'<div style="font-family:system-ui,Segoe UI,Arial,sans-serif;color:#1E1B4B;max-width:560px">'
        f"<p>{escape(hello)}</p><p>{escape(intro)}</p>"
        f'<p><a href="{escape(link)}" style="display:inline-block;background:#4338CA;color:#fff;padding:10px 18px;'
        f'border-radius:8px;text-decoration:none;font-weight:600">Open the survey</a></p>'
        f'<p style="color:#64748B;font-size:13px">{escape(survey.title)}</p>'
        f"<p>Thank you!<br>{escape(org)} training office</p></div>"
    )
    subject = f"{'[Test] ' if test else ''}{survey.cohort.name}: week {survey.week} feedback survey"
    return mail.Email(to, subject, text, html)


def send(survey: Survey, channel: str, student_ids: list[int] | None = None, test_to: str = "") -> dict:
    context = f"survey:{survey.cohort.number}:{survey.week}"
    if channel == "email" and not mail.ready():
        raise ServiceError("Connect the sender mailbox first.")
    if channel == "whatsapp" and not whatsapp.ready():
        raise ServiceError("WhatsApp is not available.")
    if channel not in ("email", "whatsapp"):
        raise ServiceError("Unknown channel.")
    if test_to:
        link = preview_url(survey)
        if channel == "email":
            sent, failed = mail.send_many([_email(survey, test_to, "", link, test=True)], context=context + ":test")
        else:
            sent, failed = whatsapp.send_many(
                [(test_to, test_to, ["there", survey.title, link])], "survey_invite", context=context + ":test"
            )
        return {"sent": sent, "failed": failed}
    people = recipients.students(student_ids or [], channel)
    if not people:
        raise ServiceError("Choose at least one student who can be reached on this channel.")
    invites = {s.id: invite(survey, s) for s in people}
    if channel == "email":
        messages = [_email(survey, s.email, s.first_name, public_url(invites[s.id].token)) for s in people]
        sent, failed = mail.send_many(messages, context=context)
    else:
        sent, failed = whatsapp.send_many(
            [(s.full_name, s.phone, [s.first_name, survey.title, public_url(invites[s.id].token)]) for s in people],
            "survey_invite",
            context=context,
        )
    failed_to = {f["to"] for f in failed}
    for s in people:
        if (s.email if channel == "email" else s.full_name) not in failed_to:
            inv = invites[s.id]
            inv.add_channel(channel)
            inv.save(update_fields=["channels", "sent_at"])
    return {"sent": sent, "failed": failed}


def latest_week(cohort: Cohort) -> int | None:
    return Survey.objects.filter(cohort=cohort).aggregate(w=Max("week"))["w"]
