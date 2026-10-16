"""
Two-factor authentication flows: enrollment, login challenge exchange,
disable (TOTP + recovery code), recovery-code regeneration.

TOTP codes are computed with the same HOTP primitive the server verifies,
using the current 30-second time step.
"""

import base64
import time
from datetime import timedelta

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.accounts.two_factor import _hotp

pytestmark = pytest.mark.django_db

PASSWORD = "Testpass123!"


# ── TOTP primitive ─────────────────────────────────────────────────────


def test_verify_totp_accepts_leading_zero_codes(monkeypatch):
    """Regression: codes like 012345 are valid 6-digit TOTP codes."""
    from apps.accounts import two_factor

    monkeypatch.setattr(two_factor, "_hotp", lambda key, counter, digits=6: 12345)
    secret = two_factor.generate_totp_secret()
    assert two_factor.verify_totp_token(secret, "012345") is True
    assert two_factor.verify_totp_token(secret, "123456") is False


def test_verify_totp_rejects_malformed_input():
    from apps.accounts import two_factor

    secret = "JBSWY3DPEHPK3PXP"
    assert two_factor.verify_totp_token(secret, "12345") is False  # 5 digits
    assert two_factor.verify_totp_token(secret, "abcdef") is False
    assert two_factor.verify_totp_token(secret, "1234567") is False
    assert two_factor.verify_totp_token("not-base32!!", "123456") is False


def current_totp(secret: str) -> str:
    key = base64.b32decode(secret.upper() + "=" * (-len(secret) % 8))
    return f"{_hotp(key, int(time.time() // 30)):06d}"


def bad_totp(secret: str) -> str:
    """A 6-digit code that is not the current valid one."""
    good = current_totp(secret)
    return "000000" if good != "000000" else "111111"


def _enable_2fa(client, citizen):
    """Run the full enrollment flow; returns (secret, recovery_codes)."""
    client.force_authenticate(user=citizen)
    setup = client.get(reverse("auth-2fa-setup"))
    assert setup.status_code == status.HTTP_200_OK
    secret = setup.data["secret"]

    response = client.post(
        reverse("auth-2fa-setup"), {"token": current_totp(secret)}, format="json"
    )
    assert response.status_code == status.HTTP_200_OK, response.data
    client.force_authenticate(user=None)
    return secret, response.data["recovery_codes"]


def _challenge_token(user):
    challenge = AccessToken.for_user(user)
    challenge.set_exp(lifetime=timedelta(minutes=2))
    challenge["2fa_pending"] = True
    return str(challenge)


