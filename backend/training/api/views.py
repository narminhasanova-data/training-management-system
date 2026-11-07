"""Staff API for the training section: cohorts, the course catalogue, agendas, weekly surveys,
the gradebook, Google Classroom and training materials."""

from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import Agenda, Cohort, Survey, Week
from ..services import agenda as agendas
from ..services import catalogue, classroom, gradebook, library, recipients, stats
from ..services import surveys as survey_service
from ..services.common import ServiceError, cohort_by_number, who
from . import serializers as s

WEEK = OpenApiParameter("week", int, required=True)
KIND = OpenApiParameter("kind", str, enum=[k for k, _ in Agenda.Kind.choices], default="week")


def _query(serializer_class, request):
    data = serializer_class(data=request.query_params)
    data.is_valid(raise_exception=True)
    return data.validated_data


def _body(serializer_class, request):
    data = serializer_class(data=request.data)
    data.is_valid(raise_exception=True)
    return data.validated_data


# --------------------------------------------------------------------------- cohorts
@extend_schema(
    methods=["GET"],
    responses=OpenApiTypes.OBJECT,
    summary="Cohort cards with headline numbers",
    operation_id="cohorts_list",
)
@extend_schema(methods=["POST"], request=s.CohortSerializer, responses={201: s.CohortSerializer})
@api_view(["GET", "POST"])
def cohorts(request):
    if request.method == "POST":
        data = s.CohortSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        cohort = data.save(source=Cohort.Source.MANUAL)
        return Response(s.CohortSerializer(cohort).data, status=status.HTTP_201_CREATED)
    return Response({"cohorts": [stats.card(c) for c in Cohort.objects.prefetch_related("classroom_classes")]})


@extend_schema(responses=OpenApiTypes.OBJECT, summary="All cohorts side by side")
@api_view(["GET"])
def compare(request):
    return Response({"cohorts": stats.compare()})


