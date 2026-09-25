"""
Incident workflow tests: creation, validation, transitions, SLA, assignment,
escalation, merge, reopen, duplicate detection, comments, privacy.
"""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.incidents.models import (
    IncidentComment,
    IncidentEscalation,
    IncidentStatus,
)
from apps.incidents.services import (
    WorkflowError,
    assign_incident,
    change_status,
    escalate_incident,
    merge_incident,
    pick_staff_workload_aware,
    reopen_incident,
    sla_breach_sweep,
)

pytestmark = pytest.mark.django_db


class TestIncidentCreation:
    def test_citizen_creates_incident(self, client, citizen, category):
        client.force_authenticate(user=citizen)
        response = client.post(
            "/api/v1/incidents/",
            {
                "title": "Broken traffic signal",
                "description": "The signal is stuck on red and causing long jams.",
                "category_id": str(category.id),
                "severity": "high",
                "urgency": "urgent",
                "latitude": 19.076,
                "longitude": 72.8777,
                "address_public": "Main junction",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["reference_number"].startswith("SC-MUM-")
        assert response.data["status"] == IncidentStatus.SUBMITTED

    def test_short_title_rejected(self, client, citizen, category):
        client.force_authenticate(user=citizen)
        response = client.post(
            "/api/v1/incidents/",
            {
                "title": "short",
                "description": "This description is definitely long enough.",
                "category_id": str(category.id),
                "severity": "low",
                "latitude": 19.076,
                "longitude": 72.8777,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_coordinates_rejected(self, client, citizen, category):
        client.force_authenticate(user=citizen)
        response = client.post(
            "/api/v1/incidents/",
            {
                "title": "Valid incident title",
                "description": "This description is definitely long enough too.",
                "category_id": str(category.id),
                "severity": "low",
                "latitude": 200,
                "longitude": 72.8777,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_citizen_cannot_declare_emergency(self, client, citizen, category):
        client.force_authenticate(user=citizen)
        response = client.post(
            "/api/v1/incidents/",
            {
                "title": "Try to fake an emergency",
                "description": "This description is definitely long enough as well.",
                "category_id": str(category.id),
                "severity": "critical",
                "latitude": 19.076,
                "longitude": 72.8777,
                "is_emergency": True,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["is_emergency"] is False

    def test_severity_urgency_conflict_rejected(self, client, citizen, category):
        client.force_authenticate(user=citizen)
        response = client.post(
            "/api/v1/incidents/",
            {
                "title": "Critical but relaxed",
                "description": "This description is definitely long enough, isn't it?",
                "category_id": str(category.id),
                "severity": "critical",
                "urgency": "low",
                "latitude": 19.076,
                "longitude": 72.8777,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestSLA:
    def test_sla_deadline_computed_on_create(self, client, citizen, category, sla_rules):
        client.force_authenticate(user=citizen)
        before = timezone.now()
        response = client.post(
            "/api/v1/incidents/",
            {
                "title": "SLA check incident",
                "description": "Checking the SLA deadline gets computed from policy.",
                "category_id": str(category.id),
                "severity": "critical",
                "latitude": 19.076,
                "longitude": 72.8777,
            },
            format="json",
        )
        deadline = response.data["sla_deadline"]
        assert deadline is not None
        expected = before + timedelta(hours=6)
        actual = timezone.datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        assert abs((actual - expected).total_seconds()) < 60

    def test_breach_sweep_flags_overdue(self, incident, sla_rules):
        incident.sla_deadline = timezone.now() - timedelta(hours=1)
        incident.save()
        count = sla_breach_sweep()
        incident.refresh_from_db()
        assert count >= 1
        assert incident.sla_breached is True


class TestTransitions:
    def test_valid_transition_verified(self, admin, incident):
        change_status(incident=incident, to_status=IncidentStatus.VERIFIED, user=admin)
        incident.refresh_from_db()
        assert incident.status == IncidentStatus.VERIFIED
        assert incident.verified_at is not None

    def test_citizen_cannot_verify(self, citizen, incident):
        with pytest.raises(WorkflowError):
            change_status(incident=incident, to_status=IncidentStatus.VERIFIED, user=citizen)

    def test_staff_other_department_cannot_verify(self, other_dept_staff, incident):
        with pytest.raises(WorkflowError):
            change_status(
                incident=incident, to_status=IncidentStatus.VERIFIED, user=other_dept_staff
            )

    def test_invalid_jump_rejected(self, admin, incident):
        with pytest.raises(WorkflowError):
            change_status(incident=incident, to_status=IncidentStatus.CLOSED, user=admin)

    def test_full_lifecycle(self, admin, staff, citizen, incident):
        change_status(incident=incident, to_status=IncidentStatus.VERIFIED, user=admin)
        assign_incident(incident=incident, assignee=staff, user=admin)
        change_status(incident=incident, to_status=IncidentStatus.IN_PROGRESS, user=staff)
        change_status(
            incident=incident,
            to_status=IncidentStatus.RESOLVED,
            user=staff,
            extra_updates={"resolution_summary": "Fixed the road."},
        )
        incident.refresh_from_db()
        assert incident.status == IncidentStatus.RESOLVED
        assert incident.resolution_summary == "Fixed the road."
        # Citizen confirms resolution
        client = APIClient()
        client.force_authenticate(user=citizen)
        response = client.post(f"/api/v1/incidents/{incident.id}/confirm/", {"rating": 5})
        assert response.status_code == status.HTTP_200_OK
        incident.refresh_from_db()
        assert incident.citizen_confirmed_resolution is True
        assert incident.satisfaction_rating == 5


class TestAssignment:
    def test_assign_within_department(self, admin, staff, incident):
        assign_incident(incident=incident, assignee=staff, user=admin)
        incident.refresh_from_db()
        assert incident.assigned_staff == staff
        assert incident.status == IncidentStatus.ASSIGNED

    def test_assign_wrong_department_rejected(self, admin, other_dept_staff, incident):
        with pytest.raises(WorkflowError):
            assign_incident(incident=incident, assignee=other_dept_staff, user=admin)

    def test_workload_aware_pick(self, admin, staff, other_dept_staff, incident_factory):
        # Give staff an open incident; picker should still pick them (only option)
        incident_factory(assigned_staff=staff, status="assigned")
        picked = pick_staff_workload_aware(incident_factory().department)
        assert picked == staff


class TestEscalationMergeReopen:
    def test_escalate(self, admin, incident):
        escalate_incident(incident=incident, user=admin, reason="Emergency SLA breach")
        incident.refresh_from_db()
        assert incident.status == IncidentStatus.ESCALATED
        assert IncidentEscalation.objects.filter(incident=incident).exists()

    def test_merge_duplicates(self, admin, incident_factory, citizen):
        parent = incident_factory(reporter=citizen)
        child = incident_factory(reporter=citizen)
        merge_incident(duplicate=child, parent=parent, user=admin)
        child.refresh_from_db()
        assert child.status == IncidentStatus.DUPLICATE
        assert child.duplicate_of == parent

    def test_citizen_reopens_own_resolved(self, admin, staff, citizen, incident):
        change_status(incident=incident, to_status=IncidentStatus.VERIFIED, user=admin)
        assign_incident(incident=incident, assignee=staff, user=admin)
        change_status(incident=incident, to_status=IncidentStatus.IN_PROGRESS, user=staff)
        change_status(incident=incident, to_status=IncidentStatus.RESOLVED, user=staff)
        reopen_incident(incident=incident, user=citizen, reason="Not fixed")
        incident.refresh_from_db()
        assert incident.status == IncidentStatus.REOPENED

    def test_citizen_cannot_reopen_others(self, admin, staff, incident, citizen):
        from apps.accounts.models import User, UserRole

        stranger = User.objects.create_user(
            email="stranger@test.local", password="Testpass123!", role=UserRole.CITIZEN
        )
        change_status(incident=incident, to_status=IncidentStatus.VERIFIED, user=admin)
        assign_incident(incident=incident, assignee=staff, user=admin)
        change_status(incident=incident, to_status=IncidentStatus.IN_PROGRESS, user=staff)
        change_status(incident=incident, to_status=IncidentStatus.RESOLVED, user=staff)
        with pytest.raises(WorkflowError):
            reopen_incident(incident=incident, user=stranger)


class TestComments:
    def test_citizen_adds_public_comment(self, client, citizen, incident):
        client.force_authenticate(user=citizen)
        response = client.post(
            f"/api/v1/incidents/{incident.id}/comments/",
            {"body": "Still not fixed, please escalate."},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["is_internal"] is False

    def test_internal_comment_flagged_by_citizen_becomes_public(self, client, citizen, incident):
        client.force_authenticate(user=citizen)
        response = client.post(
            f"/api/v1/incidents/{incident.id}/comments/",
            {"body": "Trying to mark internal", "is_internal": True},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["is_internal"] is False  # forced off for citizens

    def test_staff_internal_note_hidden_from_citizen(self, client, staff, citizen, incident):
        IncidentComment.objects.create(
            incident=incident,
            author=staff,
            body="Internal: check contractor",
            is_internal=True,
        )
        client.force_authenticate(user=citizen)
        response = client.get(f"/api/v1/incidents/{incident.id}/comments/")
        bodies = [c["body"] for c in response.data]
        assert "Internal: check contractor" not in bodies
        client.force_authenticate(user=staff)
        response = client.get(f"/api/v1/incidents/{incident.id}/comments/")
        bodies = [c["body"] for c in response.data]
        assert "Internal: check contractor" in bodies


class TestPrivacy:
    def test_public_tracking_hides_reporter(self, client, citizen, incident):
        response = client.get(f"/api/v1/incidents/track/{incident.reference_number}/")
        assert response.status_code == status.HTTP_200_OK
        assert "reporter" not in response.data
        assert "address_private" not in response.data
        assert "assigned_staff" not in response.data

    def test_public_tracking_jitters_coordinates(self, client, citizen, incident):
        response = client.get(f"/api/v1/incidents/track/{incident.reference_number}/")
        lat_diff = abs(float(response.data["latitude"]) - float(incident.latitude))
        lng_diff = abs(float(response.data["longitude"]) - float(incident.longitude))
        # Jittered ~150 m; original must not be exposed exactly
        assert lat_diff > 0.0001 or lng_diff > 0.0001

    def test_public_tracking_excludes_anonymous_from_list(self, client, incident_factory):
        anonymous = incident_factory(is_anonymous=True)
        response = client.get(f"/api/v1/incidents/track/{anonymous.reference_number}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_audit_log_written_for_transitions(self, admin, incident):
        from apps.audit.models import AuditLog

        before = AuditLog.objects.count()
        change_status(incident=incident, to_status=IncidentStatus.VERIFIED, user=admin)
        assert AuditLog.objects.count() > before


class TestDuplicateCheck:
    def test_duplicate_check_endpoint(self, client, citizen, incident):
        client.force_authenticate(user=citizen)
        response = client.post(
            "/api/v1/incidents/duplicates/check/",
            {
                "latitude": float(incident.latitude),
                "longitude": float(incident.longitude),
                "category_id": str(incident.category_id),
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        # Own incident excluded; may or may not match others
        assert "has_duplicates" in response.data


class TestNotifications:
    @patch("apps.incidents.services.notify")
    def test_verification_notifies_reporter(self, mock_notify, admin, incident, citizen):
        change_status(incident=incident, to_status=IncidentStatus.VERIFIED, user=admin)
        assert mock_notify.called

    def test_notification_created_in_db(self, admin, incident, citizen):
        change_status(incident=incident, to_status=IncidentStatus.VERIFIED, user=admin)
        from apps.notifications.models import Notification

        assert Notification.objects.filter(recipient=citizen, verb="incident.verified").exists()
