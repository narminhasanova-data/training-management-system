"""Headline numbers for cohort cards, the comparison view and the weekly report."""

from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone

from ..models import ActionItem, Attendance, Cohort, Lesson, MentoringSession, Submission, Survey, SurveyResponse
from .common import average, percent


def card(cohort: Cohort) -> dict:
    students = cohort.students.all()
    return {
        "number": cohort.number,
        "name": cohort.name,
        "status": cohort.status,
        "source": cohort.source,
        "start_date": cohort.start_date,
        "weeks_total": cohort.weeks_total,
        "current_week": cohort.current_week,
        "students": students.count(),
        "active_students": students.filter(dropped=False).count(),
        "classroom": {
            "classes": [
                {"id": c.external_id, "name": c.name, "course": c.course, "state": c.state}
                for c in cohort.classroom_classes.all()
            ],
            "synced_at": cohort.classroom_synced_at,
            "summary": cohort.classroom_summary,
        },
    }


def numbers(cohort: Cohort) -> dict:
    attendance = Attendance.objects.filter(lesson__cohort=cohort, lesson__held=True)
    present = attendance.filter(present=True).count()
    due = cohort.assignments.filter(published=True).filter(Q(due_at__isnull=True) | Q(due_at__lte=timezone.now()))
    active = cohort.students.filter(dropped=False).count()
    submitted = Submission.objects.filter(
        assignment__in=due, student__dropped=False, submitted_at__isnull=False
    ).count()
    graded = Submission.objects.filter(assignment__cohort=cohort, points__isnull=False).select_related("assignment")
    satisfaction = SurveyResponse.objects.filter(survey__cohort=cohort).aggregate(v=Avg("trainer_score"))["v"]
    return {
        "attendance_rate": percent(present, attendance.count()),
        "submission_rate": percent(submitted, due.count() * active),
        "average_grade": average(100 * s.points / s.assignment.max_points for s in graded if s.assignment.max_points),
        "satisfaction": round(satisfaction, 2) if satisfaction is not None else None,
    }


def compare() -> list[dict]:
    return [{**card(c), **numbers(c)} for c in Cohort.objects.all()]


def weekly_report(cohort: Cohort, week: int) -> dict:
    lessons = []
    for lesson in Lesson.objects.filter(cohort=cohort, week=week).annotate(
        present=Count("attendance", filter=Q(attendance__present=True)), total=Count("attendance")
    ):
        lessons.append(
            {
                "id": lesson.id,
                "course": lesson.course,
                "kind": lesson.kind,
                "date": lesson.date,
                "trainer": lesson.trainer,
                "held": lesson.held,
                "present": lesson.present,
                "total": lesson.total,
            }
        )
    homework = []
    for a in cohort.assignments.filter(week=week, published=True):
        subs = a.submissions.all()
        homework.append(
            {
                "id": a.id,
                "title": a.title,
                "course": a.course,
                "submitted": subs.filter(submitted_at__isnull=False).count(),
                "graded": subs.filter(points__isnull=False).count(),
                "average": average(
                    100 * s.points / a.max_points for s in subs if s.points is not None and a.max_points
                ),
            }
        )
    survey = Survey.objects.filter(cohort=cohort, week=week).first()
    survey_numbers = None
    if survey:
        agg = survey.responses.aggregate(
            u=Avg("understanding"), t=Avg("trainer_score"), m=Avg("mentor_score"), x=Avg("materials_score")
        )
        survey_numbers = {
            "invited": survey.invites.exclude(sent_at=None).count(),
            "answered": survey.responses.count(),
            **{k: round(v, 2) if v is not None else None for k, v in agg.items()},
        }
    start = cohort.start_date
    mentoring = MentoringSession.objects.filter(cohort=cohort)
    if start:
        from datetime import timedelta

        mentoring = mentoring.filter(
            date__gte=start + timedelta(weeks=week - 1), date__lt=start + timedelta(weeks=week)
        )
    total_present = sum(x["present"] for x in lessons)
    total_rows = sum(x["total"] for x in lessons)
    return {
        "cohort": cohort.number,
        "week": week,
        "lessons": lessons,
        "attendance_rate": percent(total_present, total_rows),
        "homework": homework,
        "survey": survey_numbers,
        "mentoring": {"sessions": mentoring.count(), "minutes": mentoring.aggregate(m=Sum("minutes"))["m"] or 0},
        "open_action_items": list(
            ActionItem.objects.filter(cohort=cohort, done=False).values("id", "week", "feedback", "action")
        ),
    }
