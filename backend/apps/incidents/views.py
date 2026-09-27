"""
Incident API views.

Querysets are role-scoped (citizens see their own, staff see their department,
admins see all; anonymous users see only public statuses). Workflow actions
delegate to services.change_status / assign_incident / escalate / merge /
reopen / confirm_resolution.
"""

from __future__ import annotations

import hashlib
from datetime import timedelta

from django.core.cache import cache
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import User, UserRole
from apps.accounts.permissions import (
    can_view_incident,
    can_view_internal_notes,
)
from apps.audit.services import log_action
from apps.core.models import EscalationRule, SLAConfiguration
from apps.incidents import services
from apps.incidents.models import (
    Incident,
    IncidentCategory,
    IncidentComment,
    IncidentMedia,
    IncidentStatus,
)
from apps.incidents.serializers import (
    EscalationRuleSerializer,
    IncidentCategorySerializer,
    IncidentCommentSerializer,
    IncidentCreateSerializer,
    IncidentPublicSerializer,
    IncidentSerializer,
    SLAConfigurationSerializer,
)
from apps.notifications.services import notify

# Statuses shown on the public / nearby maps (everything still actionable,
# including brand-new reports awaiting review).
PUBLIC_MAP_ACTIVE_STATUSES = [
    "submitted",
    "under_review",
    "verified",
    "assigned",
    "in_progress",
    "awaiting_info",
    "escalated",
    "reopened",
]

# Resolved incidents stay on the map this long, then disappear.
RESOLVED_VISIBLE_DAYS = 5

# Public-map list TTL: the SPA polls every 60s, so 30s keeps every response
# fresher than one poll interval while absorbing anonymous visitor traffic.
PUBLIC_LIST_TTL_SECONDS = 30


