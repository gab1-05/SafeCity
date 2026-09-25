"""
Role-based access control tests: the permission matrix, enforced server-side.
"""

import pytest
from django.urls import reverse
from rest_framework import status

from apps.accounts.models import UserRole
from apps.accounts.permissions import can_view_incident, can_view_internal_notes

pytestmark = pytest.mark.django_db


class TestIncidentVisibility:
    def test_citizen_sees_own_incident(self, citizen, incident):
        assert can_view_incident(citizen, incident) is True

    def test_citizen_cannot_see_others(self, citizen, incident_factory):
        other = incident_factory()  # no reporter → not owned by citizen
        assert can_view_incident(citizen, other) is False

    def test_department_staff_sees_own_department(self, staff, incident):
        assert can_view_incident(staff, incident) is True

    def test_department_staff_blocked_from_other_department(self, other_dept_staff, incident):
        assert can_view_incident(other_dept_staff, incident) is False

    def test_admin_sees_everything(self, admin, incident):
        assert can_view_incident(admin, incident) is True

    def test_responder_sees_high_severity(self, responder, incident):
        assert incident.severity == "high"
        assert can_view_incident(responder, incident) is True

    def test_volunteer_sees_verified_only(self, volunteer, incident_factory):
        draft = incident_factory(status="submitted")
        assert can_view_incident(volunteer, draft) is False
        verified = incident_factory(status="verified")
        assert can_view_incident(volunteer, verified) is True

    def test_anonymous_user_blocked_from_private_api(self, client, incident):
        response = client.get(f"/api/v1/incidents/{incident.id}/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestListScoping:
    def test_citizen_list_only_own(self, client, citizen, incident_factory):
        mine = incident_factory(reporter=citizen)
        incident_factory()  # someone else's
        client.force_authenticate(user=citizen)
        response = client.get(reverse("incidents-list"))
        ids = [r["id"] for r in response.data["results"]]
        assert str(mine.id) in ids
        assert len(ids) == 1

    def test_staff_scoped_to_department(self, client, staff, incident_factory, category):
        mine = incident_factory(category=category)
        incident_factory(status="verified")  # different department via factory default
        client.force_authenticate(user=staff)
        response = client.get(reverse("incidents-list"))
        ids = [r["id"] for r in response.data["results"]]
        assert str(mine.id) in ids

    def test_admin_sees_all(self, client, admin, incident_factory):
        incident_factory()
        incident_factory(status="verified")
        client.force_authenticate(user=admin)
        response = client.get(reverse("incidents-list"))
        assert response.data["count"] >= 2


class TestInternalNotes:
    def test_staff_sees_internal_notes(self, staff, incident):
        assert can_view_internal_notes(staff, incident) is True

    def test_citizen_never_sees_internal_notes(self, citizen, incident):
        assert can_view_internal_notes(citizen, incident) is False

    def test_admin_sees_internal_notes(self, admin, incident):
        assert can_view_internal_notes(admin, incident) is True


class TestUserManagement:
    def test_admin_can_change_roles(self, client, admin, citizen):
        client.force_authenticate(user=admin)
        response = client.post(
            f"/api/v1/users/{citizen.id}/role/",
            {"role": UserRole.DEPARTMENT_STAFF},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        citizen.refresh_from_db()
        assert citizen.role == UserRole.DEPARTMENT_STAFF

    def test_citizen_cannot_change_roles(self, client, citizen, volunteer):
        client.force_authenticate(user=citizen)
        response = client.post(
            f"/api/v1/users/{volunteer.id}/role/", {"role": "city_admin"}, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_cannot_deactivate_self(self, client, admin):
        client.force_authenticate(user=admin)
        response = client.post(f"/api/v1/users/{admin.id}/deactivate/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_admin_can_view_and_reactivate_inactive_users(self, client, admin, citizen):
        citizen.is_active = False
        citizen.save(update_fields=["is_active"])
        client.force_authenticate(user=admin)
        response = client.get("/api/v1/users/")
        assert response.status_code == status.HTTP_200_OK
        ids = [user["id"] for user in response.data["results"]]
        assert str(citizen.id) in ids

        unlock = client.post(f"/api/v1/users/{citizen.id}/deactivate/")
        assert unlock.status_code == status.HTTP_200_OK
        citizen.refresh_from_db()
        assert citizen.is_active is True

    def test_admin_can_unlock_locked_user(self, client, admin, citizen):
        citizen.locked_until = "2099-01-01T00:00:00Z"
        citizen.save(update_fields=["locked_until"])
        client.force_authenticate(user=admin)
        response = client.post(f"/api/v1/users/{citizen.id}/unlock/")
        assert response.status_code == status.HTTP_200_OK
        citizen.refresh_from_db()
        assert citizen.locked_until is None


class TestAnalyticsAccess:
    def test_citizen_blocked_from_analytics(self, client, citizen):
        client.force_authenticate(user=citizen)
        response = client.get("/api/v1/analytics/summary/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_read_analytics(self, client, admin):
        client.force_authenticate(user=admin)
        response = client.get("/api/v1/analytics/summary/")
        assert response.status_code == status.HTTP_200_OK

    def test_staff_scoped_analytics(self, client, staff):
        client.force_authenticate(user=staff)
        response = client.get("/api/v1/analytics/summary/")
        assert response.status_code == status.HTTP_200_OK
