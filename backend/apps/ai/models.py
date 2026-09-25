"""
AI recommendation records. AI output is advisory: every recommendation stores
provider, output, confidence and the human decision for explainability.
"""

from django.conf import settings
from django.db import models

from apps.core.models import UUIDModel


class AIRecommendation(UUIDModel):
    """One AI suggestion tied to an incident, with its human decision."""

    KINDS = [
        ("category", "Category suggestion"),
        ("severity", "Severity suggestion"),
        ("priority", "Priority recommendation"),
        ("duplicate", "Duplicate similarity"),
        ("summary", "Description summarization"),
        ("toxicity", "Toxicity check"),
        ("translation", "Translation"),
        ("entities", "Entity extraction"),
    ]
    DECISIONS = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("edited", "Accepted with edits"),
        ("rejected", "Rejected"),
    ]

    incident = models.ForeignKey(
        "incidents.Incident",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="ai_recommendations",
    )
    kind = models.CharField(max_length=15, choices=KINDS)
    provider = models.CharField(max_length=40, default="mock")
    output = models.JSONField(default=dict, blank=True)
    confidence = models.FloatField(null=True, blank=True)
    decision = models.CharField(max_length=10, choices=DECISIONS, default="pending")
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["kind"], name="idx_ai_kind")]

    def __str__(self) -> str:
        return f"{self.kind} ({self.provider}, {self.confidence}) for {self.incident_id}"
