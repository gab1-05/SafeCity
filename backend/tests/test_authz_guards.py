"""
Authz guard regressions for the P0 fixes.

Every test here maps to a previously-open privilege hole:
- any authenticated user could escalate / merge / assign any incident
- any authenticated user could write SLA + escalation rules
- malformed rating crashed with 500 instead of 400
- reference data (wards/zones) required auth, breaking public pages
"""

import pytest
from django.urls import reverse
from rest_framework import status

pytestmark = pytest.mark.django_db


DENIED = {
    status.HTTP_400_BAD_REQUEST,  # guard WorkflowError
    status.HTTP_403_FORBIDDEN,  # permission class
    status.HTTP_404_NOT_FOUND,  # role-scoped queryset hides the object
}


def _action(name, pk):
    return reverse(f"incidents-{name}-action", args=[str(pk)])


class TestEscalateGuards:
    def test_citizen_cannot_escalate(self, client, citizen, incident):
        client.force_authenticate(user=citizen)
        response = client.post(_action("escalate", incident.pk), {}, format="json")
        assert response.status_code in DENIED
        incident.refresh_from_db()
        assert incident.status == "submitted"

    def test_volunteer_cannot_escalate(self, client, volunteer, incident):
        client.force_authenticate(user=volunteer)
        response = client.post(_action("escalate", incident.pk), {}, format="json")
        assert response.status_code in DENIED

    def test_other_department_staff_cannot_escalate(
        self, client, other_dept_staff, incident
    ):
        client.force_authenticate(user=other_dept_staff)
        response = client.post(_action("escalate", incident.pk), {}, format="json")
        assert response.status_code in DENIED

    def test_admin_can_escalate(self, client, admin, incident):
        client.force_authenticate(user=admin)
        response = client.post(
            _action("escalate", incident.pk), {"reason": "test"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK


class TestMergeGuards:
    def test_citizen_cannot_merge(self, client, citizen, incident_factory):
        dup = incident_factory(reporter=citizen)
        parent = incident_factory()
        client.force_authenticate(user=citizen)
        response = client.post(
            _action("merge", dup.pk), {"parent_id": str(parent.pk)}, format="json"
        )
        assert response.status_code in DENIED
        dup.refresh_from_db()
        assert dup.status == "submitted"

    def test_volunteer_cannot_merge(self, client, volunteer, incident_factory):
        dup = incident_factory()
        parent = incident_factory()
        client.force_authenticate(user=volunteer)
        response = client.post(
            _action("merge", dup.pk), {"parent_id": str(parent.pk)}, format="json"
        )
        assert response.status_code in DENIED

    def test_cannot_merge_into_closed_parent(
        self, client, admin, incident_factory
    ):
        dup = incident_factory()
        parent = incident_factory(status="closed")
        client.force_authenticate(user=admin)
        response = client.post(
            _action("merge", dup.pk), {"parent_id": str(parent.pk)}, format="json"
        )
        assert response.status_code in DENIED


class TestAssignGuards:
    def test_citizen_cannot_assign(self, client, citizen, incident, staff):
        client.force_authenticate(user=citizen)
        response = client.post(
            _action("assign", incident.pk), {"assignee_id": str(staff.pk)}, format="json"
        )
        assert response.status_code in DENIED

    def test_volunteer_cannot_assign(self, client, volunteer, incident, staff):
        client.force_authenticate(user=volunteer)
        response = client.post(
            _action("assign", incident.pk), {"assignee_id": str(staff.pk)}, format="json"
        )
        assert response.status_code in DENIED


class TestConfigWriteGuards:
    def test_citizen_cannot_create_sla_rule(self, client, citizen):
        client.force_authenticate(user=citizen)
        response = client.post(
            reverse("sla-config-list"),
            {"severity": "high", "resolution_hours": 24},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_citizen_cannot_create_escalation_rule(self, client, citizen):
        client.force_authenticate(user=citizen)
        response = client.post(
            reverse("escalation-rules-list"),
            {"name": "x", "priority": 1},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_create_sla_rule(self, client, admin, category):
        client.force_authenticate(user=admin)
        response = client.post(
            reverse("sla-config-list"),
            {
                "category": str(category.pk),
                "severity": "low",
                "response_hours": 24,
                "resolution_hours": 120,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED


class TestInputGuards:
    def test_malformed_rating_is_400_not_500(
        self, client, citizen, incident_factory
    ):
        incident = incident_factory(reporter=citizen, status="resolved")
        client.force_authenticate(user=citizen)
        response = client.post(
            _action("confirm", incident.pk), {"rating": "abc"}, format="json"
        )
        assert response.status_code in DENIED

    def test_anonymous_can_list_wards_and_zones(self, client):
        assert client.get(reverse("wards-list")).status_code == status.HTTP_200_OK
        assert client.get(reverse("zones-list")).status_code == status.HTTP_200_OK
