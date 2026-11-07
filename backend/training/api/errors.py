"""One error shape for the whole API: ``{"error": "<message>"}`` (plus ``fields`` for validation)."""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from integrations.accounts import IntegrationError
from integrations.classroom.base import ClassroomError
from integrations.whatsapp import WhatsAppError

from ..services.common import ServiceError


def _first_message(data) -> str:
    if isinstance(data, dict):
        for key, value in data.items():
            message = _first_message(value)
            if message:
                return message if key in ("non_field_errors", "detail") else f"{key}: {message}"
    if isinstance(data, list) and data:
        return _first_message(data[0])
    return str(data) if data else ""


def exception_handler(exc, context):
    if isinstance(exc, ServiceError):
        return Response({"error": str(exc)}, status=exc.status)
    if isinstance(exc, (IntegrationError, ClassroomError, WhatsAppError)):
        return Response({"error": str(exc)}, status=status.HTTP_409_CONFLICT)
    response = drf_exception_handler(exc, context)
    if response is not None and not (isinstance(response.data, dict) and "error" in response.data):
        fields = response.data if isinstance(response.data, dict) and "detail" not in response.data else None
        response.data = {"error": _first_message(response.data), **({"fields": fields} if fields else {})}
    return response
