"""
RBAC permission classes.

Server-side authorization is the single source of truth; frontend checks are
UX only. Object-level checks (owner / department membership / assignment) are
implemented here and reused by incident views.
"""

from rest_framework import permissions

from apps.accounts.models import UserRole


class IsAuthenticatedRole(permissions.IsAuthenticated):
    """Base authenticated access."""


class IsCitizen(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == UserRole.CITIZEN


class IsDepartmentStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == UserRole.DEPARTMENT_STAFF


class IsCityAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user.is_authenticated
            and request.user.role in {UserRole.CITY_ADMIN, UserRole.SUPERUSER}
        )


class IsAuthority(permissions.BasePermission):
    """Any operational authority role (staff, responder, admin, superuser)."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_authority()


def can_view_incident(user, incident) -> bool:
    """
    Object-level read check.

    Rules:
      - Admins/superusers: everything.
      - Reporter: always (even anonymous ones own their report).
      - Department staff: their department's incidents.
      - Responders: high-severity or assigned/emergency incidents.
      - Volunteers: verified/resolved public incidents.
      - Anonymous private fields stay hidden via serializers, not flags.
    """
    if not user.is_authenticated:
        return incident is not None and _is_public_status(incident.status)
    if user.role in (UserRole.CITY_ADMIN, UserRole.SUPERUSER):
        return True
    if incident.reporter_id == user.id:
        return True
    if user.role == UserRole.DEPARTMENT_STAFF:
        return incident.department_id == user.department_id
    if user.role == UserRole.EMERGENCY_RESPONDER:
        return (
            incident.assigned_responder_id == user.id
            or incident.severity in ("high", "critical")
            or incident.is_emergency
        )
    if user.role == UserRole.VOLUNTEER:
        return incident.status in ("verified", "in_progress", "resolved")
    return _is_public_status(incident.status)


def _is_public_status(status: str) -> bool:
    """Unauthenticated users may see only verified/resolved community incidents."""
    return status in ("verified", "resolved")


def can_view_internal_notes(user, incident) -> bool:
    """Internal comments/timeline are authority-only."""
    if not user.is_authenticated:
        return False
    return user.is_authority() and (
        user.role in (UserRole.CITY_ADMIN, UserRole.SUPERUSER)
        or incident.department_id == user.department_id
        or incident.assigned_staff_id == user.id
        or incident.assigned_responder_id == user.id
    )


def can_manage_users(user) -> bool:
    return user.is_authenticated and user.role in (UserRole.CITY_ADMIN, UserRole.SUPERUSER)


class CanViewIncident(permissions.BasePermission):
    """DRF adapter for can_view_incident."""

    def has_object_permission(self, request, view, obj):
        return can_view_incident(request.user, obj)
