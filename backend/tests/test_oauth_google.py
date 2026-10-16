"""
Google OAuth: /auth/oauth/google/ endpoint behaviour and ID-token
verification (google-auth path + PyJWT fallback). All network calls mocked.
"""

import sys
import types

import pytest
from django.conf import settings
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from apps.accounts import oauth
from apps.accounts.models import RoleRequest, User, UserRole

pytestmark = pytest.mark.django_db

CLIENT_ID = "test-client-id.apps.googleusercontent.com"


def google_enabled_settings():
    return override_settings(SAFECITY={**settings.SAFECITY, "GOOGLE_CLIENT_ID": CLIENT_ID})


def google_disabled_settings():
    return override_settings(SAFECITY={**settings.SAFECITY, "GOOGLE_CLIENT_ID": ""})


def claims(**overrides):
    base = {
        "email": "gina@example.com",
        "email_verified": True,
        "iss": "https://accounts.google.com",
        "given_name": "Gina",
        "family_name": "Google",
    }
    base.update(overrides)
    return base


def post_oauth(client, payload):
    return client.post(reverse("auth-oauth-google"), payload, format="json")


# ── endpoint behaviour ─────────────────────────────────────────────────


def test_unconfigured_returns_503(client):
    # Use RequestFactory to bypass Django middleware/template rendering
    # which has a Python 3.14 bug (TemplateContext.__copy__) when logging
    # 5xx responses.
    from django.test import RequestFactory

    from apps.accounts.views_auth import GoogleOAuthView

    with google_disabled_settings():
        factory = RequestFactory()
        request = factory.post("/api/v1/auth/oauth/google/", {"id_token": "x"})
        response = GoogleOAuthView.as_view()(request)
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.data["code"] == "oauth_unconfigured"


