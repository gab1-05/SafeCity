"""
Incident domain models.

Incident is the central aggregate: status transitions, assignments,
escalations, media, comments and feedback all hang off it. Every
state-changing workflow lives in services.py, not in views.
"""

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils import timezone

from apps.core.models import UUIDModel


class IncidentStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    UNDER_REVIEW = "under_review", "Under Review"
    VERIFIED = "verified", "Verified"
    REJECTED = "rejected", "Rejected"
    DUPLICATE = "duplicate", "Duplicate"
    ASSIGNED = "assigned", "Assigned"
    IN_PROGRESS = "in_progress", "In Progress"
    AWAITING_INFO = "awaiting_info", "Awaiting Information"
    ESCALATED = "escalated", "Escalated"
    RESOLVED = "resolved", "Resolved"
    CLOSED = "closed", "Closed"
    REOPENED = "reopened", "Reopened"


class Severity(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class Urgency(models.TextChoices):
    LOW = "low", "Low"
    NORMAL = "normal", "Normal"
    URGENT = "urgent", "Urgent"
    IMMEDIATE = "immediate", "Immediate"


class ReferenceCounter(models.Model):
    """
    Row-locked allocator for sequential, human-readable reference numbers.

    One row per prefix (for example ``SC-MUM-2026-``). Allocation takes a
    ``SELECT ... FOR UPDATE`` lock on the row, so two concurrent submissions
    can never be handed the same sequence value and collide on the unique
    ``Incident.reference_number`` index.

    Kept as a table rather than a Postgres sequence so the counter is
    inspectable, resettable per year, and portable across database backends.
    """

    prefix = models.CharField(max_length=24, primary_key=True)
    last_value = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return f"{self.prefix}{self.last_value:06d}"


def allocate_reference_number(prefix: str) -> str:
    """
    Atomically allocate the next reference number for ``prefix``.

    Must run inside a transaction: ``select_for_update`` requires one, and the
    lock is deliberately held until the surrounding transaction commits so the
    allocating ``Incident`` insert commits alongside the counter increment.

    Self-healing: a freshly-created counter (e.g. the migration landed after
    incidents were already seeded, or the table was reset) syncs to the highest
    existing reference number for the prefix instead of colliding with it.
    """
    from django.db import IntegrityError

    with transaction.atomic():
        # get_or_create tolerates the race where two workers both find no row;
        # it retries the read after an IntegrityError on the primary key.
        ReferenceCounter.objects.get_or_create(prefix=prefix)
        counter = ReferenceCounter.objects.select_for_update().get(prefix=prefix)
        if counter.last_value == 0:
            # New/empty counter: adopt the highest allocated number so we never
            # collide with rows created before the counter existed.
            highest = (
                Incident.objects.filter(reference_number__startswith=prefix)
                .order_by("-reference_number")
                .values_list("reference_number", flat=True)
                .first()
            )
            if highest:
                try:
                    counter.last_value = int(highest[len(prefix) :])
                except ValueError:
                    counter.last_value = 0
        counter.last_value += 1
        try:
            counter.save(update_fields=["last_value"])
        except IntegrityError:
            # Unreachable in practice; keeps the atomic block well-formed.
            raise
        return f"{prefix}{counter.last_value:06d}"


class IncidentCategory(UUIDModel):
    """Reportable incident type, mapped to an owning department."""

    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=130, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=40, blank=True, help_text="Frontend icon identifier")
    default_department = models.ForeignKey(
        "accounts.Department",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="categories",
    )
    is_emergency_category = models.BooleanField(default=False)
    requires_media = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=100)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name_plural = "incident categories"

    def __str__(self) -> str:
        return self.name


