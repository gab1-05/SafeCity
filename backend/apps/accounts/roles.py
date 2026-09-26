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

# Roles a user may *request* at signup (or later from their profile).
# `citizen` needs no approval; `city_admin`/`superuser` are never
# requestable — only assignable directly by an existing admin.
REQUESTABLE_ROLES: list[str] = [
    UserRole.VOLUNTEER,
    UserRole.DEPARTMENT_STAFF,
    UserRole.EMERGENCY_RESPONDER,
]

# Human-readable permission summary per role, shown in the admin UI.
# Enforcement lives in apps.accounts.permissions (role field + code-level
# checks), so changing a user's role *is* changing their permissions.
ROLE_PERMISSION_SUMMARY: dict[str, list[str]] = {
    UserRole.CITIZEN: [
        "Report incidents",
        "Track own reports",
        "View public map (all active + recently resolved)",
    ],
    UserRole.VOLUNTEER: [
        "Everything a citizen can do",
        "View verified / in-progress / resolved incidents",
    ],
    UserRole.DEPARTMENT_STAFF: [
        "View & manage own department's incidents",
        "View internal notes for own department",
        "Assignment picker access",
    ],
    UserRole.EMERGENCY_RESPONDER: [
        "View assigned incidents + high/critical severity emergencies",
        "Update assigned incident status",
    ],
    UserRole.CITY_ADMIN: [
        "View all incidents",
        "Manage users (roles, activation, unlocks)",
        "Process deletion & role requests",
        "Manage announcements & analytics",
    ],
    UserRole.SUPERUSER: ["All city-admin powers (full system access)"],
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
