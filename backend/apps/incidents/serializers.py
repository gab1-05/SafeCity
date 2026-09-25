"""
Incident serializers.

Three representations:
- IncidentSerializer: authenticated role views (scoped by permissions).
- IncidentPublicSerializer: unauthenticated/safe view — no reporter identity,
  no private address, jittered coordinates, no internal fields.
- IncidentCreateSerializer: strict server-side validation for submissions.
"""

import random

from django.conf import settings
from rest_framework import serializers

from apps.core.models import EscalationRule, SLAConfiguration
from apps.incidents.models import (
    Incident,
    IncidentCategory,
    IncidentComment,
    IncidentFeedback,
    IncidentMedia,
    Severity,
    Urgency,
)


def jitter_coordinates(lat: float, lng: float, meters: int) -> tuple[float, float]:
    """
    Deterministic per-coordinate offset (≈meters) so public maps show an
    approximate location instead of an exact point.
    """
    if meters <= 0:
        return lat, lng
    rng = random.Random(f"{lat:.6f}:{lng:.6f}")
    dlat = rng.uniform(-meters, meters) / 111_320
    dlng = rng.uniform(-meters, meters) / (
        111_320 * max(0.2, __import__("math").cos(__import__("math").radians(lat)))
    )
    return round(lat + dlat, 6), round(lng + dlng, 6)


class IncidentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = IncidentCategory
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "icon",
            "is_emergency_category",
            "requires_media",
            "display_order",
        ]


class IncidentMediaSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = IncidentMedia
        fields = [
            "id",
            "url",
            "media_type",
            "mime_type",
            "size_bytes",
            "caption",
            "thumbnail",
            "created_at",
        ]

    def get_url(self, obj):
        request = self.context.get("request")
        if obj.file and hasattr(obj.file, "url"):
            url = obj.file.url
            return request.build_absolute_uri(url) if request else url
        return None


class PublicUserStubSerializer(serializers.Serializer):
    """Only non-identifying staff attributes are ever exposed publicly."""

    full_name = serializers.CharField(read_only=True)
    department = None


class IncidentPublicSerializer(serializers.ModelSerializer):
    """
    Privacy-safe public representation.

    Excluded by design: reporter identity, contact info, private address,
    internal timeline, assigned staff names, SLA internals.
    """

    category = IncidentCategorySerializer(read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)
    ward_name = serializers.CharField(source="ward.name", read_only=True, default=None)
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()

    class Meta:
        model = Incident
        fields = [
            "id",
            "reference_number",
            "title",
            "description",
            "category",
            "subcategory",
            "severity",
            "status",
            "department_name",
            "ward_name",
            "latitude",
            "longitude",
            "address_public",
            "landmark",
            "created_at",
            "resolved_at",
        ]
        read_only_fields = fields

    def get_latitude(self, obj):
        lat, _ = jitter_coordinates(float(obj.latitude), float(obj.longitude), _jitter_meters())
        return lat

    def get_longitude(self, obj):
        _, lng = jitter_coordinates(float(obj.latitude), float(obj.longitude), _jitter_meters())
        return lng


def _jitter_meters() -> int:
    return int(settings.SAFECITY.get("PUBLIC_COORD_JITTER_METERS", 150))


class IncidentSerializer(serializers.ModelSerializer):
    """Internal representation for authorized roles."""

    category = IncidentCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=IncidentCategory.objects.all(), source="category", write_only=True
    )
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)
    ward_name = serializers.CharField(source="ward.name", read_only=True, default=None)
    assigned_staff_name = serializers.CharField(
        source="assigned_staff.full_name", read_only=True, default=None
    )
    assigned_responder_name = serializers.CharField(
        source="assigned_responder.full_name", read_only=True, default=None
    )
    reporter_display = serializers.SerializerMethodField()
    is_reporter = serializers.SerializerMethodField()
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Incident
        fields = [
            "id",
            "reference_number",
            "title",
            "description",
            "category",
            "category_id",
            "subcategory",
            "severity",
            "urgency",
            "status",
            "reporter_display",
            "is_reporter",
            "is_anonymous",
            "department",
            "department_name",
            "assigned_staff",
            "assigned_staff_name",
            "assigned_responder",
            "assigned_responder_name",
            "latitude",
            "longitude",
            "address_public",
            "address_private",
            "ward",
            "ward_name",
            "landmark",
            "is_emergency",
            "sla_deadline",
            "sla_breached",
            "is_overdue",
            "duplicate_of",
            "merged_into",
            "citizen_confirmed_resolution",
            "satisfaction_rating",
            "resolution_summary",
            "submitted_at",
            "verified_at",
            "assigned_at",
            "resolved_at",
            "closed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "status",
            "department",
            "assigned_staff",
            "assigned_responder",
            "sla_deadline",
            "sla_breached",
            "duplicate_of",
            "merged_into",
            "submitted_at",
            "verified_at",
            "assigned_at",
            "resolved_at",
            "closed_at",
        ]

    def get_reporter_display(self, obj):
        if obj.is_anonymous or obj.reporter is None:
            return "Anonymous"
        return obj.reporter.full_name

    def get_is_reporter(self, obj):
        """True when the requesting user is the reporter (drives confirm UI)."""
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and obj.reporter_id == user.id)


