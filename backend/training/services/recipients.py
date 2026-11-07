"""Who can receive a message on a channel: every cohort with its active students that have an
email address (or a phone number for WhatsApp)."""

from ..models import Cohort, Student


def address(student: Student, channel: str) -> str:
    return student.email if channel == "email" else student.phone


def by_cohort(channel: str) -> list[dict]:
    out = []
    for cohort in Cohort.objects.prefetch_related("students"):
        people = [
            {"id": s.id, "name": s.full_name, "to": address(s, channel)}
            for s in cohort.students.all()
            if not s.dropped and address(s, channel)
        ]
        out.append({"number": cohort.number, "name": cohort.name, "status": cohort.status, "people": people})
    return out


def students(ids: list[int], channel: str) -> list[Student]:
    return [
        s for s in Student.objects.filter(pk__in=ids, dropped=False).select_related("cohort") if address(s, channel)
    ]