class Incident(UUIDModel):
    """
    A citizen-reported or desk-entered city incident.

    Privacy notes:
      - `address_public` is safe to expose; `address_private` is authority-only.
      - Reporter is nullable for anonymous reports; `is_anonymous` hides identity
        in every public representation regardless of reporter presence.
    """

    # ── Core fields ───────────────────────────────────────────
    reference_number = models.CharField(max_length=32, unique=True, db_index=True)
    title = models.CharField(max_length=160)
    description = models.TextField()
    category = models.ForeignKey(
        IncidentCategory, on_delete=models.PROTECT, related_name="incidents"
    )
    subcategory = models.CharField(max_length=120, blank=True)

    severity = models.CharField(
        max_length=10, choices=Severity.choices, default=Severity.MEDIUM, db_index=True
    )
    urgency = models.CharField(max_length=10, choices=Urgency.choices, default=Urgency.NORMAL)
    status = models.CharField(
        max_length=20,
        choices=IncidentStatus.choices,
        default=IncidentStatus.SUBMITTED,
        db_index=True,
    )

    # ── People ────────────────────────────────────────────────
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="incidents",
    )
    is_anonymous = models.BooleanField(default=False)
    department = models.ForeignKey(
        "accounts.Department",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="incidents",
    )
    assigned_staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_incidents",
    )
    assigned_responder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="responding_incidents",
    )

    # ── Location ──────────────────────────────────────────────
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    address_public = models.CharField(max_length=250, blank=True)
    address_private = models.CharField(max_length=250, blank=True)
    ward = models.ForeignKey(
        "core.Ward", null=True, blank=True, on_delete=models.SET_NULL, related_name="incidents"
    )
    landmark = models.CharField(max_length=160, blank=True)

    # ── Workflow ──────────────────────────────────────────────
    is_emergency = models.BooleanField(default=False, db_index=True)
    sla_deadline = models.DateTimeField(null=True, blank=True, db_index=True)
    sla_breached = models.BooleanField(default=False)
    duplicate_of = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="duplicates"
    )
    merged_into = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="merged_children"
    )
    citizen_confirmed_resolution = models.BooleanField(default=False)
    satisfaction_rating = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    resolution_summary = models.TextField(blank=True)

    # ── Timestamps (transition trail) ─────────────────────────
    submitted_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    # ── Search & soft delete ─────────────────────────────────
    search_vector = SearchVectorField(null=True, editable=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"], name="idx_incident_status"),
            models.Index(fields=["severity"], name="idx_incident_severity"),
            models.Index(fields=["category"], name="idx_incident_category"),
            models.Index(fields=["department"], name="idx_incident_department"),
            models.Index(fields=["ward"], name="idx_incident_ward"),
            models.Index(fields=["created_at"], name="idx_incident_created"),
            models.Index(fields=["sla_deadline"], name="idx_incident_sla"),
            models.Index(fields=["latitude", "longitude"], name="idx_incident_latlng"),
            models.Index(fields=["is_emergency"], name="idx_incident_emergency"),
            GinIndex(fields=["search_vector"], name="idx_incident_search"),
        ]
        permissions = [
            ("verify_incident", "Can verify or reject incidents"),
            ("assign_incident", "Can assign incidents to staff"),
            ("escalate_incident", "Can escalate incidents"),
            ("merge_incident", "Can merge duplicate incidents"),
            ("view_internal_timeline", "Can view internal authority timeline"),
            ("view_all_analytics", "Can view all analytics"),
        ]

    def __str__(self) -> str:
        return f"{self.reference_number} · {self.title}"

    def save(self, *args, **kwargs):
        # Sequential, human-readable reference number: SC-MUM-2026-000001.
        # An explicitly supplied value (fixtures, imports, tests) is preserved.
        if not self.reference_number:
            self.reference_number = allocate_reference_number(f"SC-MUM-{timezone.now().year}-")
        super().save(*args, **kwargs)

    # ── Convenience helpers ───────────────────────────────────
    @property
    def is_overdue(self) -> bool:
        return bool(
            self.sla_deadline
            and self.sla_breached is False
            and self.status not in {IncidentStatus.RESOLVED, IncidentStatus.CLOSED}
            and timezone.now() > self.sla_deadline
        )

    @property
    def response_time(self):
        """First authority action time (verification or assignment), if any."""
        action = self.verified_at or self.assigned_at
        if self.submitted_at and action:
            return action - self.submitted_at
        return None

    @property
    def resolution_time(self):
        if self.submitted_at and self.resolved_at:
            return self.resolved_at - self.submitted_at
        return None


