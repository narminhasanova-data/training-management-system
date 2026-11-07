"""The survey form students open from their personal link (no login), and the staff preview."""

from django.core.cache import cache
from django.db import transaction
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from ..models import SurveyInvite, SurveyResponse
from ..services import surveys
from ..services.common import ServiceError

POSTS_PER_HOUR = 30


def _client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR", "")


def _too_many(request) -> bool:
    key = f"survey-posts:{_client_ip(request)}"
    cache.add(key, 0, 3600)
    return cache.incr(key) > POSTS_PER_HOUR


def _form(survey, data=None, missing=()):
    """questions() with what the student already chose or typed (after a failed submit)."""
    data = data or {}
    out = []
    for q in surveys.questions(survey):
        q = dict(q, missing=q["id"] in missing)
        if q["kind"] == "choice":
            q["value"] = data.get(q["id"], "")
        elif q["kind"] == "text":
            q["value"] = data.get(q["id"], "")
        else:
            q["row_items"] = [
                {"label": row, "field": f"{q['id']}:{i}", "value": data.get(f"{q['id']}:{i}", "")}
                for i, row in enumerate(q["rows"])
            ]
        out.append(q)
    return out


def _page(request, survey, *, name="", preview=False, data=None, missing=(), status=200):
    return render(
        request,
        "public/survey.html",
        {
            "survey": survey,
            "questions": _form(survey, data, missing),
            "name": name,
            "preview": preview,
            "missing_count": len(missing),
        },
        status=status,
    )


def _done(request, survey, name="", preview=False, already=False):
    return render(
        request, "public/survey_done.html", {"survey": survey, "name": name, "preview": preview, "already": already}
    )


@require_http_methods(["GET", "POST"])
def answer(request, token):
    invite = SurveyInvite.objects.select_related("survey__cohort", "student").filter(token=token).first()
    if not invite:
        raise Http404("Unknown survey link")
    survey, name = invite.survey, invite.student.full_name
    if request.method == "GET":
        if SurveyResponse.objects.filter(invite=invite).exists():
            return _done(request, survey, name, already=True)
        return _page(request, survey, name=name)
    if _too_many(request):
        return render(
            request, "public/survey_error.html", {"message": "Too many attempts. Try again later."}, status=429
        )
    answers, missing = surveys.parse(survey, request.POST)
    if missing:
        return _page(request, survey, name=name, data=request.POST, missing=missing, status=400)
    with transaction.atomic():
        locked = SurveyInvite.objects.select_for_update().get(pk=invite.pk)  # one answer per link
        if SurveyResponse.objects.filter(invite=locked).exists():
            return _done(request, survey, name, already=True)
        SurveyResponse.objects.create(
            survey=survey, student=invite.student, invite=locked, answers=answers, **surveys.scores(answers)
        )
    return _done(request, survey, name)


@require_http_methods(["GET", "POST"])
def preview(request, signature):
    try:
        survey = surveys.survey_from_preview(signature)
    except ServiceError as exc:
        return render(request, "public/survey_error.html", {"message": str(exc)}, status=404)
    if request.method == "GET":
        return _page(request, survey, preview=True)
    answers, missing = surveys.parse(survey, request.POST)
    if missing:
        return _page(request, survey, preview=True, data=request.POST, missing=missing, status=400)
    return _done(request, survey, preview=True)
