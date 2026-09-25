"""
Workflow regression tests for the audit fixes:

- new transitions: verified → submitted (reporter reopen) and
  awaiting_info → assigned (staff rejects the info request);
- dead-end reverts to draft that must stay rejected;
- self-assignment rejection;
- notification fan-out on verified → assigned and reporter updates on
  in_progress → resolved / verified → rejected.
"""

import pytest
from rest_framework import status

from apps.accounts.models import User, UserRole
from apps.incidents.models import IncidentStatus
from apps.incidents.services import (
    WorkflowError,
    assign_incident,
    change_status,
)
from apps.notifications.models import Notification

pytestmark = pytest.mark.django_db


def _stranger():
    return User.objects.create_user(
        email="stranger@test.local", password="Testpass123!", role=UserRole.CITIZEN
    )


class TestNewTransitions:
    def test_reporter_resubmits_own_verified_incident(self, citizen, incident_factory):
        incident = incident_factory(reporter=citizen, status=IncidentStatus.VERIFIED)
        change_status(incident=incident, to_status=IncidentStatus.SUBMITTED, user=citizen)
        incident.refresh_from_db()
        assert incident.status == IncidentStatus.SUBMITTED

    def test_citizen_cannot_resubmit_someone_elses_verified(self, citizen, incident_factory):
        incident = incident_factory(reporter=citizen, status=IncidentStatus.VERIFIED)
        with pytest.raises(WorkflowError):
            change_status(
                incident=incident, to_status=IncidentStatus.SUBMITTED, user=_stranger()
            )

    def test_citizen_cannot_submit_someone_elses_draft(self, citizen, incident_factory):
        incident = incident_factory(reporter=citizen, status=IncidentStatus.DRAFT)
        with pytest.raises(WorkflowError):
            change_status(
                incident=incident, to_status=IncidentStatus.SUBMITTED, user=_stranger()
            )

    def test_citizen_submits_own_draft(self, citizen, incident_factory):
        incident = incident_factory(reporter=citizen, status=IncidentStatus.DRAFT)
        change_status(incident=incident, to_status=IncidentStatus.SUBMITTED, user=citizen)
        incident.refresh_from_db()
        assert incident.status == IncidentStatus.SUBMITTED

    def test_staff_rejects_info_request_back_to_assigned(self, staff, incident_factory):
        incident = incident_factory(status=IncidentStatus.ASSIGNED)
        change_status(incident=incident, to_status=IncidentStatus.AWAITING_INFO, user=staff)
        change_status(incident=incident, to_status=IncidentStatus.ASSIGNED, user=staff)
        incident.refresh_from_db()
        assert incident.status == IncidentStatus.ASSIGNED

    def test_citizen_cannot_drive_awaiting_info_to_assigned(self, citizen, incident_factory):
        incident = incident_factory(status=IncidentStatus.AWAITING_INFO)
        with pytest.raises(WorkflowError):
            change_status(incident=incident, to_status=IncidentStatus.ASSIGNED, user=citizen)


class TestRemovedDeadEnds:
    @pytest.mark.parametrize("from_status", ["submitted", "under_review", "verified"])
    def test_cannot_revert_to_draft(self, admin, incident_factory, from_status):
        incident = incident_factory(status=from_status)
        with pytest.raises(WorkflowError):
            change_status(incident=incident, to_status=IncidentStatus.DRAFT, user=admin)


class TestSelfAssignment:
    def test_staff_cannot_assign_incident_to_self(self, staff, incident_factory):
        incident = incident_factory(status=IncidentStatus.VERIFIED)
        with pytest.raises(WorkflowError) as excinfo:
            assign_incident(incident=incident, assignee=staff, user=staff)
        assert "cannot assign an incident to yourself" in str(excinfo.value)
        incident.refresh_from_db()
        assert incident.assigned_staff is None

    def test_self_assignment_rejected_via_api(self, client, staff, incident_factory):
        incident = incident_factory(status=IncidentStatus.VERIFIED)
        client.force_authenticate(user=staff)
        response = client.post(
            f"/api/v1/incidents/{incident.id}/assign/",
            {"assignee_id": str(staff.id)},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "yourself" in str(response.data["detail"])

    def test_admin_still_assigns_staff(self, admin, staff, incident_factory):
        incident = incident_factory(status=IncidentStatus.VERIFIED)
        assign_incident(incident=incident, assignee=staff, user=admin)
        incident.refresh_from_db()
        assert incident.assigned_staff == staff
        assert incident.status == IncidentStatus.ASSIGNED


class TestTransitionNotifications:
    def test_verified_to_assigned_notifies_department_staff(
        self, admin, staff, incident_factory
    ):
        incident = incident_factory(status=IncidentStatus.VERIFIED)
        change_status(incident=incident, to_status=IncidentStatus.ASSIGNED, user=admin)
        assert Notification.objects.filter(
            recipient=staff, verb="incident.assigned", incident=incident
        ).exists()

    def test_assign_action_notifies_remaining_department_staff(
        self, admin, staff, incident_factory
    ):
        incident = incident_factory(status=IncidentStatus.VERIFIED)
        colleague = User.objects.create_user(
            email="colleague@test.local",
            password="Testpass123!",
            role=UserRole.DEPARTMENT_STAFF,
            department=incident.department,
        )
        assign_incident(incident=incident, assignee=staff, user=admin)
        assert Notification.objects.filter(
            recipient=colleague, verb="incident.assigned", incident=incident
        ).exists()

    def test_in_progress_to_resolved_notifies_reporter(self, staff, citizen, incident_factory):
        incident = incident_factory(reporter=citizen, status=IncidentStatus.IN_PROGRESS)
        change_status(incident=incident, to_status=IncidentStatus.RESOLVED, user=staff)
        assert Notification.objects.filter(
            recipient=citizen, verb="incident.resolved", incident=incident
        ).exists()

    def test_submitted_to_rejected_notifies_reporter(self, admin, citizen, incident_factory):
        incident = incident_factory(reporter=citizen, status=IncidentStatus.SUBMITTED)
        change_status(incident=incident, to_status=IncidentStatus.REJECTED, user=admin)
        assert Notification.objects.filter(
            recipient=citizen, verb="incident.rejected", incident=incident
        ).exists()