class IncidentMedia(UUIDModel):
    """Photo/video/document attached to an incident."""

    TYPES = [("image", "Image"), ("video", "Video"), ("document", "Document")]

    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name="media")
    file = models.FileField(upload_to="incidents/%Y/%m/")
    media_type = models.CharField(max_length=10, choices=TYPES)
    mime_type = models.CharField(max_length=80)
    size_bytes = models.PositiveBigIntegerField(default=0)
    original_filename = models.CharField(max_length=255, blank=True)
    thumbnail = models.FileField(upload_to="incidents/thumbs/%Y/%m/", null=True, blank=True)
    caption = models.CharField(max_length=200, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    exif_stripped = models.BooleanField(default=False)
    scan_status = models.CharField(
        max_length=12,
        default="pending",
        choices=[
            ("pending", "Pending"),
            ("clean", "Clean"),
            ("infected", "Infected"),
            ("skipped", "Skipped"),
        ],
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.media_type} for {self.incident.reference_number}"


class IncidentComment(UUIDModel):
    """Public discussion or internal authority note on an incident."""

    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="comments",
    )
    body = models.TextField()
    is_internal = models.BooleanField(default=False, db_index=True)
    moderation_status = models.CharField(
        max_length=12,
        default="visible",
        choices=[
            ("visible", "Visible"),
            ("flagged", "Flagged"),
            ("hidden", "Hidden"),
        ],
    )
    # Photo comment: link to specific media
    media = models.ForeignKey(
        "IncidentMedia", null=True, blank=True, on_delete=models.SET_NULL, related_name="comments"
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Comment by {self.author} on {self.incident.reference_number}"


class IncidentStatusHistory(UUIDModel):
    """Immutable record of each status transition (public or internal visibility)."""

    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(
        max_length=20, choices=IncidentStatus.choices, null=True, blank=True
    )
    to_status = models.CharField(max_length=20, choices=IncidentStatus.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    note = models.CharField(max_length=500, blank=True)
    is_public = models.BooleanField(default=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name_plural = "incident status histories"

    def __str__(self) -> str:
        return f"{self.incident.reference_number}: {self.from_status} → {self.to_status}"


class IncidentAssignment(UUIDModel):
    """Assignment of an incident to a staff member or responder (with history)."""

    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name="assignments")
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assignment_records"
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assignments_made",
    )
    released_at = models.DateTimeField(null=True, blank=True)
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.incident.reference_number} → {self.assignee.email}"


class IncidentEscalation(UUIDModel):
    """Escalation event with level and reason (emergency workflow)."""

    LEVELS = [
        ("level_1", "Level 1 — Supervisor"),
        ("level_2", "Level 2 — Department head"),
        ("level_3", "Level 3 — Emergency operations"),
    ]

    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name="escalations")
    level = models.CharField(max_length=10, choices=LEVELS, default="level_1")
    reason = models.TextField(blank=True)
    escalated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class IncidentResolution(UUIDModel):
    """Resolution record with evidence references and approval trail."""

    incident = models.OneToOneField(Incident, on_delete=models.CASCADE, related_name="resolution")
    summary = models.TextField()
    evidence = models.ManyToManyField(IncidentMedia, blank=True, related_name="+")
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="resolutions",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="resolutions_approved",
    )
    approved_at = models.DateTimeField(null=True, blank=True)


class IncidentFeedback(UUIDModel):
    """Citizen satisfaction rating and resolution confirmation."""

    incident = models.OneToOneField(Incident, on_delete=models.CASCADE, related_name="feedback")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    # Nullable: a citizen may confirm the resolution without giving a rating.
    rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comment = models.TextField(blank=True)
    confirmed_resolution = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        score = f"{self.rating}/5" if self.rating else "no rating"
        return f"Feedback ({score}) for {self.incident.reference_number}"