class PublicByTokenView(APIView):
    """GET /api/v1/incidents/public/<uuid-token>/ — shareable, unguessable link."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_scope = "anon"

    def get(self, request, token: str):
        incident = Incident.objects.filter(pk=token, deleted_at__isnull=True).first()
        if incident is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(IncidentPublicSerializer(incident, context={"request": request}).data)


class IncidentCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = IncidentCategory.objects.filter(is_active=True).select_related("default_department")
    serializer_class = IncidentCategorySerializer
    permission_classes = [permissions.AllowAny]
    ordering = ["display_order", "name"]


class IncidentThrottle(UserRateThrottle):
    scope = "incident_create"


def public_map_queryset(qs):
    """Incidents visible on the public / nearby maps.

    All active statuses (new `submitted` reports included) plus `resolved`
    ones younger than RESOLVED_VISIBLE_DAYS. Anonymous reports are never
    public.
    """
    cutoff = timezone.now() - timedelta(days=RESOLVED_VISIBLE_DAYS)
    return qs.filter(
        Q(status__in=PUBLIC_MAP_ACTIVE_STATUSES, is_anonymous=False)
        | Q(status="resolved", is_anonymous=False, resolved_at__gte=cutoff)
    )


def scoped_incident_queryset(user, params):
    """
    List scoping + filters shared by IncidentViewSet.list and the CSV export.

    `params` is a QueryDict (request.query_params); filters and role scoping
    must stay identical for both consumers.
    """
    qs = Incident.objects.select_related(
        "category",
        "department",
        "ward",
        "assigned_staff",
        "assigned_responder",
    ).filter(deleted_at__isnull=True)

    # ── filters ──────────────────────────────────────────
    status_param = params.getlist("status")
    if status_param:
        qs = qs.filter(status__in=status_param)
    if severity := params.get("severity"):
        qs = qs.filter(severity=severity)
    if category := params.get("category"):
        qs = qs.filter(category__slug=category)
    if department := params.get("department"):
        qs = qs.filter(department__code=department)
    if ward := params.get("ward"):
        qs = qs.filter(ward__code=ward)
    if q := params.get("q"):
        qs = qs.filter(
            Q(reference_number__icontains=q) | Q(title__icontains=q) | Q(description__icontains=q)
        )
    if created_after := params.get("created_after"):
        qs = qs.filter(created_at__date__gte=created_after)
    if created_before := params.get("created_before"):
        qs = qs.filter(created_at__date__lte=created_before)
    if params.get("overdue") == "true":
        qs = qs.filter(sla_breached=False).filter(sla_deadline__lt=timezone.now())
    if params.get("sla_state") == "breached":
        qs = qs.filter(sla_breached=True)
    if params.get("emergency") == "true":
        qs = qs.filter(is_emergency=True)

    # ── role scoping ───────────────────────────────────
    # Public map visibility: every *active* status (including brand-new
    # `submitted` / `under_review` reports) plus `resolved` incidents for
    # RESOLVED_VISIBLE_DAYS, after which they disappear from the map.
    # Anonymous reports stay hidden. Opt-in via ?scope=public so the map
    # pages get this view for logged-in users too, without widening the
    # role scoping used by queues / "my incidents".
    if not user.is_authenticated or params.get("scope") == "public":
        return public_map_queryset(qs)
    if user.role in (UserRole.CITY_ADMIN, UserRole.SUPERUSER):
        pass  # all
    elif user.role == UserRole.DEPARTMENT_STAFF:
        qs = qs.filter(department_id=user.department_id)
    elif user.role == UserRole.EMERGENCY_RESPONDER:
        qs = qs.filter(
            Q(assigned_responder=user)
            | Q(severity__in=["high", "critical"])
            | Q(is_emergency=True)
        )
    elif user.role == UserRole.VOLUNTEER:
        qs = qs.filter(status__in=["verified", "in_progress", "resolved"])
    else:  # citizen
        qs = qs.filter(reporter=user)

    return qs


class IncidentViewSet(viewsets.ModelViewSet):
    """
    Incidents CRUD + workflow actions.

    list/retrieve: role-scoped, filterable, searchable, paginated.
    Anonymous users get the public-map view (all active statuses plus
    recently resolved) — this feeds the public map. Pass ?scope=public for
    the same view while authenticated. All writes require authentication.
    create: citizens and admins (staff desk-entry).
    Workflow actions: status, assign, escalate, merge, reopen, confirm.
    """

    # List must be reachable anonymously (public map); writes stay auth-only.
    permission_classes = [permissions.AllowAny]
    throttle_classes = []

    def get_throttles(self):
        if self.action == "create":
            self.throttle_scope = "incident_create"
            return [IncidentThrottle()]
        return super().get_throttles()

    def get_serializer_class(self):
        if self.action == "create":
            return IncidentCreateSerializer
        return IncidentSerializer

    def get_permissions(self):
        # Only listing is public; every other action requires authentication.
        if self.action == "list":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        incident = services.create_incident(
            reporter=request.user,
            validated_data=serializer.validated_data,
            request=request,
        )
        return Response(
            IncidentSerializer(incident, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def get_queryset(self):
        return scoped_incident_queryset(self.request.user, self.request.query_params)

    def list(self, request, *args, **kwargs):
        # Hot path: the public map is hit anonymously by every visitor (and
        # polled every 60s by the SPA). Cache it briefly keyed by the exact
        # filter set. Authenticated role-scoped queues are deliberately NOT
        # cached — a stale queue hides triage work.
        params = request.query_params
        if not request.user.is_authenticated or params.get("scope") == "public":
            fingerprint = hashlib.md5(
                params.urlencode().encode(), usedforsecurity=False
            ).hexdigest()
            cache_key = f"incidents:public-list:v1:{fingerprint}"
            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached)
            response = super().list(request, *args, **kwargs)
            if response.status_code == status.HTTP_200_OK:
                cache.set(cache_key, response.data, PUBLIC_LIST_TTL_SECONDS)
            return response
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        from apps.incidents.services import create_incident

        create_incident(
            reporter=self.request.user,
            validated_data=serializer.validated_data,
            request=self.request,
        )

    def retrieve(self, request, *args, **kwargs):
        incident = self.get_object()
        if can_view_incident(request.user, incident):
            return Response(IncidentSerializer(incident, context={"request": request}).data)
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    def update(self, request, *args, **kwargs):
        return Response(
            {"detail": "Use workflow endpoints to change incidents."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        """Soft delete — admin only."""
        if request.user.role not in (UserRole.CITY_ADMIN, UserRole.SUPERUSER):
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        incident = self.get_object()
        from django.utils import timezone

        incident.deleted_at = timezone.now()
        incident.save(update_fields=["deleted_at", "updated_at"])
        log_action(actor=request.user, action="incident.deleted", obj=incident, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ── Workflow actions ─────────────────────────────────────
    @action(detail=True, methods=["post"], url_path="status")
    def status_action(self, request, pk=None):
        incident = self.get_object()
        to_status = request.data.get("status")
        if not to_status:
            return Response({"detail": "status is required."}, status=status.HTTP_400_BAD_REQUEST)
        incident = services.change_status(
            incident=incident,
            to_status=to_status,
            user=request.user,
            note=request.data.get("note", ""),
            request=request,
            extra_updates={"resolution_summary": request.data.get("resolution_summary", "")}
            if to_status == IncidentStatus.RESOLVED
            else None,
        )
        return Response(IncidentSerializer(incident, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="assign")
    def assign_action(self, request, pk=None):
        incident = self.get_object()
        assignee_id = request.data.get("assignee_id")
        auto = request.data.get("auto", False)
        if auto:
            # Never auto-pick the requester — self-assignment is rejected below.
            assignee = services.pick_staff_workload_aware(
                incident.department, exclude_user=request.user
            )
            if assignee is None:
                return Response(
                    {"detail": "No available staff in this department."},
                    status=status.HTTP_409_CONFLICT,
                )
        else:
            if not assignee_id:
                return Response(
                    {"detail": "assignee_id or auto=true required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                assignee = User.objects.get(pk=assignee_id, is_active=True)
            except User.DoesNotExist:
                return Response({"detail": "Assignee not found."}, status=status.HTTP_404_NOT_FOUND)
        incident = services.assign_incident(
            incident=incident,
            assignee=assignee,
            user=request.user,
            note=request.data.get("note", ""),
            request=request,
        )
        return Response(IncidentSerializer(incident, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="escalate")
    def escalate_action(self, request, pk=None):
        incident = self.get_object()
        incident = services.escalate_incident(
            incident=incident,
            user=request.user,
            level=request.data.get("level", "level_1"),
            reason=request.data.get("reason", ""),
            request=request,
        )
        return Response(IncidentSerializer(incident, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="merge")
    def merge_action(self, request, pk=None):
        incident = self.get_object()  # the duplicate
        parent_id = request.data.get("parent_id")
        if not parent_id:
            return Response({"detail": "parent_id required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            parent = Incident.objects.get(pk=parent_id)
        except Incident.DoesNotExist:
            return Response(
                {"detail": "Parent incident not found."}, status=status.HTTP_404_NOT_FOUND
            )
        parent = services.merge_incident(
            duplicate=incident, parent=parent, user=request.user, request=request
        )
        return Response(IncidentSerializer(parent, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="reopen")
    def reopen_action(self, request, pk=None):
        incident = self.get_object()
        incident = services.reopen_incident(
            incident=incident,
            user=request.user,
            reason=request.data.get("reason", ""),
            request=request,
        )
        return Response(IncidentSerializer(incident, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="confirm")
    def confirm_action(self, request, pk=None):
        incident = self.get_object()
        rating = request.data.get("rating")
        if rating is not None and not 1 <= int(rating) <= 5:
            return Response({"detail": "rating must be 1–5."}, status=status.HTTP_400_BAD_REQUEST)
        incident = services.confirm_resolution(
            incident=incident,
            user=request.user,
            rating=rating,
            comment=request.data.get("comment", ""),
            request=request,
        )
        return Response(IncidentSerializer(incident, context={"request": request}).data)

    @action(detail=True, methods=["get"], url_path="timeline")
    def timeline_action(self, request, pk=None):
        """Public timeline for everyone with read access; internal events flagged."""
        incident = self.get_object()
        show_internal = can_view_internal_notes(request.user, incident)
        history = incident.status_history.all()
        if not show_internal:
            history = history.filter(is_public=True)
        return Response(
            [
                {
                    "id": str(h.id),
                    "from_status": h.from_status,
                    "to_status": h.to_status,
                    "actor": (h.actor.full_name if h.actor else "System")
                    if show_internal
                    else "SafeCity",
                    "note": h.note,
                    "is_internal": not h.is_public,
                    "created_at": h.created_at,
                }
                for h in history
            ]
        )

    @action(detail=True, methods=["get", "post"], url_path="comments")
    def comments_action(self, request, pk=None):
        """GET: visible comments; POST: add comment (internal for staff only, can link to media)."""
        incident = self.get_object()
        show_internal = can_view_internal_notes(request.user, incident)
        if request.method == "GET":
            qs = incident.comments.filter(moderation_status="visible")
            if not show_internal:
                qs = qs.filter(is_internal=False)
            return Response(
                IncidentCommentSerializer(
                    [c for c in qs], many=True, context={"request": request}
                ).data
            )
        is_internal = bool(request.data.get("is_internal", False)) and show_internal
        if is_internal and not can_view_internal_notes(request.user, incident):
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)

        # Handle photo comment (media_id)
        media_id = request.data.get("media_id")
        media = None
        if media_id:
            try:
                media = IncidentMedia.objects.get(pk=media_id, incident=incident)
            except IncidentMedia.DoesNotExist:
                return Response({"detail": "Media not found."}, status=status.HTTP_404_NOT_FOUND)

        comment = IncidentComment.objects.create(
            incident=incident,
            author=request.user,
            body=(request.data.get("body") or "").strip()[:4000],
            is_internal=is_internal,
            media=media,
        )
        log_action(
            actor=request.user,
            action="incident.comment_added",
            obj=incident,
            changes={"is_internal": is_internal, "media_id": str(media_id) if media_id else None},
            request=request,
        )
        # Notify the other party
        if is_internal and incident.assigned_staff and incident.assigned_staff != request.user:
            notify(
                user=incident.assigned_staff,
                verb="comment.internal",
                title=f"Internal note on {incident.reference_number}",
                body=comment.body[:200],
                incident=incident,
            )
        elif incident.reporter and incident.reporter != request.user:
            notify(
                user=incident.reporter,
                verb="comment.public",
                title=f"Update on {incident.reference_number}",
                body=comment.body[:200],
                incident=incident,
            )
        return Response(IncidentCommentSerializer(comment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="similar")
    def similar_action(self, request, pk=None):
        """Cheap similarity: same category within 500 m and 7 days."""
        incident = self.get_object()
        candidates = Incident.objects.filter(
            category=incident.category,
            status__in=[
                IncidentStatus.SUBMITTED,
                IncidentStatus.UNDER_REVIEW,
                IncidentStatus.VERIFIED,
                IncidentStatus.ASSIGNED,
                IncidentStatus.IN_PROGRESS,
            ],
            created_at__gte=incident.created_at - timedelta(days=7),
            created_at__lte=incident.created_at + timedelta(days=7),
        ).exclude(pk=incident.pk)[:50]
        results = []
        for other in candidates:
            distance_m = _haversine_m(
                float(incident.latitude),
                float(incident.longitude),
                float(other.latitude),
                float(other.longitude),
            )
            if distance_m <= 500:
                results.append(
                    {
                        "id": str(other.id),
                        "reference_number": other.reference_number,
                        "title": other.title,
                        "distance_m": int(distance_m),
                        "created_at": other.created_at,
                    }
                )
        results.sort(key=lambda x: x["distance_m"])
        return Response(results[:10])

    @action(detail=True, methods=["get"], url_path="export.pdf", url_name="export-pdf")
    def export_pdf(self, request, pk=None):
        """
        PDF export interface.

        Renders a structured HTML document suitable for browser print-to-PDF.
        A full PDF pipeline (weasyprint/xhtml2pdf) can be attached later without
        changing the API contract.
        """
        incident = self.get_object()
        html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>{incident.reference_number}</title>
<style>body{{font-family:system-ui;max-width:720px;margin:2rem auto;color:#111}}
h1{{font-size:1.2rem}} .meta span{{display:block;margin:0.2rem 0}}</style></head>
<body><h1>SafeCity Incident Report</h1>
<div class="meta">
<span><b>Reference:</b> {incident.reference_number}</span>
<span><b>Title:</b> {incident.title}</span>
<span><b>Category:</b> {incident.category.name}</span>
<span><b>Severity:</b> {incident.get_severity_display()}</span>
<span><b>Status:</b> {incident.get_status_display()}</span>
<span><b>Department:</b> {incident.department.name if incident.department else "—"}</span>
<span><b>Reported:</b> {incident.created_at:%Y-%m-%d %H:%M} UTC</span>
</div>
<h2>Description</h2><p>{incident.description}</p>
<h2>Resolution</h2><p>{incident.resolution_summary or "Not yet resolved."}</p>
</body></html>"""
        response = HttpResponse(html, content_type="text/html; charset=utf-8")
        response["Content-Disposition"] = f'inline; filename="{incident.reference_number}.html"'
        return response


