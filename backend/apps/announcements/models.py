"""
Public announcements authored by city administrators.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import UUIDModel


class Announcement(UUIDModel):
    """Public or targeted city announcement (admin-authored)."""

    AUDIENCES = [("public", "Public"), ("citizens", "Citizens"), ("staff", "Staff")]

    title = models.CharField(max_length=200)
    body = models.TextField()
    audience = models.CharField(max_length=20, choices=AUDIENCES, default="public")
    is_pinned = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="announcements",
    )

    class Meta:
        ordering = ["-is_pinned", "-published_at"]

    def __str__(self) -> str:
        return self.title

    def publish(self, by=None):
        self.is_published = True
        self.published_at = timezone.now()
        if by:
            self.published_by = by
        self.save(update_fields=["is_published", "published_at", "published_by"])
