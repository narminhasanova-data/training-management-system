from django.conf import settings
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from . import accounts, whatsapp
from .serializers import PURPOSES, ConnectResponseSerializer, ConnectSerializer, IntegrationsSerializer


def integrations_state() -> dict:
    return {
        "mail": accounts.status("mail"),
        "classroom": accounts.status("classroom"),
        "whatsapp": {"ready": whatsapp.ready(), "mode": whatsapp.mode()},
    }


@extend_schema(responses=IntegrationsSerializer)
@api_view(["GET"])
def overview(request):
    """Connection state of the sender mailbox, Google Classroom and WhatsApp."""
    return Response(integrations_state())


@extend_schema(request=ConnectSerializer, responses=ConnectResponseSerializer)
@api_view(["POST"])
def connect(request, purpose):
    """Start connecting an account; the web app sends the browser to the returned URL."""
    if purpose not in PURPOSES:
        return Response({"error": "Unknown purpose."}, status=status.HTTP_404_NOT_FOUND)
    data = ConnectSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    try:
        return Response({"url": accounts.start(purpose, request.user, data.validated_data["page"])})
    except accounts.IntegrationError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(request=None, responses={204: None})
@api_view(["POST"])
def disconnect(request, purpose):
    if purpose not in PURPOSES:
        return Response({"error": "Unknown purpose."}, status=status.HTTP_404_NOT_FOUND)
    accounts.disconnect(purpose)
    return Response(status=status.HTTP_204_NO_CONTENT)


@require_http_methods(["GET", "POST"])
def mock_authorize(request):
    """A local stand-in for the provider's consent screen (no real account involved)."""
    try:
        state = accounts.read_state(request.GET.get("state", ""))
    except accounts.IntegrationError as exc:
        return render(request, "integrations/mock_consent.html", {"error": str(exc)}, status=400)
    purpose = state["purpose"]
    if request.method == "POST":
        if request.POST.get("decision") != "allow":
            return redirect(
                accounts.return_url(state, connected="error", purpose=purpose, message="Access was not granted.")
            )
        email = (request.POST.get("email") or "").strip() or settings.TMS["MOCK_GOOGLE_EMAIL"]
        acc = accounts.complete(state, email, request.POST.getlist("scope"))
        if purpose == "classroom":
            from training.services import classroom

            classroom.refresh_materials_later()
        return redirect(accounts.return_url(state, connected="ok", purpose=purpose, email=acc.email))
    scopes = [(s, accounts.SCOPE_LABELS.get(s, s)) for s in accounts.SCOPES[purpose]]
    return render(
        request,
        "integrations/mock_consent.html",
        {
            "state": request.GET["state"],
            "purpose": purpose,
            "scopes": scopes,
            "email": settings.TMS["MOCK_GOOGLE_EMAIL"],
            "org": settings.TMS["ORG_NAME"],
        },
    )
