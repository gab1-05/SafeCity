"""
Incident workflow services.

All state changes flow through these functions (never mutate Incident.status
directly in views). Guarantees:

- Transition matrix validation (wrong transitions raise ValidationError).
- SLA deadlines computed from active SLAConfiguration.
- Status history + audit log + notifications written in the same transaction.
- Duplicate/merge, escalate, reopen, resolve handled here.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User, UserRole
from apps.audit.services import log_action
from apps.incidents.models import (
    Incident,
    IncidentAssignment,
    IncidentCategory,
    IncidentEscalation,
    IncidentStatus,
    IncidentStatusHistory,
)
from apps.notifications.services import notify

logger = logging.getLogger("safecity")

# ── Allowed transitions: from → {to: allowed_roles} ──────────
# "*" = any authority role may perform the transition.
TRANSITIONS: dict[str, dict[str, set[str]]] = {
    IncidentStatus.DRAFT: {IncidentStatus.SUBMITTED: {"citizen", "city_admin", "superuser"}},
    IncidentStatus.SUBMITTED: {
        IncidentStatus.UNDER_REVIEW: {"department_staff", "city_admin", "superuser"},
        IncidentStatus.VERIFIED: {"city_admin", "superuser"},
        IncidentStatus.REJECTED: {"city_admin", "superuser"},
        IncidentStatus.DUPLICATE: {"city_admin", "superuser"},
        IncidentStatus.ASSIGNED: {"city_admin", "superuser", "department_staff"},  # fast-track
    },
    IncidentStatus.UNDER_REVIEW: {
        IncidentStatus.VERIFIED: {"department_staff", "city_admin", "superuser"},
        IncidentStatus.REJECTED: {"department_staff", "city_admin", "superuser"},
        IncidentStatus.DUPLICATE: {"city_admin", "superuser"},
    },
    IncidentStatus.VERIFIED: {
        IncidentStatus.ASSIGNED: {"city_admin", "superuser", "department_staff"},
        # Reporter reopens their own verified incident with new evidence.
        IncidentStatus.SUBMITTED: {"citizen", "city_admin", "superuser"},
    },
    IncidentStatus.ASSIGNED: {
        IncidentStatus.IN_PROGRESS: {
            "department_staff",
            "city_admin",
            "superuser",
            "emergency_responder",
        },
        IncidentStatus.AWAITING_INFO: {"department_staff", "city_admin", "superuser"},
        IncidentStatus.REOPENED: {"city_admin", "superuser"},
    },
    IncidentStatus.IN_PROGRESS: {
        IncidentStatus.AWAITING_INFO: {"department_staff", "city_admin", "superuser"},
        IncidentStatus.RESOLVED: {
            "department_staff",
            "city_admin",
            "superuser",
            "emergency_responder",
        },
        IncidentStatus.ESCALATED: {
            "department_staff",
            "city_admin",
            "superuser",
            "emergency_responder",
        },
        IncidentStatus.ASSIGNED: {"city_admin", "superuser"},  # reassignment
    },
    IncidentStatus.AWAITING_INFO: {
        IncidentStatus.IN_PROGRESS: {"citizen", "department_staff", "city_admin", "superuser"},
        IncidentStatus.ESCALATED: {"city_admin", "superuser"},
        # Staff rejects the info request — the citizen cannot drive this one.
        IncidentStatus.ASSIGNED: {"department_staff", "city_admin", "superuser"},
    },
    IncidentStatus.ESCALATED: {
        IncidentStatus.IN_PROGRESS: {
            "department_staff",
            "city_admin",
            "superuser",
            "emergency_responder",
        },
        IncidentStatus.RESOLVED: {"department_staff", "city_admin", "superuser"},
    },
    IncidentStatus.RESOLVED: {
        IncidentStatus.CLOSED: {"department_staff", "city_admin", "superuser"},
        IncidentStatus.REOPENED: {"citizen", "city_admin", "superuser"},
    },
    IncidentStatus.REOPENED: {
        IncidentStatus.IN_PROGRESS: {"department_staff", "city_admin", "superuser"},
        IncidentStatus.ASSIGNED: {"city_admin", "superuser"},
    },
    IncidentStatus.REJECTED: {IncidentStatus.CLOSED: {"city_admin", "superuser"}},
    IncidentStatus.DUPLICATE: {IncidentStatus.CLOSED: {"city_admin", "superuser"}},
}


class WorkflowError(ValidationError):
    """Raised for illegal workflow operations (mapped to HTTP 400/409 by DRF)."""


def roles_allowed_for(user: User, incident: Incident, to_status: str) -> bool:
    """Check the transition matrix for this user/incident pair."""
    allowed_roles = TRANSITIONS.get(incident.status, {}).get(to_status)
    if allowed_roles is None:
        return False
    if user.is_superuser or user.role == UserRole.SUPERUSER:
        return True
    if user.role == UserRole.CITY_ADMIN and "city_admin" in allowed_roles:
        return True
    if user.role in allowed_roles:
        return True
    # department_staff transition on incidents of another department → deny
    if user.role == UserRole.DEPARTMENT_STAFF:
        return incident.department_id == user.department_id
    return False


def compute_sla_deadline(category: IncidentCategory, severity: str, from_time=None):
    """Resolve the active SLA rule for (category, severity) → deadline or None."""
    from apps.core.models import SLAConfiguration

    rule = (
        SLAConfiguration.objects.filter(is_active=True, severity=severity)
        .filter(Q(category=category) | Q(category__isnull=True))
        .order_by(models_F_desc(category))
        .first()
    )
    if rule is None:
        return None
    start = from_time or timezone.now()
    return start + timedelta(hours=rule.resolution_hours)


def models_F_desc(category):
    """Prefer category-specific SLA rule over the default (null-category) rule."""
    from django.db.models import Case, When

    return Case(
        When(category=category, then=0),
        default=1,
    )


def assign_department_for_category(category: IncidentCategory):
    """Routing rule: category → owning department."""
    return category.default_department


def pick_staff_workload_aware(department, exclude_user=None):
    """Choose the department staff member with the fewest open incidents."""
    staff = User.objects.filter(
        department=department, role=UserRole.DEPARTMENT_STAFF, is_active=True
    )
    if exclude_user:
        staff = staff.exclude(pk=exclude_user.pk)
    best, best_count = None, None
    for member in staff:
        count = Incident.objects.filter(
            assigned_staff=member,
            status__in=[
                IncidentStatus.ASSIGNED,
                IncidentStatus.IN_PROGRESS,
                IncidentStatus.AWAITING_INFO,
            ],
        ).count()
        if best_count is None or count < best_count:
            best, best_count = member, count
    return best


@transaction.atomic
def create_incident(*, reporter, validated_data, request=None) -> Incident:
    """Create + submit an incident with routing, SLA, history, notifications."""
    category: IncidentCategory = validated_data["category"]
    is_anonymous = validated_data.get("is_anonymous", False)
    if is_anonymous and not _anonymous_allowed():
        raise WorkflowError(
            {"detail": "Anonymous reporting is disabled.", "code": "anonymous_disabled"}
        )

    # Check if user is blocked from reporting
    if not is_anonymous and reporter.is_reporting_blocked:
        raise WorkflowError(
            {
                "detail": "Your account has been temporarily blocked from submitting reports due to multiple rejected reports. Please contact support.",
                "code": "reporting_blocked",
            }
        )

    incident = Incident(**validated_data)
    incident.reporter = reporter if not is_anonymous else None
    incident.department = assign_department_for_category(category)
    incident.submitted_at = timezone.now()
    incident.sla_deadline = compute_sla_deadline(category, incident.severity)
    incident.save()

    IncidentStatusHistory.objects.create(
        incident=incident,
        from_status=None,
        to_status=IncidentStatus.SUBMITTED,
        actor=reporter,
        note="Incident submitted",
        is_public=True,
    )
    log_action(actor=reporter, action="incident.created", obj=incident, request=request)

    # Notify the owning department's staff
    if incident.department:
        notify_many_staff(
            incident.department,
            verb="incident.submitted",
            title=f"New incident {incident.reference_number}",
            body=f"{category.name}: {incident.title}",
            incident=incident,
        )

    # Notify the reporter (if not anonymous) that their report was submitted
    if not is_anonymous and reporter:
        notify(
            user=reporter,
            verb="incident.submitted",
            title=f"Report submitted: {incident.reference_number}",
            body=f"Your report '{incident.title}' has been submitted and is under review.",
            incident=incident,
        )

    return incident


def _anonymous_allowed() -> bool:
    from django.conf import settings

    return bool(settings.SAFECITY.get("ALLOW_ANONYMOUS_REPORTS", True))


def notify_many_staff(department, *, verb, title, body, incident, exclude=None):
    from apps.accounts.models import User as U

    staff = U.objects.filter(department=department, is_active=True).exclude(role=UserRole.CITIZEN)
    if exclude is not None:
        staff = staff.exclude(pk=exclude.pk)
    for member in staff:
        notify(user=member, verb=verb, title=title, body=body, incident=incident)


@transaction.atomic
def change_status(
    *, incident, to_status, user, note="", request=None, extra_updates: dict | None = None
) -> Incident:
    """
    Apply a validated status transition with all side effects:
    history, timestamps, audit log, SLA flags, notifications.
    """
    if to_status == incident.status:
        return incident  # idempotent no-op
    if not roles_allowed_for(user, incident, to_status):
        raise WorkflowError(
            {
                "detail": f"Transition {incident.status} → {to_status} is not allowed for you.",
                "code": "invalid_transition",
            }
        )
    # A citizen may only (re)submit their own incident — both from draft and
    # when reopening a verified one with new evidence.
    if (
        to_status == IncidentStatus.SUBMITTED
        and user.role == UserRole.CITIZEN
        and incident.reporter_id != user.id
    ):
        raise WorkflowError(
            {"detail": "Only the reporter can submit this incident.", "code": "forbidden"}
        )

    from_status = incident.status
    incident.status = to_status
    now = timezone.now()

    stamp_map = {
        IncidentStatus.VERIFIED: "verified_at",
        IncidentStatus.ASSIGNED: "assigned_at",
        IncidentStatus.RESOLVED: "resolved_at",
        IncidentStatus.CLOSED: "closed_at",
    }
    if to_status in stamp_map:
        setattr(incident, stamp_map[to_status], now)

    if to_status == IncidentStatus.RESOLVED and extra_updates:
        incident.resolution_summary = extra_updates.get(
            "resolution_summary", incident.resolution_summary
        )
    if to_status in (
        IncidentStatus.RESOLVED,
        IncidentStatus.CLOSED,
        IncidentStatus.REJECTED,
        IncidentStatus.DUPLICATE,
    ):
        incident.sla_breached = incident.sla_breached or incident.is_overdue

    for k, v in (extra_updates or {}).items():
        setattr(incident, k, v)

    incident.save()

    IncidentStatusHistory.objects.create(
        incident=incident,
        from_status=from_status,
        to_status=to_status,
        actor=user,
        note=note[:500],
        is_public=True,
    )
    log_action(
        actor=user,
        action="incident.status_change",
        obj=incident,
        changes={"status": {"from": from_status, "to": to_status}, "note": note},
        request=request,
    )

    # Track false/rejected reports for the reporter
    if incident.reporter and to_status in (IncidentStatus.REJECTED, IncidentStatus.DUPLICATE):
        _track_false_report(incident.reporter, to_status)

    _notify_status_change(incident, from_status, to_status, user, note)
    return incident


def _notify_status_change(incident, from_status, to_status, actor, note):
    # Reporter (if not anonymous)
    if incident.reporter:
        verb_by_status = {
            IncidentStatus.VERIFIED: "incident.verified",
            IncidentStatus.REJECTED: "incident.rejected",
            IncidentStatus.ASSIGNED: "incident.assigned",
            IncidentStatus.IN_PROGRESS: "incident.in_progress",
            IncidentStatus.AWAITING_INFO: "incident.info_requested",
            IncidentStatus.ESCALATED: "incident.escalated",
            IncidentStatus.RESOLVED: "incident.resolved",
            IncidentStatus.CLOSED: "incident.closed",
            IncidentStatus.REOPENED: "incident.reopened",
            IncidentStatus.DUPLICATE: "incident.duplicate",
        }
        verb = verb_by_status.get(to_status, "incident.status_change")
        notify(
            user=incident.reporter,
            verb=verb,
            title=f"{incident.reference_number}: {incident.get_status_display()}",
            body=note or f"Status changed from {from_status} to {to_status}.",
            incident=incident,
        )
    # Assigned staff
    if incident.assigned_staff and incident.assigned_staff != actor:
        notify(
            user=incident.assigned_staff,
            verb="incident.status_change",
            title=f"{incident.reference_number} → {incident.get_status_display()}",
            body=note,
            incident=incident,
        )
    # Escalations also alert the department
    if to_status == IncidentStatus.ESCALATED and incident.department:
        notify_many_staff(
            incident.department,
            verb="incident.escalated",
            title=f"ESCALATED {incident.reference_number}",
            body=note or "Incident escalated.",
            incident=incident,
        )
    # Verified → assigned: wake up the owning department's staff queue
    if (
        from_status == IncidentStatus.VERIFIED
        and to_status == IncidentStatus.ASSIGNED
        and incident.department
    ):
        notify_many_staff(
            incident.department,
            verb="incident.assigned",
            title=f"Assigned {incident.reference_number}",
            body=note or f"{incident.title} — the verified incident was assigned.",
            incident=incident,
        )


def _track_false_report(reporter, status: str) -> None:
    """
    Track rejected/duplicate reports for a user.
    If a user exceeds the threshold, block their reporting ability.
    """
    from django.utils import timezone
    from apps.accounts.models import UserRole

    if not reporter or reporter.role != UserRole.CITIZEN:
        return

    if status == IncidentStatus.REJECTED:
        reporter.rejected_report_count += 1
    elif status == IncidentStatus.DUPLICATE:
        reporter.false_report_count += 1

    # Auto-block after 5 rejected + false reports combined
    total_false = reporter.rejected_report_count + reporter.false_report_count
    if total_false >= 5 and not reporter.is_reporting_blocked:
        reporter.is_reporting_blocked = True
        reporter.reporting_blocked_at = timezone.now()
        reporter.reporting_blocked_reason = (
            f"Auto-blocked after {total_false} rejected/duplicate reports. "
            "Please contact support to restore reporting access."
        )

    reporter.save(update_fields=[
        "rejected_report_count",
        "false_report_count",
        "is_reporting_blocked",
        "reporting_blocked_at",
        "reporting_blocked_reason",
    ])


@transaction.atomic
def assign_incident(*, incident, assignee, user, note="", request=None) -> Incident:
    """Assign to a staff member (manual or workload-aware auto pick)."""
    if incident.status not in {
        IncidentStatus.SUBMITTED,
        IncidentStatus.VERIFIED,
        IncidentStatus.ASSIGNED,
        IncidentStatus.IN_PROGRESS,
        IncidentStatus.REOPENED,
    }:
        raise WorkflowError(
            {
                "detail": "Incident cannot be assigned in its current status.",
                "code": "invalid_transition",
            }
        )
    if user.role == UserRole.DEPARTMENT_STAFF and incident.department_id != user.department_id:
        raise WorkflowError(
            {"detail": "Cannot assign outside your department.", "code": "forbidden_department"}
        )
    if assignee == user:
        raise WorkflowError(
            {
                "detail": "You cannot assign an incident to yourself",
                "code": "self_assignment",
            }
        )
    if assignee.role != UserRole.DEPARTMENT_STAFF:
        raise WorkflowError(
            {"detail": "Assignee must be department staff.", "code": "invalid_assignee"}
        )
    if assignee.department_id != incident.department_id:
        raise WorkflowError(
            {
                "detail": "Assignee must belong to the incident's department.",
                "code": "invalid_assignee_department",
            }
        )

    previous = incident.assigned_staff
    previous_status = incident.status
    incident.assigned_staff = assignee
    if incident.status == IncidentStatus.VERIFIED or incident.status == IncidentStatus.SUBMITTED:
        incident.status = IncidentStatus.ASSIGNED
    incident.assigned_at = incident.assigned_at or timezone.now()
    incident.save()

    IncidentAssignment.objects.create(
        incident=incident, assignee=assignee, assigned_by=user, note=note[:300]
    )
    IncidentStatusHistory.objects.create(
        incident=incident,
        from_status=previous and incident.status or incident.status,  # status unchanged here
        to_status=incident.status,
        actor=user,
        note=f"Assigned to {assignee.full_name}" + (f" — {note}" if note else ""),
    )
    log_action(
        actor=user,
        action="incident.assigned",
        obj=incident,
        changes={"assigned_staff": {"from": str(previous), "to": str(assignee.id)}},
        request=request,
    )
    notify(
        user=assignee,
        verb="incident.assigned",
        title=f"Assigned: {incident.reference_number}",
        body=f"{incident.title} ({incident.get_severity_display()} severity)",
        incident=incident,
    )
    if incident.reporter and incident.reporter != user:
        notify(
            user=incident.reporter,
            verb="incident.assigned",
            title=f"{incident.reference_number} assigned to {incident.department.name if incident.department else 'staff'}",
            body="Your report has been assigned and is being handled.",
            incident=incident,
        )
    # Verified → assigned also wakes up the rest of the department's staff.
    if previous_status == IncidentStatus.VERIFIED and incident.department:
        notify_many_staff(
            incident.department,
            verb="incident.assigned",
            title=f"Assigned {incident.reference_number}",
            body=f"{incident.title} — the verified incident was assigned.",
            incident=incident,
            exclude=assignee,
        )
    return incident


@transaction.atomic
def escalate_incident(*, incident, user, level="level_1", reason="", request=None) -> Incident:
    """Escalate an incident (supervisor → department head → emergency ops)."""
    if incident.status in {
        IncidentStatus.RESOLVED,
        IncidentStatus.CLOSED,
        IncidentStatus.REJECTED,
        IncidentStatus.DUPLICATE,
    }:
        raise WorkflowError(
            {"detail": "Cannot escalate a closed incident.", "code": "invalid_transition"}
        )
    previous = incident.status
    incident.status = IncidentStatus.ESCALATED
    incident.save()
    IncidentEscalation.objects.create(
        incident=incident, level=level, reason=reason[:500], escalated_by=user
    )
    IncidentStatusHistory.objects.create(
        incident=incident,
        from_status=previous,
        to_status=IncidentStatus.ESCALATED,
        actor=user,
        note=reason[:500],
    )
    log_action(
        actor=user,
        action="incident.escalated",
        obj=incident,
        changes={"level": level, "reason": reason},
        request=request,
    )
    if incident.reporter:
        notify(
            user=incident.reporter,
            verb="incident.escalated",
            title=f"{incident.reference_number} escalated",
            body="Your report has been escalated for priority handling.",
            incident=incident,
        )
    if incident.department:
        notify_many_staff(
            incident.department,
            verb="incident.escalated",
            title=f"ESCALATED: {incident.reference_number}",
            body=reason or "Incident escalated.",
            incident=incident,
        )
    return incident


@transaction.atomic
def merge_incident(*, duplicate: Incident, parent: Incident, user, request=None) -> Incident:
    """Merge a duplicate into the canonical incident."""
    if duplicate.id == parent.id:
        raise WorkflowError(
            {"detail": "Cannot merge an incident into itself.", "code": "invalid_merge"}
        )
    if parent.status in {IncidentStatus.REJECTED}:
        raise WorkflowError(
            {"detail": "Cannot merge into a rejected incident.", "code": "invalid_merge"}
        )
    duplicate.duplicate_of = parent
    duplicate.status = IncidentStatus.DUPLICATE
    duplicate.save(update_fields=["duplicate_of", "status", "updated_at"])
    IncidentStatusHistory.objects.create(
        incident=duplicate,
        to_status=IncidentStatus.DUPLICATE,
        actor=user,
        note=f"Merged into {parent.reference_number}",
    )
    log_action(
        actor=user,
        action="incident.merged",
        obj=duplicate,
        changes={"parent": str(parent.reference_number)},
        request=request,
    )
    if duplicate.reporter:
        notify(
            user=duplicate.reporter,
            verb="incident.duplicate",
            title=f"{duplicate.reference_number} merged",
            body=f"Your report matches existing report {parent.reference_number} and will be tracked there.",
            incident=parent,
        )
    return parent


@transaction.atomic
def reopen_incident(*, incident, user, reason="", request=None) -> Incident:
    """Reopen a resolved/closed incident (citizen dispute or admin action)."""
    if incident.status not in {IncidentStatus.RESOLVED, IncidentStatus.CLOSED}:
        raise WorkflowError(
            {
                "detail": "Only resolved or closed incidents can be reopened.",
                "code": "invalid_transition",
            }
        )
    if user.role == UserRole.CITIZEN and incident.reporter_id != user.id:
        raise WorkflowError(
            {"detail": "Only the reporter can request a reopen.", "code": "forbidden"}
        )
    previous = incident.status
    incident.status = IncidentStatus.REOPENED
    incident.citizen_confirmed_resolution = False
    incident.save(update_fields=["status", "citizen_confirmed_resolution", "updated_at"])
    IncidentStatusHistory.objects.create(
        incident=incident,
        from_status=previous,
        to_status=IncidentStatus.REOPENED,
        actor=user,
        note=reason[:500],
    )
    log_action(
        actor=user,
        action="incident.reopened",
        obj=incident,
        changes={"reason": reason},
        request=request,
    )
    if incident.assigned_staff:
        notify(
            user=incident.assigned_staff,
            verb="incident.reopened",
            title=f"Reopened: {incident.reference_number}",
            body=reason or "The reporter disputed the resolution.",
            incident=incident,
        )
    return incident


@transaction.atomic
def confirm_resolution(*, incident, user, rating=None, comment="", request=None):
    """Citizen confirms the resolution; optional 1–5 satisfaction rating."""
    if incident.reporter_id != user.id:
        raise WorkflowError(
            {"detail": "Only the reporter can confirm resolution.", "code": "forbidden"}
        )
    if incident.status != IncidentStatus.RESOLVED:
        raise WorkflowError(
            {"detail": "Incident is not in resolved state.", "code": "invalid_transition"}
        )
    from apps.incidents.models import IncidentFeedback

    IncidentFeedback.objects.update_or_create(
        incident=incident,
        defaults={"user": user, "rating": rating, "comment": comment, "confirmed_resolution": True},
    )
    incident.citizen_confirmed_resolution = True
    if rating:
        incident.satisfaction_rating = rating
    incident.save(
        update_fields=["citizen_confirmed_resolution", "satisfaction_rating", "updated_at"]
    )
    log_action(
        actor=user,
        action="incident.resolution_confirmed",
        obj=incident,
        changes={"rating": rating},
        request=request,
    )
    if incident.assigned_staff:
        notify(
            user=incident.assigned_staff,
            verb="incident.confirmed",
            title=f"Resolution confirmed: {incident.reference_number}",
            body=f"Rating: {rating}/5" if rating else "The reporter confirmed the fix.",
            incident=incident,
        )
    return incident


# ── SLA / escalation sweeps (Celery) ─────────────────────────


def sla_breach_sweep() -> int:
    """Flag incidents past their SLA deadline; notify staff. Returns count."""
    open_statuses = [
        IncidentStatus.SUBMITTED,
        IncidentStatus.UNDER_REVIEW,
        IncidentStatus.VERIFIED,
        IncidentStatus.ASSIGNED,
        IncidentStatus.IN_PROGRESS,
        IncidentStatus.AWAITING_INFO,
        IncidentStatus.REOPENED,
        IncidentStatus.ESCALATED,
    ]
    overdue = Incident.objects.filter(
        sla_breached=False,
        sla_deadline__lt=timezone.now(),
        status__in=open_statuses,
    )
    count = 0
    for incident in overdue[:500]:  # batch cap per run
        incident.sla_breached = True
        incident.save(update_fields=["sla_breached", "updated_at"])
        if incident.department:
            notify_many_staff(
                incident.department,
                verb="incident.sla_breach",
                title=f"SLA breached: {incident.reference_number}",
                body=incident.title,
                incident=incident,
            )
        count += 1
    return count


def escalation_sweep() -> int:
    """Auto-escalate critical/emergency incidents still open past deadline."""
    from apps.incidents.models import Incident as I

    candidates = I.objects.filter(
        status__in=[IncidentStatus.SUBMITTED, IncidentStatus.UNDER_REVIEW, IncidentStatus.ASSIGNED],
        is_emergency=True,
        sla_breached=True,
    )[:200]
    count = 0
    system = None
    for incident in candidates:
        escalate_incident(
            incident=incident,
            user=system,
            level="level_3",
            reason="Automatic escalation: emergency SLA breach",
        )
        count += 1
    return count
