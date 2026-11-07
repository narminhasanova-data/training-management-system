"""Training materials: each course's Classroom material posts, opened from the web app and emailed
to chosen students of a cohort.

Courses are taught with the same materials in every cohort, so the list shown is the fullest set
among all cohorts. For the chosen cohort each item is that cohort's own copy when its class has one
(its students can open those files); items only another cohort has are flagged."""

from collections import defaultdict
from html import escape

from django.conf import settings

from integrations import accounts
from integrations import email as mail

from ..models import ClassroomClass, ClassroomMaterial, Cohort, Course
from . import recipients
from .common import ServiceError

TYPE_LABELS = {"file": "File", "link": "Link", "video": "Video", "form": "Form"}


def _key(title: str) -> str:
    return " ".join(title.lower().split())


def _unique(materials) -> list[ClassroomMaterial]:
    seen, out = set(), []
    for m in materials:
        if _key(m.title) not in seen:
            seen.add(_key(m.title))
            out.append(m)
    return out


def sets_by_cohort(course: str) -> dict[int, list[ClassroomMaterial]]:
    by_cohort = defaultdict(list)
    query = ClassroomMaterial.objects.filter(classroom_class__course=course).select_related("classroom_class__cohort")
    for m in query.order_by("week", "posted_at", "id"):
        by_cohort[m.classroom_class.cohort.number].append(m)
    return {n: _unique(ms) for n, ms in by_cohort.items()}


def courses() -> list[dict]:
    names = list(Course.objects.values_list("name", flat=True))
    names += sorted(set(ClassroomClass.objects.exclude(course="").values_list("course", flat=True)) - set(names))
    return [{"name": n, "count": max((len(ms) for ms in sets_by_cohort(n).values()), default=0)} for n in names]


def _item(m: ClassroomMaterial, from_other: bool) -> dict:
    return {
        "id": m.pk,
        "title": m.title,
        "description": m.description,
        "topic": m.topic,
        "week": m.week,
        "attachments": m.attachments,
        "link": m.link,
        "cohort": m.classroom_class.cohort.number,
        "from_other_cohort": from_other,
    }


def listing(course: str, cohort_number: int | None) -> dict:
    sets = sets_by_cohort(course)
    if not sets:
        return {"course": course, "source": None, "items": []}
    fullest = max(sets, key=lambda n: (len(sets[n]), n))
    own = {_key(m.title): m for m in sets.get(cohort_number, [])} if cohort_number else {}
    items = []
    for m in sets[fullest]:
        mine = own.pop(_key(m.title), None)
        items.append(_item(mine or m, from_other=bool(cohort_number) and not mine and fullest != cohort_number))
    items += [_item(m, from_other=False) for m in own.values()]
    return {"course": course, "source": {"number": fullest, "name": f"Cohort {fullest}"}, "items": items}


def payload(course: str, cohort_number: int | None) -> dict:
    all_courses = courses()
    course = course or next(
        (c["name"] for c in all_courses if c["count"]), all_courses[0]["name"] if all_courses else ""
    )
    return {
        "courses": all_courses,
        "materials_permission": accounts.has_scope("classroom", accounts.MATERIALS_SCOPE),
        "mail_ready": mail.ready(),
        **listing(course, cohort_number),
    }


def _email(course: str, cohort: Cohort, items: list[dict], to: str, name: str, test: bool) -> mail.Email:
    org = settings.TMS["ORG_NAME"]
    hello = f"Hi {name}," if name else "Hello,"
    subject = f"{'[Test] ' if test else ''}{course} materials · {cohort.name}"
    groups = defaultdict(list)
    for item in items:
        groups[item["topic"] or (f"Week {item['week']}" if item["week"] else "Materials")].append(item)
    text, html = [hello, "", f"Here are the {course} materials.", ""], []
    for topic, entries in groups.items():
        text.append(topic.upper())
        html.append(f'<p style="margin:18px 0 6px;font-weight:700;color:#4338CA">{escape(topic)}</p>')
        for item in entries:
            text.append(f"- {item['title']}")
            links = []
            for a in item["attachments"]:
                if a.get("url"):
                    text.append(f"    {a.get('title') or ''} {a['url']}".rstrip())
                    links.append(
                        f'<div><a href="{escape(a["url"])}">{escape(a.get("title") or a["url"])}</a>'
                        f' <span style="color:#64748B">· {TYPE_LABELS.get(a.get("type"), "Link")}</span></div>'
                    )
            html.append(
                f'<div style="background:#F8FAFC;border-radius:8px;padding:10px 12px;margin-bottom:6px">'
                f"<b>{escape(item['title'])}</b>{''.join(links)}</div>"
            )
        text.append("")
    text += ["If a file does not open, sign in with the account you use for class.", "", f"{org} training office"]
    body = (
        f'<div style="font-family:system-ui,Segoe UI,Arial,sans-serif;color:#1E1B4B;max-width:620px">'
        f"<p>{escape(hello)}<br>Here are the {escape(course)} materials.</p>{''.join(html)}"
        f'<p style="color:#64748B;font-size:13px">'
        f"If a file does not open, sign in with the account you use for class.</p>"
        f"<p>{escape(org)} training office</p></div>"
    )
    return mail.Email(to, subject, "\n".join(text), body)


def send(
    course: str, cohort: Cohort, material_ids: list[int], student_ids: list[int] | None = None, test_to: str = ""
) -> dict:
    if not mail.ready():
        raise ServiceError("Connect the sender mailbox first.")
    wanted = set(material_ids)
    items = [i for i in listing(course, cohort.number)["items"] if i["id"] in wanted]
    if not items:
        raise ServiceError("Choose at least one material.")
    context = f"materials:{cohort.number}:{course}"
    if test_to:
        sent, failed = mail.send_many([_email(course, cohort, items, test_to, "", True)], context=context + ":test")
        return {"sent": sent, "failed": failed}
    people = recipients.students(student_ids or [], "email")
    if not people:
        raise ServiceError("Choose at least one student with an email address.")
    sent, failed = mail.send_many(
        [_email(course, cohort, items, s.email, s.first_name, False) for s in people], context=context
    )
    return {"sent": sent, "failed": failed}
