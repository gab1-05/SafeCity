"""
Notifications and per-user notification preferences.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import UUIDModel


class Notification(UUIDModel):
    """In-app notification delivered via API and WebSocket."""

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    verb = models.CharField(max_length=50, help_text="Machine-readable event key")
    title = models.CharField(max_length=160)
    body = models.TextField(blank=True)
    incident = models.ForeignKey(
        "incidents.Incident",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    payload = models.JSONField(default=dict, blank=True)
    read_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "read_at"], name="idx_notif_recipient_read")]

    def __str__(self) -> str:
        return f"{self.verb} → {self.recipient.email}"

    @property
    def is_read(self) -> bool:
        return self.read_at is not None

    def mark_read(self) -> None:
        if not self.read_at:
            self.read_at = timezone.now()
            self.save(update_fields=["read_at"])


class NotificationPreference(UUIDModel):
    """Per-user, per-channel, per-event notification switches."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_preferences"
    )
    in_app = models.BooleanField(default=True)
    email = models.BooleanField(default=True)
    sms = models.BooleanField(default=False)
    push = models.BooleanField(default=False)
    # Event-level opt-outs
    events_enabled = models.JSONField(
        default=dict, blank=True, help_text='{"status_change": false} disables that event'
    )

    def __str__(self) -> str:
        return f"prefs:{self.user.email}"
