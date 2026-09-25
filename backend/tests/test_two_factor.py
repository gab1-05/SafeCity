"""
Two-factor login challenge tests.

The login endpoint issues a short-lived ``2fa_pending`` access token instead of
a usable session. ``StrictJWTAuthentication`` (the project default) rejects it
everywhere except the ``/auth/token/2fa/`` exchange, which returns real tokens
only after the second factor checks out.
"""

import base64
import time

import pytest
from django.urls import reverse
from rest_framework import status

from apps.accounts.two_factor import _hotp, generate_totp_secret

pytestmark = pytest.mark.django_db


def _totp_now(secret: str) -> str:
    """Current TOTP code for ``secret`` (same algorithm the app verifies)."""
    key = base64.b32decode(secret + "=" * (-len(secret) % 8))
    return f"{_hotp(key, int(time.time() // 30)):06d}"


@pytest.fixture
def two_factor_citizen(citizen):
    """Citizen with 2FA enabled and a known secret."""
    secret = generate_totp_secret()
    citizen.two_factor_enabled = True
    citizen.two_factor_secret = secret
    citizen.two_factor_recovery_codes = []
    citizen.save(update_fields=["two_factor_enabled", "two_factor_secret", "two_factor_recovery_codes"])
    return citizen


def _login(client, user):
    return client.post(
        reverse("auth-token"),
        {"email": user.email, "password": "Testpass123!"},
        format="json",
    )


def test_login_without_2fa_unchanged(client, citizen):
    response = _login(client, citizen)
    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data and "refresh" in response.data
    assert response.data.get("requires_2fa") is not True


def test_login_with_2fa_returns_challenge_only(client, two_factor_citizen):
    response = _login(client, two_factor_citizen)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["requires_2fa"] is True
    # A challenge access token is present, but no usable session yet.
    assert response.data.get("access")
    assert "refresh" not in response.data


def test_challenge_token_rejected_on_normal_endpoint(client, two_factor_citizen):
    challenge = _login(client, two_factor_citizen).data["access"]
    response = client.get(reverse("auth-me"), HTTP_AUTHORIZATION=f"Bearer {challenge}")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_verify_requires_challenge(client, two_factor_citizen):
    # Anonymous call: no challenge at all.
    response = client.post(
        reverse("auth-token-2fa"),
        {"token": _totp_now(two_factor_citizen.two_factor_secret)},
        format="json",
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # A normal (non-challenge) session token is also refused here.
    normal = _login(client, two_factor_citizen).data  # challenge response
    challenge = normal["access"]
    # Log in as a plain user to get a real access token.
    from apps.accounts.models import User, UserRole

    plain = User.objects.create_user(
        email="plain@test.local",
        password="Testpass123!",
        role=UserRole.CITIZEN,
        first_name="Plain",
        last_name="User",
    )
    real_token = _login(client, plain).data["access"]
    response = client.post(
        reverse("auth-token-2fa"),
        {"token": _totp_now(two_factor_citizen.two_factor_secret)},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {real_token}",
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert challenge  # sanity: challenge was issued above


def test_verify_with_valid_totp_returns_session(client, two_factor_citizen):
    challenge = _login(client, two_factor_citizen).data["access"]
    response = client.post(
        reverse("auth-token-2fa"),
        {"token": _totp_now(two_factor_citizen.two_factor_secret)},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {challenge}",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["user"]["email"] == two_factor_citizen.email
    assert response.data["user"]["role"] == two_factor_citizen.role
    assert response.data["access"] and response.data["refresh"]
    assert response.data["access"] != challenge  # new, non-challenge token

    # The returned token now works on a normal endpoint.
    me = client.get(
        reverse("auth-me"), HTTP_AUTHORIZATION=f"Bearer {response.data['access']}"
    )
    assert me.status_code == status.HTTP_200_OK


def test_verify_rejects_wrong_totp(client, two_factor_citizen):
    challenge = _login(client, two_factor_citizen).data["access"]
    response = client.post(
        reverse("auth-token-2fa"),
        {"token": "000000"},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {challenge}",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_verify_consumes_recovery_code(client, two_factor_citizen):
    from apps.accounts.two_factor import hash_recovery_code

    code = "AABBCCDD"
    two_factor_citizen.two_factor_recovery_codes = [hash_recovery_code(code)]
    two_factor_citizen.save(update_fields=["two_factor_recovery_codes"])

    challenge = _login(client, two_factor_citizen).data["access"]
    response = client.post(
        reverse("auth-token-2fa"),
        {"token": code},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {challenge}",
    )
    assert response.status_code == status.HTTP_200_OK

    two_factor_citizen.refresh_from_db()
    assert two_factor_citizen.two_factor_recovery_codes == []
