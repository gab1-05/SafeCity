"""
Nightly aggregate rows powering fast analytics dashboards.
Maintained by the analytics.tasks.aggregate_daily task (Celery beat).
"""

from django.db import models

from apps.core.models import UUIDModel


class DailyIncidentAggregate(UUIDModel):
    """One row per (date, ward, category, department) rollup."""

    date = models.DateField(db_index=True)
    ward = models.ForeignKey(
        "core.Ward", null=True, blank=True, on_delete=models.CASCADE, related_name="aggregates"
    )
    category = models.ForeignKey(
        "incidents.IncidentCategory",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="aggregates",
    )
    department = models.ForeignKey(
        "accounts.Department",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="aggregates",
    )

    submitted_count = models.PositiveIntegerField(default=0)
    resolved_count = models.PositiveIntegerField(default=0)
    reopened_count = models.PositiveIntegerField(default=0)
    emergency_count = models.PositiveIntegerField(default=0)
    duplicate_count = models.PositiveIntegerField(default=0)
    avg_response_minutes = models.PositiveIntegerField(null=True, blank=True)
    avg_resolution_minutes = models.PositiveIntegerField(null=True, blank=True)
    sla_met_count = models.PositiveIntegerField(default=0)
    sla_missed_count = models.PositiveIntegerField(default=0)
    satisfaction_sum = models.PositiveIntegerField(default=0)
    satisfaction_n = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["date", "ward", "category", "department"],
                name="uniq_daily_aggregate",
            )
        ]

    @property
    def satisfaction_avg(self):
        return (
            round(self.satisfaction_sum / self.satisfaction_n, 2) if self.satisfaction_n else None
        )
