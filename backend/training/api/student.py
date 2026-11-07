"""Student API (no student UI ships with this demo): sign in, see the cohort's weeks, materials,
recordings and assignments, hand in work and rate a lesson.

Students sign in with the email their cohort knows. In the original system this was a Google
sign-in; here, with GOOGLE_MODE=mock, the email alone is accepted (demo only)."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, parser_classes, permission_classes, throttle_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response

from accounts.views import LoginThrottle

from ..models import Assignment, Lesson, LessonFeedback, Student, Submission
from ..services.common import ServiceError, cohort_by_number
from . import serializers as s


class IsStudent(BasePermission):
    message = "A student account is required."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.student_profiles.exists())


def _profile(request, number) -> Student:
    profile = request.user.student_profiles.filter(cohort__number=number, dropped=False).first()
    if not profile:
        raise ServiceError("You are not a student of this cohort.", status=403)
    return profile


@extend_schema(
    request=s.StudentSignInSerializer,
    responses=OpenApiTypes.OBJECT,
    auth=[],
    summary="Demo sign-in for students (mock mode only)",
)
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginThrottle])
def mock_sign_in(request):
    if settings.TMS["GOOGLE_MODE"] != "mock":
        raise ServiceError("Student sign-in is only available in mock mode in this demo.", status=404)
    data = s.StudentSignInSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    email = data.validated_data["email"].lower()
    profiles = Student.objects.filter(email__iexact=email, dropped=False)
    if not profiles.exists():
        raise ServiceError("No cohort has a student with this email.", status=404)
    user_model = get_user_model()
    user, _ = user_model.objects.get_or_create(username=f"student:{email}", defaults={"email": email})
    profiles.filter(user__isnull=True).update(user=user)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "cohorts": [p.cohort.number for p in profiles.select_related("cohort")]})


@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([IsStudent])
def me(request):
    profiles = request.user.student_profiles.select_related("cohort").filter(dropped=False)
    return Response(
        {
            "email": request.user.email,
            "cohorts": [
                {"number": p.cohort.number, "name": p.cohort.name, "code": p.code, "name_on_record": p.full_name}
                for p in profiles
            ],
        }
    )


@extend_schema(request=None, responses={204: None})
@api_view(["POST"])
@permission_classes([IsStudent])
def logout(request):
    Token.objects.filter(user=request.user).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(responses=OpenApiTypes.OBJECT, summary="The student's view of a cohort, week by week")
@api_view(["GET"])
@permission_classes([IsStudent])
def cohort_view(request, number):
    student = _profile(request, number)
    cohort = cohort_by_number(number)
    subs = {x.assignment_id: x for x in student.submissions.all()}
    weeks = []
    for w in range(1, min(cohort.current_week, cohort.weeks_total) + 1):
        topics = cohort.weeks.filter(number=w).values_list("topics", flat=True).first() or {}
        weeks.append(
            {
                "week": w,
                "topics": topics,
                "materials": [
                    {"title": m.title, "kind": m.kind, "url": m.url or (m.file.url if m.file else "")}
                    for m in cohort.learning_materials.filter(week=w, visible=True)
                ],
                "recordings": [
                    {"title": r.title, "url": r.url or (r.file.url if r.file else ""), "duration_min": r.duration_min}
                    for r in cohort.recordings.filter(week=w, visible=True)
                ],
                "assignments": [
                    {
                        "id": a.pk,
                        "title": a.title,
                        "course": a.course,
                        "due_at": a.due_at,
                        "max_points": a.max_points,
                        "status": subs[a.pk].status if a.pk in subs else "missing",
                        "points": subs[a.pk].points if a.pk in subs else None,
                    }
                    for a in cohort.assignments.filter(week=w, published=True)
                ],
                "lessons": [
                    {"id": x.pk, "course": x.course, "kind": x.kind, "date": x.date, "trainer": x.trainer}
                    for x in cohort.lessons.filter(week=w, held=True)
                ],
            }
        )
    return Response(
        {"cohort": {"number": cohort.number, "name": cohort.name, "current_week": cohort.current_week}, "weeks": weeks}
    )


@extend_schema(
    request={"multipart/form-data": s.StudentSubmitSerializer, "application/json": s.StudentSubmitSerializer},
    responses=OpenApiTypes.OBJECT,
    summary="Hand in (or replace) work for an assignment",
)
@api_view(["POST"])
@permission_classes([IsStudent])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def submit(request, number):
    student = _profile(request, number)
    data = s.StudentSubmitSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    v = data.validated_data
    assignment = get_object_or_404(Assignment, pk=v["assignment"], cohort=student.cohort, published=True)
    sub, _ = Submission.objects.get_or_create(assignment=assignment, student=student)
    if sub.points is not None:
        raise ServiceError("This work has already been graded.")
    sub.source = Submission.Source.PORTAL
    sub.submitted_at = timezone.now()
    sub.late = bool(assignment.due_at and sub.submitted_at > assignment.due_at)
    sub.link, sub.text = v["link"], v["text"]
    if v["file"]:
        sub.file = v["file"]
    sub.save()
    return Response({"status": sub.status, "late": sub.late, "submitted_at": sub.submitted_at})


@extend_schema(request=s.StudentLessonRatingSerializer, responses=OpenApiTypes.OBJECT, summary="Rate a lesson (1–5)")
@api_view(["POST"])
@permission_classes([IsStudent])
def rate_lesson(request, number):
    student = _profile(request, number)
    data = s.StudentLessonRatingSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    v = data.validated_data
    lesson = get_object_or_404(Lesson, pk=v.pop("lesson"), cohort=student.cohort, held=True)
    fb, created = LessonFeedback.objects.update_or_create(lesson=lesson, student=student, defaults=v)
    return Response({"id": fb.pk, "updated": not created})
