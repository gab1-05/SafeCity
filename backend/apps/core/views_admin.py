"""
Admin overview endpoint: one aggregate payload for the admin dashboard SPA.

Permission: city_admin / superuser only. Read-only; cheap single-pass queries.
"""

from django.db.models import Avg, Count, Q
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import DeletionRequest, Department, User, UserRole
from apps.accounts.permissions import IsCityAdmin
from apps.audit.models import AuditLog
from apps.incidents.models import Incident, IncidentStatus


class AdminOverviewView(APIView):
    permission_classes = [IsCityAdmin]

    def get(self, request):
        now = timezone.now()
        week_ago = now - timezone.timedelta(days=7)

        users = User.objects.aggregate(
            total=Count("id"),
            citizens=Count("id", filter=Q(role=UserRole.CITIZEN)),
            staff=Count(
                "id",
                filter=Q(
                    role__in=[
                        UserRole.DEPARTMENT_STAFF,
                        UserRole.EMERGENCY_RESPONDER,
                        UserRole.CITY_ADMIN,
                    ]
                ),
            ),
            locked=Count("id", filter=Q(locked_until__gt=now)),
            new_this_week=Count("id", filter=Q(created_at__gte=week_ago)),
            active_this_week=Count("id", filter=Q(last_login__gte=week_ago)),
            with_2fa=Count("id", filter=Q(two_factor_enabled=True)),
        )

        open_statuses = [
            IncidentStatus.SUBMITTED,
            IncidentStatus.UNDER_REVIEW,
            IncidentStatus.VERIFIED,
            IncidentStatus.ASSIGNED,
            IncidentStatus.IN_PROGRESS,
            IncidentStatus.AWAITING_INFO,
            IncidentStatus.REOPENED,
            IncidentStatus.ESCALATED,
        ]
        incidents = Incident.objects.aggregate(
            total=Count("id"),
            open=Count("id", filter=Q(status__in=open_statuses)),
            awaiting_verification=Count(
                "id", filter=Q(status__in=[IncidentStatus.SUBMITTED, IncidentStatus.UNDER_REVIEW])
            ),
            overdue=Count("id", filter=Q(sla_breached=True, status__in=open_statuses)),
            emergency=Count("id", filter=Q(is_emergency=True, status__in=open_statuses)),
            resolved_rate=Count("id", filter=Q(status__in=[IncidentStatus.RESOLVED, IncidentStatus.CLOSED]))
            * 100.0
            / Count("id"),
        )

        departments = []
        for dept in Department.objects.all().order_by("name"):
            dept_staff = User.objects.filter(department=dept, is_active=True).exclude(role=UserRole.CITIZEN).count()
            departments.append(
                {
                    "id": str(dept.id),
                    "name": dept.name,
                    "open_incidents": Incident.objects.filter(
                        department=dept, status__in=open_statuses
                    ).count(),
                    "staff_count": dept_staff,
                }
            )

        deletion_requests = [
            {
                "id": str(r.id),
                "email": r.user.email,
                "reason": r.reason,
                "requested_at": r.created_at,
            }
            for r in DeletionRequest.objects.filter(status="pending").select_related("user")[:10]
        ]

        recent_audit = [
            {
                "id": str(a.id),
                "action": a.action,
                "actor": (a.actor.email if a.actor else None),
                "created_at": a.created_at,
            }
            for a in AuditLog.objects.select_related("actor").order_by("-created_at")[:10]
        ]

        avg_satisfaction = Incident.objects.filter(
            satisfaction_rating__isnull=False
        ).aggregate(v=Avg("satisfaction_rating"))["v"]

        status_breakdown = [
            {"status": row["status"], "count": row["count"]}
            for row in Incident.objects.values("status").annotate(count=Count("id")).order_by("status")
        ]

        by_category = [
            {"name": row["category__name"], "count": row["count"]}
            for row in Incident.objects.values("category__name").annotate(count=Count("id")).order_by("-count")[:10]
        ]

        by_ward = [
            {"name": row["ward__name"], "count": row["count"]}
            for row in Incident.objects.values("ward__name").annotate(count=Count("id")).order_by("-count")[:10]
        ]

        # SLA breaches - top 10 most overdue
        sla_breaches = []
        for inc in Incident.objects.filter(sla_breached=True, status__in=open_statuses).select_related("department")[:10]:
            overdue_hours = int((now - inc.sla_deadline).total_seconds() / 3600) if inc.sla_deadline else 0
            sla_breaches.append({
                "id": str(inc.id),
                "reference": inc.reference_number,
                "title": inc.title,
                "department": inc.department.name if inc.department else "Unassigned",
                "overdue_hours": overdue_hours,
            })

        return Response(
            {
                "users": {
                    "total": users["total"],
                    "citizens": users["citizens"],
                    "staff": users["staff"],
                    "locked": users["locked"],
                    "new_this_week": users["new_this_week"],
                    "active_this_week": users["active_this_week"],
                    "with_2fa": users["with_2fa"],
                },
                "incidents": {
                    "total": incidents["total"],
                    "open": incidents["open"],
                    "awaiting_verification": incidents["awaiting_verification"],
                    "overdue": incidents["overdue"],
                    "emergency": incidents["emergency"],
                    "resolved_rate_pct": round(incidents["resolved_rate"], 1)
                    if incidents["total"]
                    else None,
                    "sla_compliance_pct": None,  # authoritative figure lives in analytics.summary
                    "avg_satisfaction": avg_satisfaction,
                    "status_breakdown": status_breakdown,
                    "by_category": by_category,
                    "by_ward": by_ward,
                },
                "departments": departments,
                "deletion_requests": deletion_requests,
                "recent_audit": recent_audit,
                "sla_breaches": sla_breaches,
            }
        )