def test_missing_id_token_400(client):
    with google_enabled_settings():
        response = post_oauth(client, {})
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_invalid_requested_role_400(client):
    with google_enabled_settings():
        response = post_oauth(client, {"id_token": "x", "requested_role": "superuser"})
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_verification_failure_401(client, monkeypatch):
    def raiser(token):
        raise ValueError("Invalid token.")

    monkeypatch.setattr(oauth, "verify_google_id_token", raiser)
    with google_enabled_settings():
        response = post_oauth(client, {"id_token": "bad"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_new_user_autoprovisioned(client, monkeypatch):
    monkeypatch.setattr(oauth, "verify_google_id_token", lambda token: claims())
    with google_enabled_settings():
        response = post_oauth(client, {"id_token": "tok"})
    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data and "refresh" in response.data
    user = User.objects.get(email="gina@example.com")
    assert user.role == UserRole.CITIZEN
    assert user.email_verified_at is not None
    assert user.first_name == "Gina"


def test_new_user_with_role_request(client, monkeypatch, department):
    monkeypatch.setattr(
        oauth, "verify_google_id_token", lambda token: claims(email="req@example.com")
    )
    with google_enabled_settings():
        response = post_oauth(
            client,
            {
                "id_token": "tok",
                "requested_role": "volunteer",
                "requested_department_id": str(department.id),
                "role_request_reason": "I want to help",
            },
        )
    assert response.status_code == status.HTTP_200_OK
    role_request = RoleRequest.objects.get(user__email="req@example.com")
    assert role_request.requested_role == "volunteer"
    assert role_request.department == department
    assert role_request.reason == "I want to help"


def test_citizen_role_request_is_ignored(client, monkeypatch):
    monkeypatch.setattr(
        oauth, "verify_google_id_token", lambda token: claims(email="citizen2@example.com")
    )
    with google_enabled_settings():
        response = post_oauth(client, {"id_token": "tok", "requested_role": "citizen"})
    assert response.status_code == status.HTTP_200_OK
    assert not RoleRequest.objects.exists()


def test_invalid_department_uuid_is_ignored(client, monkeypatch):
    monkeypatch.setattr(
        oauth, "verify_google_id_token", lambda token: claims(email="baddep@example.com")
    )
    with google_enabled_settings():
        response = post_oauth(
            client,
            {
                "id_token": "tok",
                "requested_role": "volunteer",
                "requested_department_id": "not-a-uuid",
            },
        )
    assert response.status_code == status.HTTP_200_OK
    assert RoleRequest.objects.get(user__email="baddep@example.com").department is None


def test_existing_user_logs_in_without_duplicate(client, monkeypatch, citizen):
    monkeypatch.setattr(
        oauth, "verify_google_id_token", lambda token: claims(email=citizen.email)
    )
    with google_enabled_settings():
        response = post_oauth(client, {"id_token": "tok"})
    assert response.status_code == status.HTTP_200_OK
    assert response.data["user"]["id"] == str(citizen.id)
    assert User.objects.filter(email=citizen.email).count() == 1


def test_existing_user_verification_backfilled(client, monkeypatch):
    user = User.objects.create_user(email="unverified@example.com", password="Testpass123!")
    assert user.email_verified_at is None
    monkeypatch.setattr(oauth, "verify_google_id_token", lambda token: claims(email=user.email))
    with google_enabled_settings():
        response = post_oauth(client, {"id_token": "tok"})
    assert response.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    assert user.email_verified_at is not None


def test_deactivated_user_403(client, monkeypatch, citizen):
    citizen.is_active = False
    citizen.save(update_fields=["is_active"])
    monkeypatch.setattr(oauth, "verify_google_id_token", lambda token: claims(email=citizen.email))
    with google_enabled_settings():
        response = post_oauth(client, {"id_token": "tok"})
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_locked_user_423(client, monkeypatch, citizen):
    citizen.locked_until = timezone.now() + timezone.timedelta(minutes=10)
    citizen.save(update_fields=["locked_until"])
    monkeypatch.setattr(oauth, "verify_google_id_token", lambda token: claims(email=citizen.email))
    with google_enabled_settings():
        response = post_oauth(client, {"id_token": "tok"})
    assert response.status_code == status.HTTP_423_LOCKED


def test_claim_without_email_401(client, monkeypatch):
    monkeypatch.setattr(oauth, "verify_google_id_token", lambda token: claims(email=""))
    with google_enabled_settings():
        response = post_oauth(client, {"id_token": "tok"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_unverified_google_email_401(client, monkeypatch):
    monkeypatch.setattr(
        oauth, "verify_google_id_token", lambda token: claims(email_verified=False)
    )
    with google_enabled_settings():
        response = post_oauth(client, {"id_token": "tok"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ── token verification module ──────────────────────────────────────────


def test_google_enabled_reads_setting():
    with google_disabled_settings():
        assert oauth.google_enabled() is False
    with google_enabled_settings():
        assert oauth.google_enabled() is True


def test_verify_raises_when_not_configured():
    with google_disabled_settings(), pytest.raises(ValueError):
        oauth.verify_google_id_token("whatever")


def test_verify_google_auth_path_success(monkeypatch):
    # Mock google-auth modules since they may not be installed. Create proper
    # package modules (with __path__) so Python's import system accepts them.
    def _fake_package(name):
        mod = types.ModuleType(name)
        mod.__path__ = []
        mod.__file__ = f"<fake>{name}"
        return mod

    calls = {}

    def fake_verify(token, request, audience):
        calls["audience"] = audience
        return claims()

    google_mod = _fake_package("google")
    auth_mod = _fake_package("google.auth")
    transport_mod = _fake_package("google.auth.transport")
    requests_mod = types.ModuleType("google.auth.transport.requests")
    requests_mod.Request = lambda: None

    oauth2_mod = _fake_package("google.oauth2")
    id_token_mod = types.ModuleType("google.oauth2.id_token")
    id_token_mod.verify_oauth2_token = fake_verify

    monkeypatch.setitem(sys.modules, "google", google_mod)
    monkeypatch.setitem(sys.modules, "google.auth", auth_mod)
    monkeypatch.setitem(sys.modules, "google.auth.transport", transport_mod)
    monkeypatch.setitem(sys.modules, "google.auth.transport.requests", requests_mod)
    monkeypatch.setitem(sys.modules, "google.oauth2", oauth2_mod)
    monkeypatch.setitem(sys.modules, "google.oauth2.id_token", id_token_mod)

    import google.oauth2.id_token as google_id_token

    monkeypatch.setattr(google_id_token, "verify_oauth2_token", fake_verify)
    with google_enabled_settings():
        result = oauth.verify_google_id_token("tok")
    assert result["email"] == "gina@example.com"
    assert calls["audience"] == CLIENT_ID


def test_verify_google_auth_path_bad_issuer(monkeypatch):
    def _fake_package(name):
        mod = types.ModuleType(name)
        mod.__path__ = []
        mod.__file__ = f"<fake>{name}"
        return mod

    fake_id_token = types.ModuleType("google.oauth2.id_token")
    fake_id_token.verify_oauth2_token = lambda token, request, audience: claims(
        iss="https://evil.example.com"
    )

    google_mod = _fake_package("google")
    auth_mod = _fake_package("google.auth")
    transport_mod = _fake_package("google.auth.transport")
    requests_mod = types.ModuleType("google.auth.transport.requests")
    requests_mod.Request = lambda: None

    oauth2_mod = _fake_package("google.oauth2")

    monkeypatch.setitem(sys.modules, "google", google_mod)
    monkeypatch.setitem(sys.modules, "google.auth", auth_mod)
    monkeypatch.setitem(sys.modules, "google.auth.transport", transport_mod)
    monkeypatch.setitem(sys.modules, "google.auth.transport.requests", requests_mod)
    monkeypatch.setitem(sys.modules, "google.oauth2", oauth2_mod)
    monkeypatch.setitem(sys.modules, "google.oauth2.id_token", fake_id_token)

    import google.oauth2.id_token as google_id_token

    monkeypatch.setattr(
        google_id_token,
        "verify_oauth2_token",
        fake_id_token.verify_oauth2_token,
    )
    with google_enabled_settings(), pytest.raises(ValueError, match="issuer"):
        oauth.verify_google_id_token("tok")


def _force_pyjwt_path(monkeypatch):
    """Make `import google.auth...` fail so the PyJWT fallback runs."""
    monkeypatch.setitem(sys.modules, "google.auth.transport.requests", None)


class _FakeJWKClient:
    def __init__(self, url):
        self.url = url

    def get_signing_key_from_jwt(self, token):
        return types.SimpleNamespace(key="fake-public-key")


def test_verify_pyjwt_fallback_success(monkeypatch):
    _force_pyjwt_path(monkeypatch)
    import jwt as jwt_module

    monkeypatch.setattr(jwt_module, "PyJWKClient", _FakeJWKClient)
    monkeypatch.setattr(jwt_module, "decode", lambda *a, **k: claims())

    with google_enabled_settings():
        result = oauth.verify_google_id_token("tok")
    assert result["email"] == "gina@example.com"


def test_verify_pyjwt_fallback_bad_issuer(monkeypatch):
    _force_pyjwt_path(monkeypatch)
    import jwt as jwt_module

    monkeypatch.setattr(jwt_module, "PyJWKClient", _FakeJWKClient)
    monkeypatch.setattr(
        jwt_module, "decode", lambda *a, **k: claims(iss="https://evil.example.com")
    )

    with google_enabled_settings(), pytest.raises(ValueError, match="issuer"):
        oauth.verify_google_id_token("tok")


def test_verify_reports_missing_libraries(monkeypatch):
    _force_pyjwt_path(monkeypatch)
    monkeypatch.setitem(sys.modules, "jwt", None)

    with google_enabled_settings(), pytest.raises(ValueError, match="missing"):
        oauth.verify_google_id_token("tok")
