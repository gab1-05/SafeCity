"""
Incident export endpoints:

- GET /api/v1/incidents/export/csv/        → filtered CSV of visible incidents
- GET /api/v1/incidents/<uuid>/export/pdf/ → real PDF download

Both are registered in apps/incidents/urls.py BEFORE the router include, so
the router's `incidents/<pk>/` pattern can never swallow them.
"""

import csv

from django.http import HttpResponse
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import can_view_incident, can_view_internal_notes
from apps.analytics.views import _csv_safe
from apps.incidents.models import Incident
from apps.incidents.pdf import build_incident_pdf
from apps.incidents.views import scoped_incident_queryset

CSV_COLUMNS = [
    "reference_number",
    "title",
    "category",
    "severity",
    "status",
    "ward",
    "department",
    "created_at",
    "sla_deadline",
    "sla_breached",
]


def _apply_ordering(qs, ordering: str | None):
    """Honour ?ordering= (same fields the list endpoint's OrderingFilter allows)."""
    if not ordering:
        return qs
    sortable = {field.name for field in Incident._meta.fields}
    clean = [
        field.strip()
        for field in ordering.split(",")
        if field.strip() and field.strip().lstrip("-") in sortable
    ]
    return qs.order_by(*clean) if clean else qs


class IncidentExportCSVView(APIView):
    """GET /incidents/export/csv/ — same filters and scoping as the list endpoint."""

    permission_classes = [permissions.AllowAny]  # scoped exactly like GET /incidents/

    def get(self, request):
        qs = scoped_incident_queryset(request.user, request.query_params)
        qs = _apply_ordering(qs, request.query_params.get("ordering"))

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="safecity-incidents.csv"'
        writer = csv.writer(response)
        writer.writerow(CSV_COLUMNS)
        for incident in qs.iterator(500):
            writer.writerow(
                [
                    _csv_safe(incident.reference_number),
                    _csv_safe(incident.title),
                    _csv_safe(incident.category.name if incident.category else ""),
                    incident.severity,
                    incident.status,
                    _csv_safe(incident.ward.name if incident.ward else ""),
                    _csv_safe(incident.department.name if incident.department else ""),
                    incident.created_at.isoformat(),
                    incident.sla_deadline.isoformat() if incident.sla_deadline else "",
                    incident.sla_breached,
                ]
            )
        return response


class IncidentExportPDFView(APIView):
    """GET /incidents/<uuid>/export/pdf/ — permission mirrors retrieving the incident."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        incident = Incident.objects.filter(pk=pk, deleted_at__isnull=True).first()
        if incident is None or not can_view_incident(request.user, incident):
            return Response({"detail": "Not found."}, status=404)
        pdf = build_incident_pdf(
            incident,
            show_actor_names=can_view_internal_notes(request.user, incident),
        )
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="safecity-incident-{incident.reference_number}.pdf"'
        )
        return response
