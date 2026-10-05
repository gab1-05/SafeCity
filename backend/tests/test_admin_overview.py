"""Admin overview regression tests.

Covers the /api/v1/admin/overview/ 500 caused by an unscoped
`status` lookup inside the department `open_incidents` annotation
(FieldError: Cannot resolve keyword 'status' into field).
"""

import pytest
from rest_framework import status

pytestmark = pytest.mark.django_db


class TestAdminOverview:
    def test_citizen_forbidden(self, client, citizen):
        client.force_authenticate(user=citizen)
        response = client.get("/api/v1/admin/overview/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_overview_payload(self, client, admin, incident_factory):
        incident_factory()
        client.force_authenticate(user=admin)
        response = client.get("/api/v1/admin/overview/")
        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert set(payload) == {
            "users",
            "incidents",
            "departments",
            "deletion_requests",
            "recent_audit",
            "sla_breaches",
        }
        assert payload["users"]["total"] >= 1
        assert payload["incidents"]["total"] >= 1
        assert isinstance(payload["departments"], list)
        assert payload["departments"], "seeded department missing from overview"
