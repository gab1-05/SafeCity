"""
Role → permission mapping.

Roles map to Django Groups whose names match ROLE_GROUPS; the groups are
recreated idempotently by the `sync_roles` management command. Object-level
checks (owner, department membership, assignment) live in permissions.py.
"""

from django.contrib.auth.models import Group, Permission

from apps.accounts.models import ROLE_GROUPS, UserRole

ROLE_PERMISSIONS: dict[str, list[str]] = {
    UserRole.CITIZEN: [],
    UserRole.VOLUNTEER: [],
    UserRole.DEPARTMENT_STAFF: [],
    UserRole.EMERGENCY_RESPONDER: [],
    UserRole.CITY_ADMIN: [],
    UserRole.SUPERUSER: [],
}


def sync_roles() -> dict[str, int]:
    """Create role groups; returns group name → member count. Idempotent."""
    result = {}
    for role, group_name in ROLE_GROUPS.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        codenames = ROLE_PERMISSIONS.get(role, [])
        if codenames:
            perms = Permission.objects.filter(codename__in=codenames)
            group.permissions.set(perms)
        result[group_name] = group.user_set.count()
    return result
