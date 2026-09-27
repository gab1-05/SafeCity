"""
Analytics API — role-scoped aggregations over Incident.

Citizen requests return 403; staff get department-scoped numbers; admins see
everything. CSV export mirrors the JSON summary.
"""

import csv
from datetime import timedelta

from django.core.cache import cache
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserRole
from apps.incidents.models import Incident, IncidentStatus

# Dashboard KPIs are expensive (~15 aggregate queries) and polled every
# 30–60s by the SPA. A 60s TTL keyed by role scope keeps dashboards snappy
# without ever showing data older than one poll interval.
ANALYTICS_SUMMARY_TTL_SECONDS = 60

OPEN_STATUSES = [
    IncidentStatus.SUBMITTED,
    IncidentStatus.UNDER_REVIEW,
    IncidentStatus.VERIFIED,
    IncidentStatus.ASSIGNED,
    IncidentStatus.IN_PROGRESS,
    IncidentStatus.AWAITING_INFO,
    IncidentStatus.ESCALATED,
    IncidentStatus.REOPENED,
]


def _scope_queryset(user):
    qs = Incident.objects.filter(deleted_at__isnull=True)
    if user.role in (UserRole.CITY_ADMIN, UserRole.SUPERUSER):
        return qs
    if user.role == UserRole.DEPARTMENT_STAFF:
        return qs.filter(department_id=user.department_id)
    if user.role == UserRole.EMERGENCY_RESPONDER:
        return qs.filter(Q(assigned_responder=user) | Q(severity__in=["high", "critical"]))
    return Incident.objects.none()


def _parse_range(request):
    days = int(request.query_params.get("days", 30))
    days = max(1, min(days, 365))
    end = timezone.now()
    start = end - timedelta(days=days)
    return start, end


class AnalyticsSummaryView(APIView):
    """GET /api/v1/analytics/summary/ — headline KPIs."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role == UserRole.CITIZEN:
            return Response({"detail": "Not allowed."}, status=403)
        user = request.user
        if user.role in (UserRole.CITY_ADMIN, UserRole.SUPERUSER):
            scope_id = "all"
        elif user.role == UserRole.DEPARTMENT_STAFF:
            scope_id = f"dept:{user.department_id}"
        else:  # emergency responder — assignment-scoped
            scope_id = f"user:{user.id}"
        try:
            days = max(1, min(int(request.query_params.get("days", 30)), 365))
        except (TypeError, ValueError):
            days = 30
        cache_key = f"analytics:summary:v1:{scope_id}:{days}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)
        qs = _scope_queryset(request.user)
        start, end = _parse_range(request)
        window = qs.filter(created_at__range=(start, end))

        response_times = window.filter(verified_at__isnull=False).annotate(
            rt=ExpressionWrapper(F("verified_at") - F("submitted_at"), output_field=DurationField())
        )
        resolution_times = window.filter(resolved_at__isnull=False).annotate(
            rt=ExpressionWrapper(F("resolved_at") - F("submitted_at"), output_field=DurationField())
        )
        resolved = window.filter(status__in=[IncidentStatus.RESOLVED, IncidentStatus.CLOSED])

        def _avg_minutes(queryset, field="rt"):
            agg = queryset.aggregate(a=Avg(field))
            return int(agg["a"].total_seconds() // 60) if agg["a"] else None

        payload = {
            "total": qs.count(),
                "in_window": window.count(),
                "open": qs.filter(status__in=OPEN_STATUSES).count(),
                "new_in_window": window.count(),
                "awaiting_verification": qs.filter(
                    status__in=[IncidentStatus.SUBMITTED, IncidentStatus.UNDER_REVIEW]
                ).count(),
                "high_priority": qs.filter(
                    severity__in=["high", "critical"], status__in=OPEN_STATUSES
                ).count(),
                "overdue": qs.filter(sla_breached=True, status__in=OPEN_STATUSES).count(),
                "emergency": qs.filter(is_emergency=True, status__in=OPEN_STATUSES).count(),
                "resolved_in_window": resolved.count(),
                "reopened_in_window": window.filter(status=IncidentStatus.REOPENED).count(),
                "duplicates_in_window": window.filter(status=IncidentStatus.DUPLICATE).count(),
                "avg_response_minutes": _avg_minutes(response_times),
                "avg_resolution_minutes": _avg_minutes(resolution_times),
                "sla_compliance_pct": (
                    round(
                        100
                        * (window.count() - window.filter(sla_breached=True).count())
                        / window.count(),
                        1,
                    )
                    if window.count()
                    else None
                ),
                "resolution_rate_pct": (
                    round(100 * resolved.count() / window.count(), 1) if window.count() else None
                ),
                "avg_satisfaction": round(
                    window.aggregate(a=Avg("satisfaction_rating"))["a"] or 0, 2
                )
                or None,
            }
        cache.set(cache_key, payload, ANALYTICS_SUMMARY_TTL_SECONDS)
        return Response(payload)


class AnalyticsTrendView(APIView):
    """GET /api/v1/analytics/trends/?days=30 — incidents per day."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role == UserRole.CITIZEN:
            return Response({"detail": "Not allowed."}, status=403)
        start, end = _parse_range(request)
        qs = _scope_queryset(request.user).filter(created_at__range=(start, end))
        by_day = (
            qs.extra({"day": "date(created_at)"})
            .values("day")
            .annotate(
                total=Count("id"), resolved=Count("id", filter=Q(status__in=["resolved", "closed"]))
            )
            .order_by("day")
        )
        return Response(
            [
                {"date": row["day"], "total": row["total"], "resolved": row["resolved"]}
                for row in by_day
            ]
        )