class IncidentCreateSerializer(serializers.ModelSerializer):
    """Server-side validation for citizen/staff submissions."""

    category_id = serializers.PrimaryKeyRelatedField(
        queryset=IncidentCategory.objects.all(), source="category"
    )
    is_anonymous = serializers.BooleanField(default=False)

    class Meta:
        model = Incident
        fields = [
            "title",
            "description",
            "category_id",
            "subcategory",
            "severity",
            "urgency",
            "latitude",
            "longitude",
            "address_public",
            "address_private",
            "ward",
            "landmark",
            "is_anonymous",
            "is_emergency",
        ]
        extra_kwargs = {
            "ward": {"required": False, "allow_null": True},
            "address_public": {"required": False, "allow_blank": True},
            "address_private": {"required": False, "allow_blank": True},
            "is_emergency": {"default": False},
        }

    def validate_title(self, value):
        value = value.strip()
        if len(value) < 8:
            raise serializers.ValidationError("Title must be at least 8 characters.")
        return value

    def validate_description(self, value):
        value = value.strip()
        if len(value) < 20:
            raise serializers.ValidationError("Description must be at least 20 characters.")
        return value

    def validate_is_emergency(self, value):
        # Only staff may declare emergencies; citizens flag urgency instead.
        request = self.context.get("request")
        if value and request and request.user.is_authenticated and not request.user.is_authority():
            return False
        return value

    def validate(self, attrs):
        lat, lng = attrs.get("latitude"), attrs.get("longitude")
        if lat is not None and lng is not None:
            if not (-90 <= float(lat) <= 90):
                raise serializers.ValidationError({"latitude": "Latitude out of range."})
            if not (-180 <= float(lng) <= 180):
                raise serializers.ValidationError({"longitude": "Longitude out of range."})
        if attrs.get("severity") == Severity.CRITICAL and attrs.get("urgency") == Urgency.LOW:
            raise serializers.ValidationError(
                {"urgency": "Critical severity cannot have low urgency."}
            )
        return attrs


class IncidentCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    media_url = serializers.SerializerMethodField()

    class Meta:
        model = IncidentComment
        fields = [
            "id",
            "incident",
            "author",
            "author_name",
            "body",
            "is_internal",
            "moderation_status",
            "created_at",
            "media",
            "media_url",
        ]
        read_only_fields = ["author", "moderation_status", "created_at", "incident", "media_url"]

    def get_author_name(self, obj):
        if obj.author is None:
            return "Unknown"
        return obj.author.full_name

    def get_media_url(self, obj):
        if obj.media and obj.media.file:
            request = self.context.get("request")
            url = obj.media.file.url
            return request.build_absolute_uri(url) if request else url
        return None


class IncidentFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncidentFeedback
        fields = ["rating", "comment", "confirmed_resolution", "created_at"]


class SLAConfigurationSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    category_slug = serializers.CharField(source="category.slug", read_only=True, default=None)

    class Meta:
        model = SLAConfiguration
        fields = [
            "id",
            "category",
            "category_name",
            "category_slug",
            "severity",
            "response_hours",
            "resolution_hours",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class EscalationRuleSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    category_slug = serializers.CharField(source="category.slug", read_only=True, default=None)

    class Meta:
        model = EscalationRule
        fields = [
            "id",
            "name",
            "priority",
            "severity",
            "category",
            "category_name",
            "category_slug",
            "statuses",
            "trigger_on_sla_breach",
            "trigger_after_hours",
            "trigger_on_reopen_count",
            "escalate_to_level",
            "notify_department_head",
            "auto_assign_supervisor",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_statuses(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Statuses must be a list.")
        valid_statuses = [
            "draft", "submitted", "under_review", "verified", "rejected", "duplicate",
            "assigned", "in_progress", "awaiting_info", "escalated", "resolved",
            "closed", "reopened"
        ]
        for v in value:
            if v not in valid_statuses:
                raise serializers.ValidationError(f"Invalid status: {v}")
        return value