def test_2fa_setup_lifecycle(client, citizen):
    client.force_authenticate(user=citizen)
    setup = client.get(reverse("auth-2fa-setup"))
    assert setup.status_code == status.HTTP_200_OK
    secret = setup.data["secret"]
    assert secret
    assert len(setup.data["recovery_codes"]) == 10
    assert setup.data["otpauth_uri"].startswith("otpauth://totp/SafeCity:")

    # Wrong token rejected, 2FA stays disabled.
    response = client.post(
        reverse("auth-2fa-setup"), {"token": bad_totp(secret)}, format="json"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    citizen.refresh_from_db()
    assert citizen.two_factor_enabled is False

    # Correct token enables 2FA and returns the plaintext recovery codes.
    response = client.post(
        reverse("auth-2fa-setup"), {"token": current_totp(secret)}, format="json"
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["recovery_codes"]) == 10
    citizen.refresh_from_db()
    assert citizen.two_factor_enabled is True
    assert citizen.two_factor_secret == secret

    # Re-running setup on an enabled account is rejected.
    assert client.get(reverse("auth-2fa-setup")).status_code == status.HTTP_400_BAD_REQUEST
    assert (
        client.post(reverse("auth-2fa-setup"), {"token": "123456"}, format="json").status_code
        == status.HTTP_400_BAD_REQUEST
    )


def test_2fa_setup_post_without_session(client, citizen):
    client.force_authenticate(user=citizen)
    response = client.post(reverse("auth-2fa-setup"), {"token": "123456"}, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_2fa_login_challenge_and_verify(client, citizen):
    secret, _ = _enable_2fa(client, citizen)

    login = client.post(
        reverse("auth-token"),
        {"email": citizen.email, "password": PASSWORD},
        format="json",
    )
    assert login.status_code == status.HTTP_200_OK
    assert login.data["requires_2fa"] is True
    assert "refresh" not in login.data
    challenge = login.data["access"]

    # The challenge token authenticates ONLY the 2FA exchange endpoint.
    me = client.get(reverse("auth-me"), HTTP_AUTHORIZATION=f"Bearer {challenge}")
    assert me.status_code == status.HTTP_401_UNAUTHORIZED

    # No challenge token at all.
    anon = client.post(reverse("auth-token-2fa"), {"token": "123456"}, format="json")
    assert anon.status_code == status.HTTP_401_UNAUTHORIZED

    # A regular (non-pending) access token is rejected too.
    regular = str(RefreshToken.for_user(citizen).access_token)
    regular_resp = client.post(
        reverse("auth-token-2fa"),
        {"token": "123456"},
        HTTP_AUTHORIZATION=f"Bearer {regular}",
        format="json",
    )
    assert regular_resp.status_code == status.HTTP_401_UNAUTHORIZED

    # Wrong TOTP.
    bad = client.post(
        reverse("auth-token-2fa"),
        {"token": bad_totp(secret)},
        HTTP_AUTHORIZATION=f"Bearer {challenge}",
        format="json",
    )
    assert bad.status_code == status.HTTP_400_BAD_REQUEST

    # Correct TOTP issues a full session.
    ok = client.post(
        reverse("auth-token-2fa"),
        {"token": current_totp(secret)},
        HTTP_AUTHORIZATION=f"Bearer {challenge}",
        format="json",
    )
    assert ok.status_code == status.HTTP_200_OK
    assert "access" in ok.data and "refresh" in ok.data
    assert ok.data["user"]["email"] == citizen.email


def test_2fa_verify_rejected_when_not_enabled(client, citizen):
    response = client.post(
        reverse("auth-token-2fa"),
        {"token": "123456"},
        HTTP_AUTHORIZATION=f"Bearer {_challenge_token(citizen)}",
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_2fa_login_with_recovery_code(client, citizen):
    _, recovery_codes = _enable_2fa(client, citizen)

    login = client.post(
        reverse("auth-token"), {"email": citizen.email, "password": PASSWORD}, format="json"
    )
    challenge = login.data["access"]

    ok = client.post(
        reverse("auth-token-2fa"),
        {"token": recovery_codes[0]},
        HTTP_AUTHORIZATION=f"Bearer {challenge}",
        format="json",
    )
    assert ok.status_code == status.HTTP_200_OK

    # The used recovery code is consumed.
    citizen.refresh_from_db()
    assert len(citizen.two_factor_recovery_codes) == 9


def test_2fa_disable_paths(client, citizen):
    client.force_authenticate(user=citizen)
    # Not enabled yet.
    response = client.post(reverse("auth-2fa-disable"), {"token": "123456"}, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    # Disable with a recovery code.
    _, recovery_codes = _enable_2fa(client, citizen)
    client.force_authenticate(user=citizen)
    bad = client.post(
        reverse("auth-2fa-disable"), {"token": "ZZZZZZZZ"}, format="json"
    )
    assert bad.status_code == status.HTTP_400_BAD_REQUEST
    ok = client.post(
        reverse("auth-2fa-disable"), {"token": recovery_codes[0]}, format="json"
    )
    assert ok.status_code == status.HTTP_200_OK
    citizen.refresh_from_db()
    assert citizen.two_factor_enabled is False
    assert citizen.two_factor_recovery_codes == []

    # Disable with a TOTP code.
    secret, _ = _enable_2fa(client, citizen)
    client.force_authenticate(user=citizen)
    ok = client.post(
        reverse("auth-2fa-disable"), {"token": current_totp(secret)}, format="json"
    )
    assert ok.status_code == status.HTTP_200_OK
    citizen.refresh_from_db()
    assert citizen.two_factor_enabled is False


def test_2fa_regenerate_recovery_codes(client, citizen):
    client.force_authenticate(user=citizen)
    response = client.post(
        reverse("auth-2fa-recovery-regenerate"), {"token": "123456"}, format="json"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    secret, first_codes = _enable_2fa(client, citizen)
    client.force_authenticate(user=citizen)

    bad = client.post(
        reverse("auth-2fa-recovery-regenerate"), {"token": bad_totp(secret)}, format="json"
    )
    assert bad.status_code == status.HTTP_400_BAD_REQUEST

    ok = client.post(
        reverse("auth-2fa-recovery-regenerate"),
        {"token": current_totp(secret)},
        format="json",
    )
    assert ok.status_code == status.HTTP_200_OK
    assert len(ok.data["recovery_codes"]) == 10
    assert ok.data["recovery_codes"] != first_codes

    # Old recovery codes no longer work.
    citizen.refresh_from_db()
    assert len(citizen.two_factor_recovery_codes) == 10