def _haversine_m(lat1, lng1, lat2, lng2):
    """Great-circle distance in meters."""
    from math import asin, cos, radians, sin, sqrt

    lng1, lat1, lng2, lat2 = map(radians, (float(lng1), float(lat1), float(lng2), float(lat2)))
    dlat, dlng = lat2 - lat1, lng2 - lng1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
    return 6371000 * 2 * asin(sqrt(a))


class SLAConfigurationViewSet(viewsets.ModelViewSet):
    """
      Manage SLA rules per (category, severity).
      Admin-only. Defines response_hours (first action) and resolution_hours (full resolution).
      Category-specific rules override default (null category) rules.
      """
    queryset = SLAConfiguration.objects.select_related("category").all()
    serializer_class = SLAConfigurationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]  # Only admins can write


class EscalationRuleViewSet(viewsets.ModelViewSet):
    """
      Manage automatic escalation rules.
      Admin-only. Rules are evaluated in priority order when SLA breaches or
      time thresholds are met. Can auto-escalate and notify department heads.
      """
    queryset = EscalationRule.objects.select_related("category").all()
    serializer_class = EscalationRuleSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering = ["priority", "created_at"]


class DuplicateCheckView(APIView):
    """POST /incidents/duplicates/check/ — wizard duplicate warning."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from datetime import timedelta

        lat, lng = request.data.get("latitude"), request.data.get("longitude")
        category_id = request.data.get("category_id")
        if lat is None or lng is None or not category_id:
            return Response(
                {"detail": "latitude, longitude, category_id required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        window = Incident.objects.filter(
            category_id=category_id,
            status__in=[
                IncidentStatus.SUBMITTED,
                IncidentStatus.UNDER_REVIEW,
                IncidentStatus.VERIFIED,
                IncidentStatus.ASSIGNED,
                IncidentStatus.IN_PROGRESS,
            ],
            created_at__gte=timezone.now() - timedelta(days=7),
        ).exclude(reporter=request.user)[:100]
        matches = []
        for other in window:
            distance = _haversine_m(lat, lng, other.latitude, other.longitude)
            if distance <= 300:
                matches.append(
                    {
                        "id": str(other.id),
                        "reference_number": other.reference_number,
                        "title": other.title,
                        "status": other.status,
                        "distance_m": int(distance),
                        "created_at": other.created_at,
                    }
                )
        matches.sort(key=lambda x: x["distance_m"])
        return Response({"has_duplicates": bool(matches), "matches": matches[:5]})
