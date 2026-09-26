"""
SafeCity accounts: custom User, departments, consent, deletion requests,
saved locations/filters, and role definitions.
"""

import uuid

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone

from apps.core.models import UUIDModel


class UserRole(models.TextChoices):
    CITIZEN = "citizen", "Citizen"
    DEPARTMENT_STAFF = "department_staff", "Department Staff"
    EMERGENCY_RESPONDER = "emergency_responder", "Emergency Responder"
    VOLUNTEER = "volunteer", "Volunteer"
    CITY_ADMIN = "city_admin", "City Administrator"
    SUPERUSER = "superuser", "Superuser"


ROLE_GROUPS = {
    UserRole.CITIZEN: "citizens",
    UserRole.DEPARTMENT_STAFF: "department-staff",
    UserRole.EMERGENCY_RESPONDER: "emergency-responders",
    UserRole.VOLUNTEER: "volunteers",
    UserRole.CITY_ADMIN: "city-admins",
    UserRole.SUPERUSER: "superusers",
}


class UserManager(BaseUserManager):
    """Manager for email-based custom user."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", UserRole.CITIZEN)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", UserRole.SUPERUSER)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("role") != UserRole.SUPERUSER:
            raise ValueError("Superuser must have role=superuser")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, UUIDModel):
    """
    SafeCity user.

    Primary role is stored in `role`; Django groups provide composite
    permission sets (see accounts.permissions.ROLE_PERMISSIONS). Staff and
    responders may belong to a Department for scoping.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=80, blank=True)
    last_name = models.CharField(max_length=80, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(
        max_length=30, choices=UserRole.choices, default=UserRole.CITIZEN, db_index=True
    )
    department = models.ForeignKey(
        "accounts.Department",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="members",
    )

    # Django admin access
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # Privacy / preferences
    prefers_anonymous_reporting = models.BooleanField(default=False)
    marketing_consent = models.BooleanField(default=False)
    language = models.CharField(
        max_length=8,
        default="en",
        choices=[
            ("en", "English"),
            ("hi", "हिन्दी"),
            ("mr", "मराठी"),
        ],
    )

    # Brute-force protection
    failed_login_count = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    # Report quality tracking - auto-blocking for false reports
    false_report_count = models.PositiveIntegerField(default=0)
    rejected_report_count = models.PositiveIntegerField(default=0)
    is_reporting_blocked = models.BooleanField(default=False)
    reporting_blocked_at = models.DateTimeField(null=True, blank=True)
    reporting_blocked_reason = models.TextField(blank=True)

    # Two-factor authentication (enforced for admins in production)
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=64, blank=True)
    two_factor_recovery_codes = models.JSONField(default=list, blank=True)

    # Password strength / rotation
    password_changed_at = models.DateTimeField(null=True, blank=True)
    password_expires_at = models.DateTimeField(null=True, blank=True)

    # Security notifications
    login_notifications_enabled = models.BooleanField(default=True)
    security_alerts_enabled = models.BooleanField(default=True)

    # Email verification structure
    email_verified_at = models.DateTimeField(null=True, blank=True)

    # Soft deletion
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        indexes = [
            models.Index(fields=["role"], name="idx_user_role"),
            models.Index(fields=["department"], name="idx_user_department"),
        ]

    def __str__(self) -> str:
        return f"{self.email} [{self.role}]"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.email

    def is_authority(self) -> bool:
        """Any role with operational authority over incidents."""
        return self.role in {
            UserRole.DEPARTMENT_STAFF,
            UserRole.EMERGENCY_RESPONDER,
            UserRole.CITY_ADMIN,
            UserRole.SUPERUSER,
        }

    def soft_delete(self) -> None:
        """GDPR-style soft deletion: deactivate and anonymize PII, keep audit FKs."""
        self.is_active = False
        self.deleted_at = timezone.now()
        self.first_name = ""
        self.last_name = ""
        self.phone = ""
        self.email = f"deleted-{self.id}@safecity.invalid"
        self.set_unusable_password()
        self.save(
            update_fields=[
                "is_active",
                "deleted_at",
                "first_name",
                "last_name",
                "phone",
                "email",
                "password",
            ]
        )


class Department(UUIDModel):
    """Municipal department that owns incidents (Roads, Water, Fire…)."""

    name = models.CharField(max_length=120, unique=True)
    code = models.SlugField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    is_emergency_department = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class ConsentRecord(UUIDModel):
    """Immutable record of a user consent for a policy version."""

    KINDS = [
        ("terms", "Terms of service"),
        ("privacy", "Privacy policy"),
        ("data_processing", "Personal data processing"),
        ("marketing", "Marketing communication"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="consents")
    kind = models.CharField(max_length=30, choices=KINDS)
    version = models.CharField(max_length=20)
    granted_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-granted_at"]
        indexes = [models.Index(fields=["user", "kind"], name="idx_consent_user_kind")]


class DeletionRequest(UUIDModel):
    """User-initiated account deletion request (admin-completed workflow)."""

    STATUSES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("rejected", "Rejected"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="deletion_requests")
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=STATUSES, default="pending", db_index=True)
    processed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="deletion_requests_processed",
    )
    processed_at = models.DateTimeField(null=True, blank=True)


class RoleRequest(UUIDModel):
    """User request for an elevated role (admin-approved workflow).

    New signups always start as `citizen`; requesting e.g. `volunteer` or
    `department_staff` creates a pending row here. Approving flips
    `user.role` (and optionally `user.department`); rejecting just closes
    the request. `city_admin`/`superuser` are never requestable — they can
    only be assigned directly by an admin via the role endpoint.
    """

    STATUSES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="role_requests")
    requested_role = models.CharField(max_length=30, choices=UserRole.choices, db_index=True)
    department = models.ForeignKey(
        "accounts.Department",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="role_requests",
    )
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=STATUSES, default="pending", db_index=True)
    reviewed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="role_requests_reviewed",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status"], name="idx_rolereq_status")]


class SavedLocation(UUIDModel):
    """Citizen-saved location for faster reporting (home, work…)."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="saved_locations")
    label = models.CharField(max_length=80)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    address = models.CharField(max_length=250, blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_default", "label"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default=True),
                name="uniq_default_saved_location_per_user",
            )
        ]


class SavedFilter(UUIDModel):
    """Reusable incident-queue filter for authority users."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="saved_filters")
    name = models.CharField(max_length=80)
    querystring = models.CharField(max_length=1000)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="uniq_filter_name_per_user")
        ]
