"""
Core shared models: abstract base classes, geographic admin units, SLA rules.

Note: wards/zones shipped here are *illustrative* seed data for Mumbai-style
municipal structure and do not claim official administrative accuracy.
"""

import uuid

from django.db import models


class UUIDModel(models.Model):
    """Abstract base with UUID primary key and timestamps."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Zone(UUIDModel):
    """Top-level municipal zone (illustrative grouping of wards)."""

    name = models.CharField(max_length=120, unique=True)
    code = models.SlugField(max_length=20, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class Ward(UUIDModel):
    """Municipal ward within a zone (illustrative seed data)."""

    zone = models.ForeignKey(Zone, on_delete=models.PROTECT, related_name="wards")
    name = models.CharField(max_length=120)
    code = models.SlugField(max_length=20, unique=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        ordering = ["code"]
        indexes = [models.Index(fields=["zone"], name="idx_ward_zone")]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class SLAConfiguration(UUIDModel):
    """
    Response/resolution deadlines per (category, severity).

    `response_hours` is used for first-action deadlines and `resolution_hours`
    for the full resolution deadline; incidents store the computed
    `sla_deadline` so historical policies do not retroactively change.
    """

    SEVERITIES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    category = models.ForeignKey(
        "incidents.IncidentCategory",
        on_delete=models.CASCADE,
        related_name="sla_rules",
        null=True,
        blank=True,
        help_text="Null = default rule for all categories",
    )
    severity = models.CharField(max_length=10, choices=SEVERITIES)
    response_hours = models.PositiveIntegerField(default=24)
    resolution_hours = models.PositiveIntegerField(default=72)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["category", "severity"],
                condition=models.Q(is_active=True),
                name="uniq_active_sla_category_severity",
            )
        ]

    def __str__(self) -> str:
        cat = self.category.name if self.category else "default"
        return f"SLA {cat}/{self.severity}: {self.response_hours}h/{self.resolution_hours}h"


class IntegrationConfiguration(UUIDModel):
    """Toggle + settings for external integrations (email, SMS, AI, scanning)."""

    KINDS = [
        ("email", "Email"),
        ("sms", "SMS"),
        ("push", "Push"),
        ("ai", "AI provider"),
        ("malware_scan", "Malware scanning"),
        ("captcha", "CAPTCHA"),
        ("map_tiles", "Map tiles"),
        ("storage", "Object storage"),
    ]

    name = models.SlugField(max_length=60, unique=True)
    kind = models.CharField(max_length=20, choices=KINDS, db_index=True)
    enabled = models.BooleanField(default=False)
    settings = models.JSONField(default=dict, blank=True)
    updated_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL
    )

    def __str__(self) -> str:
        return f"{self.name} [{self.kind}] enabled={self.enabled}"


class APIKey(UUIDModel):
    """
    Hashed API key for server-to-server integrations.

    Only the SHA-256 hash is stored; the raw key is shown once at creation.
    """

    name = models.CharField(max_length=120)
    key_hash = models.CharField(max_length=64, unique=True)
    scopes = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL
    )
    last_used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return self.name


class EscalationRule(UUIDModel):
    """
    Automatic escalation rules based on SLA breach, severity, or time in status.
    Rules are evaluated in order of priority (lower = higher priority).
    When conditions match, the incident is escalated to the next level.
    """

    LEVELS = [
        ("level_1", "Level 1 — Supervisor"),
        ("level_2", "Level 2 — Department Head"),
        ("level_3", "Level 3 — Emergency Operations"),
    ]

    name = models.CharField(max_length=120)
    priority = models.PositiveIntegerField(default=100, help_text="Lower = evaluated first")
    # Conditions
    severity = models.CharField(
        max_length=10,
        choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical"), ("any", "Any")],
        default="any",
    )
    category = models.ForeignKey(
        "incidents.IncidentCategory",
        on_delete=models.CASCADE,
        related_name="escalation_rules",
        null=True,
        blank=True,
        help_text="Null = all categories",
    )
    statuses = models.JSONField(
        default=list,
        blank=True,
        help_text="List of status codes to trigger on, e.g. ['submitted', 'assigned']",
    )

    # Triggers
    trigger_on_sla_breach = models.BooleanField(default=True)
    trigger_after_hours = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Escalate after this many hours in matching status (regardless of SLA)",
    )
    trigger_on_reopen_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Escalate if reopened this many times",
    )

    # Action
    escalate_to_level = models.CharField(max_length=10, choices=LEVELS, default="level_1")
    notify_department_head = models.BooleanField(default=True)
    auto_assign_supervisor = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["priority", "created_at"]

    def __str__(self) -> str:
        return f"Escalation Rule: {self.name} ({self.escalate_to_level})"
