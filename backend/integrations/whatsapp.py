"""WhatsApp notifications. Business-initiated WhatsApp messages must use pre-approved templates,
so callers send a template name plus parameters (and optionally a document).

Only the mock client exists in this demo: it validates the number and records the message as an
OutboundMessage with status "simulated"; nothing leaves the machine."""

import re
from dataclasses import dataclass
from typing import Protocol

from django.conf import settings

from .models import OutboundMessage


@dataclass
class Document:
    filename: str
    content: bytes


class WhatsAppClient(Protocol):
    def send_template(
        self, to: str, template: str, params: list[str], document: Document | None = None, context: str = ""
    ) -> None: ...


class WhatsAppError(Exception):
    pass


def normalize(phone: str) -> str:
    """Digits of an international number ('+1 202 555 0103' -> '12025550103'), or ''."""
    digits = re.sub(r"\D", "", phone or "")
    return digits if 8 <= len(digits) <= 15 else ""


class MockWhatsApp:
    def send_template(self, to, template, params, document=None, context=""):
        number = normalize(to)
        if not number:
            raise WhatsAppError("Invalid phone number")
        OutboundMessage.objects.create(
            channel=OutboundMessage.Channel.WHATSAPP,
            recipient=number,
            template=template,
            body=" | ".join(params),
            status=OutboundMessage.Status.SIMULATED,
            context=context,
            payload={"params": params, "document": document.filename if document else None},
        )


def mode() -> str:
    return settings.TMS["WHATSAPP_MODE"]


def ready() -> bool:
    return mode() == "mock"


def client() -> WhatsAppClient:
    if mode() != "mock":
        raise WhatsAppError("Only the mock WhatsApp client is available in this demo (WHATSAPP_MODE=mock).")
    return MockWhatsApp()


def send_many(
    items: list[tuple[str, str, list[str]]], template: str, document: Document | None = None, context: str = ""
) -> tuple[int, list[dict]]:
    """items: (label, phone, params). Returns (sent count, [{"to", "error"}])."""
    wa = client()
    sent, failed = 0, []
    for label, phone, params in items:
        try:
            wa.send_template(phone, template, params, document, context)
            sent += 1
        except WhatsAppError as exc:
            failed.append({"to": label or phone, "error": str(exc)})
    return sent, failed
