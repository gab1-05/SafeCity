"""
Role-request workflow tests: signup with a role choice creates a pending
request (account stays citizen); admins approve/reject; privilege
escalation attempts are refused.
"""

import pytest
from django.urls import reverse
from rest_framework import status

from apps.accounts.models import RoleRequest, User

pytestmark = pytest.mark.django_db


def _register(client, **overrides):
    payload = {
        "email": "newuser@test.local",
        "first_name": "New",
        "last_name": "User",
        "password": "Testpass123!",
        "accept_terms": True,
    }
    payload.update(overrides)
    return client.post(reverse("auth-register"), payload, format="json")


class TestSignupRoleRequest:
    def test_plain_signup_stays_citizen_without_request(self, client):
        response = _register(client)
        assert response.status_code == status.HTTP_201_CREATED
        user = User.objects.get(email="newuser@test.local")
        assert user.role == "citizen"
        assert RoleRequest.objects.filter(user=user).count() == 0

    def test_signup_with_role_creates_pending_request(self, client):
        response = _register(client, requested_role="volunteer", role_request_reason="I help out")
        assert response.status_code == status.HTTP_201_CREATED
        user = User.objects.get(email="newuser@test.local")
        assert user.role == "citizen"  # never granted immediately
        req = RoleRequest.objects.get(user=user)
        assert req.requested_role == "volunteer"
        assert req.status == "pending"

    def test_signup_cannot_request_admin(self, client):
        response = _register(client, requested_role="city_admin")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_signup_cannot_request_superuser(self, client):
        response = _register(client, requested_role="superuser")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestRoleRequestReview:
    def test_user_can_request_from_profile(self, client, citizen):
        client.force_authenticate(user=citizen)
        response = client.post(
            reverse("role-requests"), {"requested_role": "volunteer"}, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert RoleRequest.objects.get(user=citizen).status == "pending"

    def test_duplicate_pending_rejected(self, client, citizen):
        client.force_authenticate(user=citizen)
        client.post(reverse("role-requests"), {"requested_role": "volunteer"}, format="json")
        response = client.post(
            reverse("role-requests"), {"requested_role": "volunteer"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_citizen_cannot_review(self, client, citizen):
        other = User.objects.create_user(
            email="other@test.local", password="Testpass123!", first_name="O", last_name="U"
        )
        req = RoleRequest.objects.create(user=other, requested_role="volunteer")
        client.force_authenticate(user=citizen)
        response = client.post(
            reverse("role-request-review", kwargs={"pk": req.pk}),
            {"decision": "approve"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_approve_applies_role(self, client, citizen, admin, department):
        req = RoleRequest.objects.create(
            user=citizen, requested_role="department_staff", department=department
        )
        client.force_authenticate(user=admin)
        response = client.post(
            reverse("role-request-review", kwargs={"pk": req.pk}),
            {"decision": "approve"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        citizen.refresh_from_db()
        assert citizen.role == "department_staff"
        assert citizen.department_id == department.id
        req.refresh_from_db()
        assert req.status == "approved"
        assert req.reviewed_by_id == admin.id

    def test_admin_reject_keeps_role(self, client, citizen, admin):
        req = RoleRequest.objects.create(user=citizen, requested_role="volunteer")
        client.force_authenticate(user=admin)
        response = client.post(
            reverse("role-request-review", kwargs={"pk": req.pk}),
            {"decision": "reject"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        citizen.refresh_from_db()
        assert citizen.role == "citizen"
        req.refresh_from_db()
        assert req.status == "rejected"

    def test_admin_sees_pending_queue(self, client, citizen, admin):
        RoleRequest.objects.create(user=citizen, requested_role="volunteer")
        client.force_authenticate(user=admin)
        response = client.get(reverse("role-requests"))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["requested_role"] == "volunteer"
