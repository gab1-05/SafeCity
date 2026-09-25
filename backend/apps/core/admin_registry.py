"""
Django admin registration for SafeCity apps.

Registers the operational models so /admin/ is a real back-office instead of
an empty shell (closes PROJECT-MANAGEMENT.md L6). Reference data that is
read-only over the API becomes editable here (L7).
"""

from django.contrib import admin

from apps.accounts.models import Department, User
from apps.announcements.models import Announcement
from apps.core.models import SLAConfiguration, Ward, Zone
from apps.incidents.models import (
    Incident,
    IncidentCategory,
    IncidentComment,
    IncidentStatusHistory,
)

admin.site.register(
    [
        Department,
        Ward,
        Zone,
        SLAConfiguration,
        IncidentCategory,
        IncidentComment,
        IncidentStatusHistory,
        Announcement,
    ]
)


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
