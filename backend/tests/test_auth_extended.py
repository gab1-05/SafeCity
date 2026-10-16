"""
Extended authentication flows: password reset confirm, change password,
session management, logout edge cases, profile update, lockout response.
"""

import re
import uuid

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

pytestmark = pytest.mark.django_db


def _login(client, email, password="Testpass123!"):
    return client.post(
        reverse("auth-token"), {"email": email, "password": password}, format="json"
    )


def _reset_uid_token(user):
    """Issue a reset link the same way the request view does."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    from django.contrib.auth.tokens import default_token_generator

    return uid, default_token_generator.make_token(user)


def test_password_reset_request_sends_email_and_confirm_works(client, citizen):
    response = client.post(
        reverse("auth-password-reset"), {"email": "citizen@test.local"}, format="json"
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert len(mail.outbox) == 1

    match = re.search(r"uid=([^&]+)&token=([\w-]+)", mail.outbox[0].body)
    assert match, "reset email must contain uid and token"
    uid, token = match.group(1), match.group(2)

    response = client.post(
        reverse("auth-password-reset-confirm"),
        {"uid": uid, "token": token, "password": "BrandNewPass987!"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK

    citizen.refresh_from_db()
    assert citizen.check_password("BrandNewPass987!")
    # The new password actually logs in.
    assert _login(client, "citizen@test.local", "BrandNewPass987!").status_code == 200


def test_password_reset_confirm_invalid_uid(client):
    response = client.post(
        reverse("auth-password-reset-confirm"),
        {"uid": "!!!not-base64!!!", "token": "x", "password": "BrandNewPass987!"},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_password_reset_confirm_unknown_user(client):
    uid = urlsafe_base64_encode(force_bytes(uuid.uuid4()))
    response = client.post(
        reverse("auth-password-reset-confirm"),
        {"uid": uid, "token": "whatever", "password": "BrandNewPass987!"},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_password_reset_confirm_bad_token(client, citizen):
    uid, _ = _reset_uid_token(citizen)
    response = client.post(
        reverse("auth-password-reset-confirm"),
        {"uid": uid, "token": "deadbeef", "password": "BrandNewPass987!"},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    citizen.refresh_from_db()
    assert citizen.check_password("Testpass123!")


def test_change_password_requires_current_and_blacklists_sessions(client, citizen):
    assert _login(client, "citizen@test.local").status_code == 200
    client.force_authenticate(user=citizen)

    response = client.post(
        reverse("auth-password-change"),
        {"current_password": "WrongPassword!", "new_password": "AnotherPass456!"},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    response = client.post(
        reverse("auth-password-change"),
        {"current_password": "Testpass123!", "new_password": "AnotherPass456!"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    citizen.refresh_from_db()
    assert citizen.check_password("AnotherPass456!")
    assert BlacklistedToken.objects.filter(token__user=citizen).count() >= 1


def test_session_list_and_revoke(client, citizen):
    assert _login(client, "citizen@test.local").status_code == 200
    client.force_authenticate(user=citizen)

    response = client.get(reverse("auth-sessions"))
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) >= 1
    session_id = response.data[0]["id"]
    assert response.data[0]["active"] is True

    response = client.delete(reverse("auth-session-delete", args=[session_id]))
    assert response.status_code == status.HTTP_200_OK

    response = client.get(reverse("auth-sessions"))
    row = next(r for r in response.data if str(r["id"]) == str(session_id))
    assert row["active"] is False


def test_session_revoke_unknown_id_404(client, citizen):
    client.force_authenticate(user=citizen)
    response = client.delete(reverse("auth-session-delete", args=[999_999]))
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_session_revoke_other_users_session_404(client, citizen, admin):
    assert _login(client, "admin@test.local").status_code == 200
    admin_token = OutstandingToken.objects.filter(user=admin).first()
    assert admin_token is not None

    client.force_authenticate(user=citizen)
    response = client.delete(reverse("auth-session-delete", args=[admin_token.id]))
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_logout_edge_cases(client, citizen):
    client.force_authenticate(user=citizen)
    # Invalid token still logs out (blacklisting is best-effort).
    response = client.post(reverse("auth-logout"), {"refresh": "not-a-token"}, format="json")
    assert response.status_code == status.HTTP_200_OK
    # Missing token is a client error.
    response = client.post(reverse("auth-logout"), {}, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_me_patch_updates_profile(client, citizen):
    client.force_authenticate(user=citizen)
    response = client.patch(
        reverse("auth-me"),
        {"first_name": "Renamed", "phone": "+919999900000"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    citizen.refresh_from_db()
    assert citizen.first_name == "Renamed"
    assert citizen.phone == "+919999900000"


def test_locked_account_login_returns_423(client, citizen):
    citizen.locked_until = timezone.now() + timezone.timedelta(minutes=10)
    citizen.save(update_fields=["locked_until"])

    response = _login(client, "citizen@test.local", "Whatever!123")
    assert response.status_code == status.HTTP_423_LOCKED
    assert response.data["code"] == "account_locked"


def test_successful_login_clears_failed_attempts(client, citizen):
    citizen.failed_login_count = 3
    citizen.save(update_fields=["failed_login_count"])

    assert _login(client, "citizen@test.local").status_code == 200
    citizen.refresh_from_db()
    assert citizen.failed_login_count == 0
    assert citizen.locked_until is None
