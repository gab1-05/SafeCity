"""
Audit service: single entry point for writing audit entries.

Every state-changing workflow must call `log_action` inside the same
transaction as the change. There is deliberately no bypass: even
superuser-triggered actions are recorded.
"""

from typing import Any

from apps.audit.models import AuditLog
from apps.core.middleware import get_request_id


def log_action(
    *,
    actor: Any | None,
    action: str,
    obj: Any = None,
    changes: dict | None = None,
    request=None,
) -> AuditLog:
    """
    Write an audit entry.

    Args:
        actor: the user performing the action (None for system/celery).
        action: machine-readable action key, e.g. "incident.status_change".
        obj: model instance (or None); type + pk are recorded.
        changes: {"field": {"from": x, "to": y}} or free-form payload.
        request: optional HttpRequest to extract ip/UA.
    """
    ip = None
    ua = ""
    if request is not None:
        ip = request.META.get("REMOTE_ADDR") or None
        ua = (request.META.get("HTTP_USER_AGENT") or "")[:250]

    return AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        object_type=obj.__class__.__name__ if obj is not None else "",
        object_id=str(getattr(obj, "pk", "")) if obj is not None else "",
        changes=changes or {},
        request_id=get_request_id(),
        ip_address=ip,
        user_agent=ua,
    )
