"""Google Classroom → cohorts.

Classes are grouped into cohorts by the number in their name ("Cohort 102 · SQL Foundations"); the
course is the catalogue name found in the class name. Importing a cohort links all its classes;
a sync then mirrors students (matched by email), coursework, submissions, grades and material posts.
"""

import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone

from integrations import accounts
from integrations.classroom.base import ClassroomError, get_provider

from ..models import Assignment, ClassroomClass, ClassroomMaterial, Cohort, Course, Student, Submission
from .common import ServiceError

log = logging.getLogger(__name__)

COHORT_NUMBER = re.compile(r"\bcohort\s*#?\s*(\d{2,5})\b", re.IGNORECASE)
WEEK_IN_TOPIC = re.compile(r"\bweek\s*(\d{1,2})\b", re.IGNORECASE)
SUBMITTED = {"TURNED_IN", "RETURNED"}
LOCK_ID = 48151623  # PostgreSQL advisory lock shared by every process that syncs


def min_cohort() -> int:
    return settings.TMS["CLASSROOM_MIN_COHORT"]


def provider():
    account = accounts.require(accounts.ConnectedAccount.Purpose.CLASSROOM)
    return get_provider(), account


def course_for(class_name: str) -> str:
    """The catalogue course named in a class name (the longest match wins), or ''."""
    lowered = class_name.lower()
    matches = [name for name in Course.objects.values_list("name", flat=True) if name.lower() in lowered]
    return max(matches, key=len) if matches else ""


def describe(course: dict) -> dict | None:
    match = COHORT_NUMBER.search(course.get("name", ""))
    if not match:
        return None
    return {"number": int(match.group(1)), "course": course_for(course["name"])}


# --------------------------------------------------------------------------- listing and import
def list_classes() -> dict:
    """The connected account's classes, grouped by cohort (only cohorts from CLASSROOM_MIN_COHORT on)."""
    api, _ = provider()
    linked = dict(ClassroomClass.objects.values_list("external_id", "cohort__number"))
    on_site = set(Cohort.objects.values_list("number", flat=True))
    groups: dict[int, dict] = {}
    left_out = 0
    for c in api.list_courses():
        info = describe(c)
        if not info or info["number"] < min_cohort():
            left_out += 1
            continue
        group = groups.setdefault(
            info["number"],
            {
                "number": info["number"],
                "name": f"Cohort {info['number']}",
                "on_site": info["number"] in on_site,
                "classes": [],
            },
        )
        group["classes"].append(
            {
                "id": c["id"],
                "name": c["name"],
                "section": c.get("section", ""),
                "state": c.get("courseState", ""),
                "course": info["course"],
                "linked": c["id"] in linked,
            }
        )
    cohorts = sorted(groups.values(), key=lambda g: -g["number"])
    for g in cohorts:
        g["new_classes"] = sum(1 for c in g["classes"] if not c["linked"])
    return {"cohorts": cohorts, "min_cohort": min_cohort(), "left_out": left_out}


def import_cohort(number: int) -> tuple[Cohort, bool]:
    api, _ = provider()
    classes = [c for c in api.list_courses() if (describe(c) or {}).get("number") == number]
    if not classes:
        raise ServiceError(f"Classroom has no classes for cohort {number}.", status=404)
    states = {c.get("courseState") for c in classes}
    status = (
        Cohort.Status.RUNNING
        if "ACTIVE" in states
        else (Cohort.Status.UPCOMING if states == {"PROVISIONED"} else Cohort.Status.FINISHED)
    )
    cohort, created = Cohort.objects.get_or_create(
        number=number, defaults={"name": f"Cohort {number}", "source": Cohort.Source.CLASSROOM, "status": status}
    )
    for c in classes:
        ClassroomClass.objects.update_or_create(
            external_id=c["id"],
            defaults={
                "cohort": cohort,
                "name": c["name"],
                "section": c.get("section", ""),
                "state": c.get("courseState", ""),
                "course": course_for(c["name"]),
            },
        )
    sync_or_record(cohort)
    return cohort, created


