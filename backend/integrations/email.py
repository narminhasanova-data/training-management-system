"""Outgoing email through the connected sender mailbox. Delivery uses Django's EMAIL_BACKEND
(console locally, Mailpit in docker-compose); every message is also logged as an OutboundMessage."""

import logging
from dataclasses import dataclass, field
from email.utils import formataddr

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection

from . import accounts
from .models import OutboundMessage

log = logging.getLogger(__name__)


@dataclass
class Email:
    to: str
    subject: str
    text: str
    html: str = ""
    attachments: list[tuple[str, bytes, str]] = field(default_factory=list)


def ready() -> bool:
    acc = accounts.account(accounts.ConnectedAccount.Purpose.MAIL)
    return bool(acc and not acc.expired)


def sender() -> str:
    acc = accounts.require(accounts.ConnectedAccount.Purpose.MAIL)
    return formataddr((settings.TMS["ORG_NAME"], acc.email))


def send_many(messages: list[Email], context: str = "") -> tuple[int, list[dict]]:
    """Send each message separately (one failure does not stop the rest).
    Returns (sent count, [{"to", "error"}])."""
    from_addr = sender()
    sent, failed = 0, []
    with get_connection() as connection:
        for m in messages:
            msg = EmailMultiAlternatives(m.subject, m.text, from_addr, [m.to], connection=connection)
            if m.html:
                msg.attach_alternative(m.html, "text/html")
            for name, content, mime in m.attachments:
                msg.attach(name, content, mime)
            try:
                msg.send()
            except Exception as exc:  # noqa: BLE001 - report per recipient, keep going
                log.warning("email to %s failed: %s", m.to, exc)
                failed.append({"to": m.to, "error": exc.__class__.__name__})
                status, error = OutboundMessage.Status.FAILED, str(exc)
            else:
                sent += 1
                status, error = OutboundMessage.Status.SENT, ""
            OutboundMessage.objects.create(
                channel=OutboundMessage.Channel.EMAIL,
                recipient=m.to,
                subject=m.subject[:300],
                body=m.text,
                payload={"attachments": [a[0] for a in m.attachments]},
                status=status,
                error=error,
                context=context,
            )
    return sent, failed
