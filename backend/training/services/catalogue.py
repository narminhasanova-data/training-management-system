"""The course catalogue (agenda modules and survey blocks)."""

from django.db import transaction

from ..models import Course
from .common import ServiceError


def as_list() -> list[dict]:
    return [
        {
            "id": c.id,
            "name": c.name,
            "weeks": c.weeks,
            "day_split": c.day_split,
            "split_weeks": c.split_weeks,
            "position": c.position,
        }
        for c in Course.objects.all()
    ]


def names() -> list[str]:
    return list(Course.objects.values_list("name", flat=True))


@transaction.atomic
def replace(rows: list[dict]) -> list[dict]:
    """Make the catalogue exactly `rows` (validated by the serializer), keeping ids of rows that have one."""
    seen = set()
    for row in rows:
        key = row["name"].strip().lower()
        if key in seen:
            raise ServiceError(f"“{row['name']}” appears twice.")
        seen.add(key)
    keep = []
    for position, row in enumerate(rows):
        split_weeks = sorted({w for w in row.get("split_weeks", []) if 1 <= w <= row["weeks"]})
        values = {
            "name": row["name"].strip(),
            "weeks": row["weeks"],
            "day_split": row["day_split"],
            "split_weeks": split_weeks if row["day_split"] == Course.DaySplit.SOME else [],
            "position": position,
        }
        course = Course.objects.filter(pk=row.get("id")).first() if row.get("id") else None
        if course:
            for k, v in values.items():
                setattr(course, k, v)
            course.save()
        else:
            course = Course.objects.create(**values)
        keep.append(course.pk)
    Course.objects.exclude(pk__in=keep).delete()
    return as_list()
