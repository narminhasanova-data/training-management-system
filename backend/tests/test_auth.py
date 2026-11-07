from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


def test_login_returns_token_and_me_works():
    client = APIClient()
    r = client.post("/api/auth/login/", {"username": "coordinator", "password": "coordinator-demo"}, format="json")
    assert r.status_code == 200
    client.credentials(HTTP_AUTHORIZATION=f"Token {r.json()['token']}")
    assert client.get("/api/auth/me/").json()["username"] == "coordinator"


def test_wrong_password_is_rejected():
    r = APIClient().post("/api/auth/login/", {"username": "coordinator", "password": "nope-nope"}, format="json")
    assert r.status_code == 400
    assert r.json() == {"error": "Wrong username or password."}


def test_non_staff_user_cannot_sign_in_or_call_the_api():
    get_user_model().objects.create_user("student", password="password-123")
    client = APIClient()
    assert (
        client.post("/api/auth/login/", {"username": "student", "password": "password-123"}, format="json").status_code
        == 400
    )
    client.force_authenticate(get_user_model().objects.get(username="student"))
    assert client.get("/api/cohorts/").status_code == 403


def test_logout_invalidates_the_token():
    client = APIClient()
    token = client.post(
        "/api/auth/login/", {"username": "coordinator", "password": "coordinator-demo"}, format="json"
    ).json()["token"]
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    assert client.post("/api/auth/logout/").status_code == 204
    assert client.get("/api/auth/me/").status_code == 401


def test_api_requires_authentication():
    assert APIClient().get("/api/cohorts/").status_code == 401


def test_openapi_schema_is_served(api):
    r = api.get("/api/schema/")
    assert r.status_code == 200
    assert b"Training Management System API" in r.content
