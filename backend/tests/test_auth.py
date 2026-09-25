"""
Authentication API tests: registration, login, lockout, rotation, sessions.
"""

import pytest
from django.urls import reverse
from rest_framework import status

from apps.accounts.models import User, UserRole

pytestmark = pytest.mark.django_db


def test_register_citizen(client):
    response = client.post(
        reverse("auth-register"),
        {
            "email": "new@test.local",
            "first_name": "New",
            "last_name": "Citizen",
            "password": "StrongPass123!",
            "accept_terms": True,
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    user = User.objects.get(email="new@test.local")
    assert user.role == UserRole.CITIZEN
    assert user.consents.count() == 1  # consent recorded


def test_register_requires_terms(client):
    response = client.post(
        reverse("auth-register"),
        {
            "email": "noterms@test.local",
            "first_name": "No",
            "last_name": "Terms",
            "password": "StrongPass123!",
            "accept_terms": False,
        },
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_login_success_and_role_claim(client, citizen):
    response = client.post(
        reverse("auth-token"),
        {"email": "citizen@test.local", "password": "Testpass123!"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["user"]["role"] == UserRole.CITIZEN
    assert "access" in response.data and "refresh" in response.data


def test_login_wrong_password(client, citizen):
    response = client.post(
        reverse("auth-token"),
        {"email": "citizen@test.local", "password": "wrong-password"},
        format="json",
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_lockout_after_repeated_failures(client, citizen):
    for _ in range(5):
        client.post(
            reverse("auth-token"),
            {"email": "citizen@test.local", "password": "bad"},
            format="json",
        )
    citizen.refresh_from_db()
    assert citizen.locked_until is not None
    # Even the correct password is refused while locked (423 Locked)
    response = client.post(
        reverse("auth-token"),
        {"email": "citizen@test.local", "password": "Testpass123!"},
        format="json",
    )
    assert response.status_code == status.HTTP_423_LOCKED


def test_refresh_rotation_blacklists_old_token(client, citizen):
    login = client.post(
        reverse("auth-token"),
        {"email": "citizen@test.local", "password": "Testpass123!"},
        format="json",
    )
    old_refresh = login.data["refresh"]
    response = client.post(reverse("auth-token-refresh"), {"refresh": old_refresh}, format="json")
    assert response.status_code == status.HTTP_200_OK
    # Old refresh must now be blacklisted
    reuse = client.post(reverse("auth-token-refresh"), {"refresh": old_refresh}, format="json")
    assert reuse.status_code == status.HTTP_401_UNAUTHORIZED


def test_logout_blacklists_session(client, citizen):
    login = client.post(
        reverse("auth-token"),
        {"email": "citizen@test.local", "password": "Testpass123!"},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    response = client.post(reverse("auth-logout"), {"refresh": login.data["refresh"]})
    assert response.status_code == status.HTTP_200_OK
    # Refresh is now unusable
    reuse = client.post(
        reverse("auth-token-refresh"), {"refresh": login.data["refresh"]}, format="json"
    )
    assert reuse.status_code == status.HTTP_401_UNAUTHORIZED


def test_me_requires_auth(client):
    response = client.get(reverse("auth-me"))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_me_returns_profile(client, citizen):
    client.force_authenticate(user=citizen)
    response = client.get(reverse("auth-me"))
    assert response.status_code == status.HTTP_200_OK
    assert response.data["email"] == "citizen@test.local"


def test_password_reset_does_not_leak_existence(client, citizen):
    response = client.post(
        reverse("auth-password-reset"), {"email": "citizen@test.local"}, format="json"
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    # Unknown email returns identical response (no enumeration)
    unknown = client.post(
        reverse("auth-password-reset"), {"email": "ghost@test.local"}, format="json"
    )
    assert unknown.status_code == status.HTTP_202_ACCEPTED