@extend_schema(methods=["GET"], responses=OpenApiTypes.OBJECT)
@extend_schema(methods=["PATCH"], request=s.CohortSerializer, responses=s.CohortSerializer)
@api_view(["GET", "PATCH"])
def cohort_detail(request, number):
    cohort = cohort_by_number(number)
    if request.method == "PATCH":
        data = s.CohortSerializer(cohort, data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        data.save()
        return Response(s.CohortSerializer(cohort).data)
    return Response({**stats.card(cohort), **stats.numbers(cohort)})


@extend_schema(request=s.WeekSerializer, responses=s.WeekSerializer, summary="Set a week's topics and note")
@api_view(["PATCH"])
def week_detail(request, number, week):
    cohort = cohort_by_number(number)
    if not 1 <= week <= cohort.weeks_total:
        raise ServiceError("No such week in this cohort.", status=404)
    obj, _ = Week.objects.get_or_create(cohort=cohort, number=week)
    data = s.WeekSerializer(obj, data=request.data, partial=True)
    data.is_valid(raise_exception=True)
    data.save()
    return Response(data.data)


@extend_schema(
    parameters=[WEEK], responses=OpenApiTypes.OBJECT, summary="Lessons, attendance, homework and survey of a week"
)
@api_view(["GET"])
def weekly_report(request, number):
    week = _query(s.SurveyQuerySerializer, request)["week"]
    return Response(stats.weekly_report(cohort_by_number(number), week))


# --------------------------------------------------------------------------- catalogue and recipients
@extend_schema(methods=["GET"], responses=s.CatalogueSerializer)
@extend_schema(
    methods=["PUT"],
    request=s.CatalogueSerializer,
    responses=s.CatalogueSerializer,
    summary="Replace the course catalogue",
)
@api_view(["GET", "PUT"])
def courses(request):
    if request.method == "PUT":
        rows = _body(s.CatalogueSerializer, request)["courses"]
        return Response({"courses": catalogue.replace(rows)})
    return Response({"courses": catalogue.as_list()})


@extend_schema(
    parameters=[OpenApiParameter("channel", str, enum=["email", "whatsapp"])],
    responses=OpenApiTypes.OBJECT,
    summary="Students reachable on a channel, grouped by cohort",
)
@api_view(["GET"])
def recipient_list(request):
    channel = _query(s.ChannelQuerySerializer, request)["channel"]
    return Response({"cohorts": recipients.by_cohort(channel)})


# --------------------------------------------------------------------------- agenda
@extend_schema(
    methods=["GET"],
    parameters=[WEEK, KIND],
    responses=OpenApiTypes.OBJECT,
    summary="The saved agenda, or a draft built from lessons / Classroom",
)
@extend_schema(methods=["PUT"], request=s.AgendaSaveSerializer, responses=OpenApiTypes.OBJECT)
@api_view(["GET", "PUT"])
def agenda(request, number):
    cohort = cohort_by_number(number)
    if request.method == "PUT":
        data = _body(s.AgendaSaveSerializer, request)
        agendas.save(cohort, data["week"], data["kind"], request.data.get("days"), who(request.user))
        return Response(_agenda_payload(cohort, data["week"], data["kind"]))
    q = _query(s.AgendaQuerySerializer, request)
    return Response(_agenda_payload(cohort, q["week"], q["kind"]))


def _agenda_payload(cohort, week, kind):
    from integrations.views import integrations_state

    return {**agendas.payload(cohort, week, kind), "integrations": integrations_state()}


@extend_schema(parameters=[WEEK, KIND], responses={(200, "application/pdf"): OpenApiTypes.BINARY})
@api_view(["GET"])
def agenda_pdf(request, number):
    from ..services.agenda_pdf import filename, render

    q = _query(s.AgendaQuerySerializer, request)
    saved = agendas.get(cohort_by_number(number), q["week"], q["kind"])
    if not saved:
        raise ServiceError("Save the agenda first.", status=404)
    response = HttpResponse(render(saved), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename(saved)}"'
    return response


@extend_schema(
    request=s.AgendaSendSerializer,
    responses=s.SendResultSerializer,
    summary="Email or WhatsApp the saved agenda (PDF attached) to chosen students or a test address",
)
@api_view(["POST"])
def agenda_send(request, number):
    data = _body(s.AgendaSendSerializer, request)
    saved = agendas.get(cohort_by_number(number), data["week"], data["kind"])
    if not saved:
        raise ServiceError("Save the agenda before sending it.")
    result = agendas.send(saved, data["channel"], data["student_ids"], data["test_to"])
    return Response({**result, "agenda": _agenda_payload(saved.cohort, saved.week, saved.kind)})


# --------------------------------------------------------------------------- survey
@extend_schema(
    methods=["GET"],
    parameters=[WEEK],
    responses=OpenApiTypes.OBJECT,
    summary="The week's survey (or a draft) with scales, suggestions and results",
)
@extend_schema(methods=["PUT"], request=s.SurveySaveSerializer, responses=OpenApiTypes.OBJECT)
@api_view(["GET", "PUT"])
def survey(request, number):
    cohort = cohort_by_number(number)
    if request.method == "PUT":
        data = _body(s.SurveySaveSerializer, request)
        survey_service.save(cohort, data["week"], data, who(request.user))
        return Response(_survey_payload(cohort, data["week"]))
    return Response(_survey_payload(cohort, _query(s.SurveyQuerySerializer, request)["week"]))


def _survey_payload(cohort, week):
    from integrations.views import integrations_state

    return {**survey_service.payload(cohort, week), "integrations": integrations_state()}


@extend_schema(
    request=s.SurveySendSerializer,
    responses=s.SendResultSerializer,
    summary="Send personal survey links (or the preview link to a test address)",
)
@api_view(["POST"])
def survey_send(request, number):
    cohort = cohort_by_number(number)
    data = _body(s.SurveySendSerializer, request)
    saved = Survey.objects.filter(cohort=cohort, week=data["week"]).first()
    if not saved:
        raise ServiceError("Save the survey before sending it.")
    result = survey_service.send(saved, data["channel"], data["student_ids"], data["test_to"])
    return Response({**result, "survey": _survey_payload(cohort, data["week"])})


# --------------------------------------------------------------------------- gradebook
@extend_schema(
    parameters=[OpenApiParameter("week", int)],
    responses=OpenApiTypes.OBJECT,
    summary="Students × assignments with status, points and averages",
)
@api_view(["GET"])
def gradebook_view(request, number):
    week = _query(s.WeekQuerySerializer, request)["week"]
    return Response(gradebook.build(cohort_by_number(number), week))


# --------------------------------------------------------------------------- classroom
@extend_schema(responses=OpenApiTypes.OBJECT, summary="The connected account's classes grouped by cohort")
@api_view(["GET"])
def classroom_classes(request):
    return Response(classroom.list_classes())


@extend_schema(
    request=s.ClassroomImportSerializer,
    responses=OpenApiTypes.OBJECT,
    summary="Bring a Classroom cohort onto the site with all its classes",
)
@api_view(["POST"])
def classroom_import(request):
    number = _body(s.ClassroomImportSerializer, request)["number"]
    cohort, created = classroom.import_cohort(number)
    return Response(
        {"created": created, "cohort": stats.card(cohort)},
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@extend_schema(
    request=s.ClassroomSyncSerializer,
    responses=OpenApiTypes.OBJECT,
    summary="Sync a cohort from Classroom now (optionally adding unmatched students)",
)
@api_view(["POST"])
def classroom_sync(request, number):
    cohort = cohort_by_number(number)
    if not cohort.classroom_classes.exists():
        raise ServiceError("This cohort is not linked to Classroom.")
    add = _body(s.ClassroomSyncSerializer, request)["add_unmatched"]
    summary = classroom.sync_or_record(cohort, add_unmatched=add)
    cohort.refresh_from_db()
    if summary.get("error"):
        return Response({"error": summary["error"], "cohort": stats.card(cohort)}, status=status.HTTP_409_CONFLICT)
    return Response({"cohort": stats.card(cohort)})


# --------------------------------------------------------------------------- materials library
@extend_schema(
    parameters=[OpenApiParameter("course", str), OpenApiParameter("cohort", int)],
    responses=OpenApiTypes.OBJECT,
    summary="Courses and the chosen course's Classroom materials",
)
@api_view(["GET"])
def library_view(request):
    q = _query(s.LibraryQuerySerializer, request)
    return Response(library.payload(q["course"], q["cohort"]))


@extend_schema(
    request=s.LibrarySendSerializer,
    responses=s.SendResultSerializer,
    summary="Email chosen materials to chosen students (or a test address)",
)
@api_view(["POST"])
def library_send(request):
    data = _body(s.LibrarySendSerializer, request)
    cohort = cohort_by_number(data["cohort"])
    return Response(library.send(data["course"], cohort, data["material_ids"], data["student_ids"], data["test_to"]))
