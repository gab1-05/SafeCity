"""
Append-only audit log. Written inside the same transaction as state changes.
"""

from django.conf import settings
from django.db import models

from apps.core.models import UUIDModel


class AuditLog(UUIDModel):
    """Immutable audit trail of security- and workflow-relevant actions."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=60, db_index=True)
    object_type = models.CharField(max_length=60)
    object_id = models.CharField(max_length=64, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    request_id = models.CharField(max_length=64, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=250, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["actor", "-created_at"], name="idx_audit_actor_time"),
            models.Index(fields=["object_type", "object_id"], name="idx_audit_object"),
        ]

    def __str__(self) -> str:
        return f"{self.action} {self.object_type}#{self.object_id} by {self.actor}"
