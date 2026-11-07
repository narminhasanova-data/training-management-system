"""Gradebook: every student of a cohort against every published assignment."""

from django.db.models import Q
from django.utils import timezone

from ..models import Cohort, Submission
from .common import average


def build(cohort: Cohort, week: int | None = None) -> dict:
    published = cohort.assignments.filter(published=True)
    weeks = sorted(set(published.values_list("week", flat=True)))
    assignments = list(published.filter(week=week) if week else published)
    due_ids = {a.pk for a in assignments if a.due_at is None or a.due_at <= timezone.now()}
    subs = {(s.assignment_id, s.student_id): s for s in Submission.objects.filter(assignment__in=assignments)}
    people = []
    for student in cohort.students.order_by("dropped", "code"):
        cells, done, pcts = {}, 0, []
        for a in assignments:
            s = subs.get((a.pk, student.pk))
            status = s.status if s else "missing"
            pct = round(100 * s.points / a.max_points, 1) if s and s.points is not None and a.max_points else None
            cells[str(a.pk)] = {
                "status": status,
                "points": s.points if s else None,
                "percent": pct,
                "late": bool(s and s.late),
                "link": (s.link if s else "") or "",
            }
            if status != "missing" and a.pk in due_ids:
                done += 1
            if pct is not None:
                pcts.append(pct)
        people.append(
            {
                "id": student.pk,
                "code": student.code,
                "name": student.full_name,
                "email": student.email,
                "courses": student.courses,
                "dropped": student.dropped,
                "cells": cells,
                "done": done,
                "due": len(due_ids),
                "average": average(pcts),
            }
        )
    return {
        "cohort": {
            "number": cohort.number,
            "name": cohort.name,
            "classroom_linked": cohort.classroom_classes.exists(),
            "classroom_synced_at": cohort.classroom_synced_at,
        },
        "weeks": weeks,
        "week": week,
        "assignments": [
            {
                "id": a.pk,
                "title": a.title,
                "week": a.week,
                "course": a.course,
                "kind": a.kind,
                "max_points": a.max_points,
                "due_at": a.due_at,
                "link": a.external_link,
            }
            for a in assignments
        ],
        "people": people,
    }


def ungraded_count(cohort: Cohort) -> int:
    return Submission.objects.filter(
        Q(assignment__cohort=cohort) & Q(submitted_at__isnull=False) & Q(points=None)
    ).count()
