from urllib.parse import parse_qs, urlparse

from django.core.management import call_command
from django.test import Client

from integrations import accounts
from integrations.models import ConnectedAccount


def _consent(api, purpose="classroom"):
    url = api.post(f"/api/integrations/{purpose}/connect/", {"page": "classroom"}, format="json").json()["url"]
    return url


def test_mock_oauth_round_trip(api):
    ConnectedAccount.objects.all().delete()
    url = _consent(api)
    client = Client()
    page = client.get(url)
    assert page.status_code == 200 and b"no real account" in page.content
    r = client.post(
        url, {"decision": "allow", "email": "teacher@academy.example", "scope": accounts.SCOPES["classroom"]}
    )
    assert r.status_code == 302
    query = parse_qs(urlparse(r["Location"]).query)
    assert query["connected"] == ["ok"] and query["email"] == ["teacher@academy.example"]
    status = api.get("/api/integrations/").json()["classroom"]
    assert status["connected"] and not status["expired"] and status["email"] == "teacher@academy.example"
    assert "teacher@academy.example" not in ConnectedAccount.objects.get(purpose="classroom").secret  # stored encrypted


def test_denied_consent_returns_an_error(api):
    url = _consent(api, "mail")
    r = Client().post(url, {"decision": "deny"})
    assert parse_qs(urlparse(r["Location"]).query)["connected"] == ["error"]


def test_forged_state_is_rejected():
    assert Client().get("/oauth/mock/authorize/?state=forged").status_code == 400


def test_expiry_warning_and_command(api):
    call_command("expire_connection", "mail")
    mail = api.get("/api/integrations/").json()["mail"]
    assert mail["expired"] is True
    assert api.post("/api/integrations/mail/disconnect/").status_code == 204
    assert api.get("/api/integrations/").json()["mail"]["connected"] is False