class AnalyticsBreakdownView(APIView):
    """GET /api/v1/analytics/by-<dimension>/ — category/ward/department/status."""

    permission_classes = [permissions.IsAuthenticated]
    DIMENSIONS = {
        "category": "category__name",
        "ward": "ward__name",
        "department": "department__name",
        "status": "status",
        "severity": "severity",
    }

    def get(self, request, dimension: str):
        if request.user.role == UserRole.CITIZEN:
            return Response({"detail": "Not allowed."}, status=403)
        if dimension not in self.DIMENSIONS:
            return Response({"detail": "Unknown dimension."}, status=404)
        start, end = _parse_range(request)
        qs = _scope_queryset(request.user).filter(created_at__range=(start, end))
        field = self.DIMENSIONS[dimension]
        rows = (
            qs.values(field)
            .annotate(
                total=Count("id"),
                resolved=Count("id", filter=Q(status__in=["resolved", "closed"])),
                breached=Count("id", filter=Q(sla_breached=True)),
            )
            .order_by("-total")
        )
        return Response(
            [
                {
                    "name": row[field] or "—",
                    "total": row["total"],
                    "resolved": row["resolved"],
                    "sla_breached": row["breached"],
                }
                for row in rows
            ]
        )


def _csv_safe(value) -> str:
    """
    Neutralize spreadsheet formula injection (OWASP CSV injection).

    A cell beginning with = + - @ could execute as a formula when the export is
    opened in Excel/Sheets. Prefixing with a tab makes it inert text.
    """
    text = str(value)
    if text.startswith(("=", "+", "-", "@", "\t", "\r")):
        return f"'{text}"
    return text


class AnalyticsExportView(APIView):
    """GET /api/v1/analytics/export.csv/ — summary CSV download."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role == UserRole.CITIZEN:
            return Response({"detail": "Not allowed."}, status=403)
        start, end = _parse_range(request)
        qs = _scope_queryset(request.user).filter(created_at__range=(start, end))
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="safecity-analytics.csv"'
        writer = csv.writer(response)
        writer.writerow(
            [
                "reference_number",
                "title",
                "category",
                "severity",
                "status",
                "department",
                "ward",
                "created_at",
                "resolved_at",
                "sla_breached",
                "satisfaction_rating",
            ]
        )
        for i in qs.select_related("category", "department", "ward").iterator(500):
            writer.writerow(
                [
                    _csv_safe(i.reference_number),
                    _csv_safe(i.title),
                    _csv_safe(i.category.name),
                    i.severity,
                    i.status,
                    _csv_safe(i.department.name if i.department else ""),
                    _csv_safe(i.ward.name if i.ward else ""),
                    i.created_at.isoformat(),
                    i.resolved_at.isoformat() if i.resolved_at else "",
                    i.sla_breached,
                    i.satisfaction_rating or "",
                ]
            )
        return response
