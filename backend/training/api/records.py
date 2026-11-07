"""CRUD endpoints for a cohort's records: students, lessons, attendance, assignments and grading,
materials, recordings, lesson feedback, mentoring sessions and action items."""

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from ..models import (
    ActionItem,
    Assignment,
    Attendance,
    LearningMaterial,
    Lesson,
    LessonFeedback,
    LessonRecording,
    MentoringSession,
    Student,
    Submission,
)
from ..services.common import ServiceError, cohort_by_number, who
from . import serializers as s


class CohortScoped:
    """Generic views nested under /api/cohorts/<number>/; records always belong to that cohort."""

    model = None
    cohort_field = "cohort"
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_cohort(self):
        if not hasattr(self, "_cohort"):
            self._cohort = cohort_by_number(self.kwargs["number"])
        return self._cohort

    def get_queryset(self):
        return self.model.objects.filter(**{self.cohort_field: self.get_cohort()})

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "cohort": self.get_cohort()}

    def perform_create(self, serializer):
        serializer.save(cohort=self.get_cohort())


def crud(model_class, serializer, filters=()):
    """A (list/create, retrieve/update/delete) pair of views for one model."""

    class ListCreate(CohortScoped, generics.ListCreateAPIView):
        model = model_class
        serializer_class = serializer

        def get_queryset(self):
            qs = super().get_queryset()
            for name in filters:
                value = self.request.query_params.get(name)
                if value not in (None, ""):
                    qs = qs.filter(**{name: value})
            return qs

    class Detail(CohortScoped, generics.RetrieveUpdateDestroyAPIView):
        model = model_class
        serializer_class = serializer

    ListCreate.__name__ = f"{model_class.__name__}List"
    Detail.__name__ = f"{model_class.__name__}Detail"
    if filters:
        ListCreate = extend_schema(parameters=[OpenApiParameter(f, str) for f in filters])(ListCreate)
    return ListCreate.as_view(), Detail.as_view()


students = crud(Student, s.StudentSerializer, filters=("dropped",))
lessons = crud(Lesson, s.LessonSerializer, filters=("week", "course"))
assignments = crud(Assignment, s.AssignmentSerializer, filters=("week", "course"))
materials = crud(LearningMaterial, s.LearningMaterialSerializer, filters=("week",))
recordings = crud(LessonRecording, s.LessonRecordingSerializer, filters=("week",))
mentoring = crud(MentoringSession, s.MentoringSessionSerializer)
action_items = crud(ActionItem, s.ActionItemSerializer, filters=("done",))


class LessonFeedbackList(CohortScoped, generics.ListAPIView):
    model = LessonFeedback
    cohort_field = "lesson__cohort"
    serializer_class = s.LessonFeedbackSerializer

    def get_queryset(self):
        return super().get_queryset().select_related("lesson", "student")


@extend_schema(
    methods=["GET"],
    parameters=[OpenApiParameter("week", int, required=True)],
    responses=OpenApiTypes.OBJECT,
    summary="Attendance grid of a week: lessons × students",
)
@extend_schema(methods=["POST"], request=s.AttendanceMarkSerializer, responses=s.AttendanceSerializer)
@api_view(["GET", "POST"])
def attendance(request, number):
    cohort = cohort_by_number(number)
    if request.method == "POST":
        data = s.AttendanceMarkSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        lesson = get_object_or_404(Lesson, pk=data.validated_data["lesson"], cohort=cohort)
        student = get_object_or_404(Student, pk=data.validated_data["student"], cohort=cohort)
        row, _ = Attendance.objects.update_or_create(
            lesson=lesson, student=student, defaults={"present": data.validated_data["present"]}
        )
        return Response(s.AttendanceSerializer(row).data)
    week = s.SurveyQuerySerializer(data=request.query_params)
    week.is_valid(raise_exception=True)
    lessons = list(Lesson.objects.filter(cohort=cohort, week=week.validated_data["week"]))
    marks = {(a.lesson_id, a.student_id): a.present for a in Attendance.objects.filter(lesson__in=lessons)}
    return Response(
        {
            "lessons": s.LessonSerializer(lessons, many=True).data,
            "students": [
                {
                    "id": st.pk,
                    "code": st.code,
                    "name": st.full_name,
                    "present": {str(lesson.pk): marks.get((lesson.pk, st.pk)) for lesson in lessons},
                }
                for st in cohort.students.filter(dropped=False)
            ],
        }
    )


@extend_schema(request=s.GradeSerializer, responses={200: None}, summary="Record a submission and/or a grade")
@api_view(["POST"])
@transaction.atomic
def grade(request, number, pk):
    cohort = cohort_by_number(number)
    assignment = get_object_or_404(Assignment, pk=pk, cohort=cohort)
    data = s.GradeSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    v = data.validated_data
    student = get_object_or_404(Student, pk=v["student"], cohort=cohort)
    points = v.get("points")
    if points is not None and points > assignment.max_points:
        raise ServiceError(f"Points cannot exceed {assignment.max_points:g}.")
    sub, _ = Submission.objects.get_or_create(
        assignment=assignment, student=student, defaults={"source": Submission.Source.STAFF}
    )
    sub.source = Submission.Source.STAFF  # entered on the site: a Classroom sync will not overwrite it
    if v.get("submitted") is not None:
        sub.submitted_at = (sub.submitted_at or timezone.now()) if v["submitted"] else None
    if "points" in v:
        sub.points = points
        sub.graded_at = timezone.now() if points is not None else None
        sub.graded_by = who(request.user)
        if points is not None and not sub.submitted_at:
            sub.submitted_at = timezone.now()
    if "feedback" in v:
        sub.feedback = v["feedback"]
    sub.save()
    return Response({"status": sub.status, "points": sub.points, "submitted_at": sub.submitted_at})
