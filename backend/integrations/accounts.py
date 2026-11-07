"""Connected accounts (OAuth) for the two purposes the training office needs:

* ``mail``: the mailbox agendas, survey links and materials are sent from;
* ``classroom``: the Google Classroom teacher account the sync reads.

Only the offline mock is implemented: "connecting" opens a local consent screen
(/oauth/mock/authorize/) and stores a fake token that expires after MOCK_TOKEN_DAYS, so the
expiry warnings and the reconnect flow can be demonstrated without any Google account.
"""

import base64
import hashlib
import json
import secrets
from datetime import timedelta
from urllib.parse import urlencode

from cryptography.fernet import Fernet
from django.conf import settings
from django.core import signing
from django.utils import timezone

from .models import ConnectedAccount

SCOPES = {
    ConnectedAccount.Purpose.MAIL: ["openid", "email", "gmail.send"],
    ConnectedAccount.Purpose.CLASSROOM: [
        "openid",
        "email",
        "classroom.courses.readonly",
        "classroom.rosters.readonly",
        "classroom.profile.emails",
        "classroom.topics.readonly",
        "classroom.coursework.students.readonly",
        "classroom.courseworkmaterials.readonly",
    ],
}
SCOPE_LABELS = {
    "openid": "Know who you are",
    "email": "See your email address",
    "gmail.send": "Send email on your behalf",
    "classroom.courses.readonly": "View your classes",
    "classroom.rosters.readonly": "View class rosters",
    "classroom.profile.emails": "See students' email addresses",
    "classroom.topics.readonly": "View class topics",
    "classroom.coursework.students.readonly": "View coursework and grades",
    "classroom.courseworkmaterials.readonly": "View class materials",
}
MATERIALS_SCOPE = "classroom.courseworkmaterials.readonly"
EXPIRY_WARNING = timedelta(hours=36)
STATE_SALT = "integrations.oauth-state"
PAGES = {"agenda", "surveys", "classroom", "tracker"}


class IntegrationError(Exception):
    """An integration is not connected, has expired, or is not available in this deployment."""


def _fernet() -> Fernet:
    key = settings.TMS["TOKEN_ENCRYPTION_KEY"]
    if not key:
        key = base64.urlsafe_b64encode(hashlib.sha256(f"tokens:{settings.SECRET_KEY}".encode()).digest()).decode()
    return Fernet(key.encode())


def mode() -> str:
    return settings.TMS["GOOGLE_MODE"]


def account(purpose: str) -> ConnectedAccount | None:
    return ConnectedAccount.objects.filter(purpose=purpose).first()


def status(purpose: str) -> dict:
    acc = account(purpose)
    if not acc:
        return {"connected": False, "expired": False, "expiring_soon": False, "mode": mode()}
    soon = bool(acc.expires_at and not acc.expired and acc.expires_at - timezone.now() < EXPIRY_WARNING)
    return {
        "connected": True,
        "mode": mode(),
        "email": acc.email,
        "connected_at": acc.connected_at,
        "connected_by": acc.connected_by,
        "expires_at": acc.expires_at,
        "expired": acc.expired,
        "expiring_soon": soon,
        "scopes": acc.scopes,
    }


def require(purpose: str) -> ConnectedAccount:
    acc = account(purpose)
    label = ConnectedAccount.Purpose(purpose).label
    if not acc:
        raise IntegrationError(f"{label} is not connected.")
    if acc.expired:
        raise IntegrationError(f"The {label.lower()} connection has expired. Reconnect it to continue.")
    return acc


def has_scope(purpose: str, scope: str) -> bool:
    acc = account(purpose)
    return bool(acc and scope in (acc.scopes or []))


def start(purpose: str, user, page: str) -> str:
    """The address the browser opens to grant access."""
    if purpose not in SCOPES:
        raise IntegrationError("Unknown purpose.")
    if mode() != "mock":
        raise IntegrationError("Only the mock Google sign-in is available in this demo (GOOGLE_MODE=mock).")
    state = signing.dumps(
        {
            "purpose": purpose,
            "page": page if page in PAGES else "classroom",
            "by": user.get_username(),
            "nonce": secrets.token_hex(8),
        },
        salt=STATE_SALT,
    )
    return f"/oauth/mock/authorize/?{urlencode({'state': state})}"


def read_state(state: str) -> dict:
    try:
        return signing.loads(state, salt=STATE_SALT, max_age=600)
    except signing.BadSignature as exc:
        raise IntegrationError("The sign-in request is invalid or has expired. Start again.") from exc


def complete(state: dict, email: str, scopes: list[str]) -> ConnectedAccount:
    """Store the (mock) grant for the purpose in `state`."""
    purpose = state["purpose"]
    granted = [s for s in SCOPES[purpose] if s in scopes]
    token = {"access_token": secrets.token_urlsafe(32), "refresh_token": secrets.token_urlsafe(32), "mock": True}
    acc, _ = ConnectedAccount.objects.update_or_create(
        purpose=purpose,
        defaults={
            "provider": "google",
            "email": email,
            "secret": _fernet().encrypt(json.dumps(token).encode()).decode(),
            "scopes": granted,
            "connected_at": timezone.now(),
            "connected_by": state.get("by", ""),
            "expires_at": timezone.now() + timedelta(days=settings.TMS["MOCK_TOKEN_DAYS"]),
            "revoked_at": None,
        },
    )
    return acc


def return_url(state: dict, **params) -> str:
    return f"{settings.TMS['FRONTEND_URL']}/{state.get('page', 'classroom')}?{urlencode(params)}"


def disconnect(purpose: str) -> None:
    ConnectedAccount.objects.filter(purpose=purpose).delete()


def expire(purpose: str) -> bool:
    """Demo helper: behave as if the provider had dropped the token."""
    return bool(ConnectedAccount.objects.filter(purpose=purpose).update(revoked_at=timezone.now()))