# --------------------------------------------------------------------------- sync
def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _due(work: dict) -> datetime | None:
    d = work.get("dueDate")
    if not d:
        return None
    t = work.get("dueTime") or {}
    return datetime(
        d["year"], d["month"], d["day"], t.get("hours", 23), t.get("minutes", 59), tzinfo=timezone.get_fixed_timezone(0)
    )


def _week_from_date(cohort: Cohort, when: datetime | None) -> int | None:
    if not (cohort.start_date and when):
        return None
    return max(1, min(cohort.weeks_total, (when.date() - cohort.start_date).days // 7 + 1))


def _attachments(items: list[dict]) -> list[dict]:
    out = []
    for item in items or []:
        if "driveFile" in item:
            f = item["driveFile"].get("driveFile", item["driveFile"])
            out.append({"type": "file", "title": f.get("title", ""), "url": f.get("alternateLink", "")})
        elif "link" in item:
            out.append({"type": "link", "title": item["link"].get("title", ""), "url": item["link"].get("url", "")})
        elif "youtubeVideo" in item:
            v = item["youtubeVideo"]
            out.append({"type": "video", "title": v.get("title", ""), "url": v.get("alternateLink", "")})
        elif "form" in item:
            out.append({"type": "form", "title": item["form"].get("title", ""), "url": item["form"].get("formUrl", "")})
    return out


def _next_code(cohort: Cohort) -> str:
    taken = set(cohort.students.values_list("code", flat=True))
    n = 1
    while f"CL-{n:03d}" in taken:
        n += 1
    return f"CL-{n:03d}"


@transaction.atomic
def sync(cohort: Cohort, add_unmatched: bool = False) -> dict:
    """Mirror the cohort's Classroom classes. Work entered on the site is never overwritten.
    A cohort imported from Classroom takes its students from there; for other cohorts students
    Classroom has but the site does not are reported, and added only with `add_unmatched`."""
    add_unmatched = add_unmatched or cohort.source == Cohort.Source.CLASSROOM
    api, account = provider()
    with_materials = accounts.has_scope("classroom", accounts.MATERIALS_SCOPE)
    by_email = {s.email.lower(): s for s in cohort.students.all() if s.email}
    unmatched: dict[str, dict] = {}
    totals = defaultdict(int)
    latest_activity = None
    all_firsts: list[datetime] = []  # when week-1 work was posted: the start date of an imported cohort
    for cls in cohort.classroom_classes.all():
        cid = cls.external_id
        cls.teachers = [
            t["profile"]["name"]["fullName"]
            for t in api.list_teachers(cid)
            if t["profile"].get("emailAddress", "").lower() != account.email.lower()
        ]
        cls.save(update_fields=["teachers"])
        people = {}
        for entry in api.list_students(cid):
            email = entry["profile"].get("emailAddress", "").lower()
            name = entry["profile"]["name"]["fullName"]
            student = by_email.get(email)
            if not student and add_unmatched and email:
                student = Student.objects.create(cohort=cohort, code=_next_code(cohort), full_name=name, email=email)
                by_email[email] = student
            if not student:
                unmatched.setdefault(email, {"name": name, "email": email})
                continue
            changed = []
            if student.classroom_user_id != entry["userId"]:
                student.classroom_user_id = entry["userId"]
                changed.append("classroom_user_id")
            if cls.course and cls.course not in student.courses:
                student.courses = [*student.courses, cls.course]
                changed.append("courses")
            if changed:
                student.save(update_fields=changed)
            people[entry["userId"]] = student
        totals["students"] = len({s.pk for s in by_email.values()})

        weeks = {}
        for topic in api.list_topics(cid):
            m = WEEK_IN_TOPIC.search(topic.get("name", ""))
            if m:
                weeks[topic["topicId"]] = int(m.group(1))

        works, seen, firsts = {}, [], []
        for work in api.list_coursework(cid):
            if work.get("state", "PUBLISHED") != "PUBLISHED":
                continue
            due = _due(work)
            created = _parse_time(work.get("creationTime"))
            week = weeks.get(work.get("topicId")) or _week_from_date(cohort, due or created) or 1
            external_id = f"{cid}:{work['id']}"
            seen.append(external_id)
            max_points = float(work.get("maxPoints") or 10)
            assignment, _ = Assignment.objects.update_or_create(
                cohort=cohort,
                external_id=external_id,
                defaults={
                    "title": work.get("title", "")[:200],
                    "description": work.get("description", ""),
                    "week": week,
                    "course": cls.course,
                    "due_at": due,
                    "max_points": max_points,
                    "published": True,
                    "external_link": work.get("alternateLink", ""),
                    "kind": Assignment.Kind.PROJECT if max_points > 10 else Assignment.Kind.HOMEWORK,
                },
            )
            works[work["id"]] = assignment
            if week == 1 and created:
                firsts.append(created)
            latest_activity = max(
                filter(None, [latest_activity, created, _parse_time(work.get("updateTime"))]), default=None
            )
        Assignment.objects.filter(cohort=cohort, external_id__startswith=f"{cid}:").exclude(
            external_id__in=seen
        ).delete()
        totals["assignments"] += len(works)

        existing = {
            (s.assignment_id, s.student_id): s for s in Submission.objects.filter(assignment__in=works.values())
        }
        for sub in api.list_submissions(cid):
            assignment = works.get(sub.get("courseWorkId"))
            student = people.get(sub.get("userId"))
            if not (assignment and student):
                continue
            current = existing.get((assignment.pk, student.pk))
            if current and current.source != Submission.Source.CLASSROOM:
                continue  # handed in or graded on the site: the site wins
            state = sub.get("state", "")
            attachments = _attachments((sub.get("assignmentSubmission") or {}).get("attachments"))
            updated = _parse_time(sub.get("updateTime"))
            values = {
                "source": Submission.Source.CLASSROOM,
                "external_state": state,
                "late": bool(sub.get("late")),
                "submitted_at": updated if state in SUBMITTED else None,
                "link": (attachments[0]["url"] if attachments else sub.get("alternateLink", ""))[:500],
                "points": sub.get("assignedGrade") if state == "RETURNED" else None,
                "graded_at": updated if state == "RETURNED" and sub.get("assignedGrade") is not None else None,
            }
            Submission.objects.update_or_create(assignment=assignment, student=student, defaults=values)
            if state in SUBMITTED:
                totals["submitted"] += 1
                latest_activity = max(filter(None, [latest_activity, updated]), default=None)
            if values["points"] is not None:
                totals["graded"] += 1

        if with_materials:
            _sync_materials(api, cls, weeks)
        firsts += [m.posted_at for m in cls.materials.filter(week=1) if m.posted_at]
        all_firsts.extend(firsts)

    if not cohort.start_date and all_firsts:
        cohort.start_date = min(all_firsts).date()
    if cohort.source == Cohort.Source.CLASSROOM:
        cohort.status = _status(cohort, latest_activity)
    summary = {
        "students": totals["students"],
        "assignments": totals["assignments"],
        "submitted": totals["submitted"],
        "graded": totals["graded"],
        "unmatched": sorted(unmatched.values(), key=lambda x: x["name"]),
        "materials": with_materials,
        "error": "",
    }
    cohort.classroom_summary = summary
    cohort.classroom_synced_at = timezone.now()
    cohort.save(update_fields=["classroom_summary", "classroom_synced_at", "start_date", "status"])
    return summary


def _status(cohort: Cohort, latest_activity: datetime | None) -> str:
    states = set(cohort.classroom_classes.values_list("state", flat=True))
    if states and states <= {"PROVISIONED"}:
        return Cohort.Status.UPCOMING
    recent = latest_activity and latest_activity > timezone.now() - timedelta(
        days=settings.TMS["CLASSROOM_ACTIVE_DAYS"]
    )
    return Cohort.Status.RUNNING if "ACTIVE" in states and recent else Cohort.Status.FINISHED


def _sync_materials(api, cls: ClassroomClass, weeks: dict) -> None:
    keep = []
    for post in api.list_materials(cls.external_id):
        if post.get("state", "PUBLISHED") != "PUBLISHED":
            continue
        keep.append(post["id"])
        ClassroomMaterial.objects.update_or_create(
            classroom_class=cls,
            external_id=post["id"],
            defaults={
                "title": post.get("title", "")[:300],
                "description": post.get("description", ""),
                "topic": f"Week {weeks[post['topicId']]}" if post.get("topicId") in weeks else "",
                "week": weeks.get(post.get("topicId")),
                "attachments": _attachments(post.get("materials")),
                "link": post.get("alternateLink", "")[:500],
                "posted_at": _parse_time(post.get("creationTime")),
            },
        )
    cls.materials.exclude(external_id__in=keep).delete()


def sync_or_record(cohort: Cohort, add_unmatched: bool = False) -> dict:
    """sync(), but a failure is stored on the cohort (and returned) instead of raised."""
    try:
        return sync(cohort, add_unmatched)
    except (ClassroomError, accounts.IntegrationError, ServiceError) as exc:
        summary = {**(cohort.classroom_summary or {}), "error": str(exc)}
        Cohort.objects.filter(pk=cohort.pk).update(classroom_summary=summary)
        cohort.classroom_summary = summary
        return summary


def refresh_materials() -> int:
    """Material posts of every linked class, right after (re)connecting with the materials permission."""
    if not accounts.has_scope("classroom", accounts.MATERIALS_SCOPE):
        return 0
    try:
        api, _ = provider()
    except accounts.IntegrationError:
        return 0
    count = 0
    for cls in ClassroomClass.objects.all():
        weeks = {
            t["topicId"]: int(m.group(1))
            for t in api.list_topics(cls.external_id)
            if (m := WEEK_IN_TOPIC.search(t.get("name", "")))
        }
        _sync_materials(api, cls, weeks)
        count += 1
    return count


def week_courses(cohort: Cohort, week: int) -> list[tuple[str, int, list[str]]]:
    """[(course, course week, teachers)] with Classroom coursework or material posts in cohort week `week`."""
    weeks_by_course = defaultdict(set)
    for course, w in cohort.assignments.filter(published=True).exclude(course="").values_list("course", "week"):
        weeks_by_course[course].add(w)
    posts = ClassroomMaterial.objects.filter(classroom_class__cohort=cohort, week__isnull=False)
    for course, w in posts.exclude(classroom_class__course="").values_list("classroom_class__course", "week"):
        weeks_by_course[course].add(w)
    teachers = defaultdict(list)
    for cls in cohort.classroom_classes.all():
        teachers[cls.course] += [t for t in cls.teachers if t not in teachers[cls.course]]
    return [
        (course, len({w for w in ws if w <= week}), teachers.get(course, []))
        for course, ws in sorted(weeks_by_course.items())
        if week in ws
    ]


# --------------------------------------------------------------------------- scheduled work
def _locked(fn):
    """Run `fn` only in the process holding the advisory lock (PostgreSQL); elsewhere just run it."""
    if connection.vendor != "postgresql":
        return fn()
    with connection.cursor() as cur:
        cur.execute("SELECT pg_try_advisory_lock(%s)", [LOCK_ID])
        if not cur.fetchone()[0]:
            log.info("another process is syncing; skipped")
            return None
        try:
            return fn()
        finally:
            cur.execute("SELECT pg_advisory_unlock(%s)", [LOCK_ID])


def sync_due() -> list[int]:
    """Sync linked cohorts that are due: running ones every CLASSROOM_SYNC_MINUTES, others daily."""

    def run():
        now, done = timezone.now(), []
        every = timedelta(minutes=settings.TMS["CLASSROOM_SYNC_MINUTES"])
        for cohort in Cohort.objects.filter(classroom_classes__isnull=False).distinct():
            interval = every if cohort.status == Cohort.Status.RUNNING else timedelta(days=1)
            if cohort.classroom_synced_at and cohort.classroom_synced_at > now - interval:
                continue
            sync_or_record(cohort)
            done.append(cohort.number)
        return done

    return _locked(run) or []


def auto_import() -> list[int]:
    """Import every Classroom cohort (from CLASSROOM_MIN_COHORT on) that is not on the site yet."""

    def run():
        added = []
        for group in list_classes()["cohorts"]:
            if not group["on_site"]:
                import_cohort(group["number"])
                added.append(group["number"])
        return added

    return _locked(run) or []


def connected() -> bool:
    acc = accounts.account(accounts.ConnectedAccount.Purpose.CLASSROOM)
    return bool(acc and not acc.expired)
