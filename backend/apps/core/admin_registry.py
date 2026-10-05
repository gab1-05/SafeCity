"""
Django admin registration for SafeCity apps.

Registers the operational models so /admin/ is a real back-office instead of
an empty shell (closes PROJECT-MANAGEMENT.md L6). Reference data that is
read-only over the API becomes editable here (L7).
"""

from django.contrib import admin

from apps.accounts.models import (
    ConsentRecord,
    DeletionRequest,
    Department,
    RoleRequest,
    User,
)
from apps.ai.models import AIRecommendation
from apps.analytics.models import DailyIncidentAggregate
from apps.announcements.models import Announcement
from apps.audit.models import AuditLog
from apps.core.models import EscalationRule, IntegrationConfiguration, SLAConfiguration, Ward, Zone
from apps.incidents.models import (
    Incident,
    IncidentCategory,
    IncidentComment,
    IncidentFeedback,
    IncidentMedia,
    IncidentStatusHistory,
)
from apps.notifications.models import Notification, NotificationPreference

admin.site.register(
    [
        Department,
        Ward,
        Zone,
        SLAConfiguration,
        EscalationRule,
        IntegrationConfiguration,
        IncidentCategory,
        IncidentMedia,
        IncidentComment,
        IncidentFeedback,
        IncidentStatusHistory,
        Announcement,
        Notification,
        NotificationPreference,
        DailyIncidentAggregate,
        AIRecommendation,
        RoleRequest,
        DeletionRequest,
        ConsentRecord,
    ]
)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Append-only trail: visible but never editable or deletable."""

    list_display = ("action", "actor", "object_type", "object_id", "created_at")
    list_filter = ("action",)
    search_fields = ("action", "object_id")
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "role", "department", "is_active", "created_at")
    list_filter = ("role", "is_active", "department")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-created_at",)
    readonly_fields = ("last_login",)


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = (
        "reference_number",
        "title",
        "status",
        "severity",
        "department",
        "assigned_staff",
        "sla_breached",
        "created_at",
    )
    list_filter = ("status", "severity", "is_emergency", "sla_breached", "department")
    search_fields = ("reference_number", "title", "description")
    readonly_fields = ("reference_number",)
    date_hierarchy = "created_at"
