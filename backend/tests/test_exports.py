"""
Export endpoint tests: /incidents/export/csv/ and /incidents/<pk>/export/pdf/.

Both were 404ing (frontend called them; backend never registered them) and the
"PDF" endpoint only ever emitted print-to-PDF HTML.
"""

import pytest
from django.urls import resolve
from rest_framework import status

from apps.incidents.models import IncidentStatusHistory
from apps.incidents.pdf import build_incident_pdf
from apps.incidents.views import IncidentViewSet
from apps.incidents.views_export import IncidentExportCSVView, IncidentExportPDFView

pytestmark = pytest.mark.django_db

CSV_HEADER = (
    "reference_number,title,category,severity,status,ward,department,"
    "created_at,sla_deadline,sla_breached"
)


def _rows(response) -> list[str]:
    return response.content.decode("utf-8").splitlines()


class TestExportRouting:
    def test_csv_path_resolves_to_export_view(self):
        match = resolve("/api/v1/incidents/export/csv/")
        assert match.func.cls is IncidentExportCSVView

    def test_pdf_path_resolves_to_export_view(self):
        match = resolve("/api/v1/incidents/11111111-1111-1111-1111-111111111111/export/pdf/")
        assert match.func.cls is IncidentExportPDFView

    def test_incident_detail_route_still_resolves_to_viewset(self):
        match = resolve("/api/v1/incidents/11111111-1111-1111-1111-111111111111/")
        assert match.func.cls is IncidentViewSet


class TestCsvExport:
    def test_csv_downloads_with_attachment_header(self, client, citizen, incident):
        client.force_authenticate(user=citizen)
        response = client.get("/api/v1/incidents/export/csv/")

        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "text/csv"
        assert response["Content-Disposition"] == 'attachment; filename="safecity-incidents.csv"'
        rows = _rows(response)
        assert rows[0] == CSV_HEADER
        assert len(rows) == 2  # header + the citizen's own incident
        assert incident.reference_number in rows[1]

    def test_csv_scopes_citizen_to_own_incidents(self, client, citizen, incident_factory):
        mine = incident_factory(reporter=citizen)
        incident_factory()  # someone else's — reporter None
        client.force_authenticate(user=citizen)
        rows = _rows(client.get("/api/v1/incidents/export/csv/"))
        assert len(rows) == 2
        assert mine.reference_number in rows[1]

    def test_csv_honours_filter_params(self, client, citizen, incident_factory):
        incident_factory(reporter=citizen, severity="high")
        incident_factory(reporter=citizen, severity="low")
        client.force_authenticate(user=citizen)
        rows = _rows(client.get("/api/v1/incidents/export/csv/?severity=low"))
        assert len(rows) == 2
        assert ",low," in rows[1]
        assert ",high," not in rows[1]

    def test_csv_empty_result_is_valid_csv(self, client, citizen):
        """No rows → header-only CSV, never a 404/500."""
        client.force_authenticate(user=citizen)
        response = client.get("/api/v1/incidents/export/csv/")
        assert response.status_code == status.HTTP_200_OK
        assert _rows(response) == [CSV_HEADER]

    def test_csv_anonymous_sees_active_and_recently_resolved(self, client, incident_factory):
        """Public-map view: new/active reports are visible; resolved ones
        drop out after RESOLVED_VISIBLE_DAYS."""
        from datetime import timedelta

        from django.utils import timezone

        incident_factory(status="verified")
        incident_factory(status="submitted")
        incident_factory(status="resolved", resolved_at=timezone.now())
        incident_factory(
            status="resolved", resolved_at=timezone.now() - timedelta(days=10)
        )
        response = client.get("/api/v1/incidents/export/csv/")
        assert response.status_code == status.HTTP_200_OK
        rows = _rows(response)
        assert len(rows) == 4  # header + verified + submitted + recent resolved


class TestPdfExport:
    def test_pdf_download_is_a_real_pdf(self, client, citizen, incident):
        client.force_authenticate(user=citizen)
        response = client.get(f"/api/v1/incidents/{incident.id}/export/pdf/")

        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/pdf"
        assert response["Content-Disposition"].startswith("attachment;")
        assert response["Content-Disposition"].endswith(".pdf\"")
        body = response.content
        assert body.startswith(b"%PDF-1.4")
        assert body.endswith(b"%%EOF")
        assert b"/Type /Catalog" in body

    def test_pdf_bytes_start_with_header_and_end_with_eof(self, incident):
        pdf = build_incident_pdf(incident)
        assert pdf.startswith(b"%PDF-1.4")
        assert pdf.endswith(b"%%EOF")

    def test_pdf_contains_incident_content(self, incident):
        pdf = build_incident_pdf(incident)
        assert incident.reference_number.encode() in pdf
        assert b"Description" in pdf
        assert b"Timeline" in pdf

    def test_pdf_escapes_parentheses_and_backslashes(self, citizen, incident_factory):
        incident = incident_factory(reporter=citizen, title="Fire (small) \\ blaze")
        pdf = build_incident_pdf(incident)
        assert b"\\(small\\)" in pdf
        assert b"\\\\ blaze" in pdf

    def test_pdf_includes_only_public_timeline_entries(self, incident):
        IncidentStatusHistory.objects.create(
            incident=incident,
            to_status="submitted",
            note="Public step",
            is_public=True,
        )
        IncidentStatusHistory.objects.create(
            incident=incident,
            to_status="verified",
            note="Internal step",
            is_public=False,
        )
        pdf = build_incident_pdf(incident)
        assert b"Public step" in pdf
        assert b"Internal step" not in pdf

    def test_pdf_requires_authentication(self, client, incident):
        response = client.get(f"/api/v1/incidents/{incident.id}/export/pdf/")
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_pdf_permission_mirrors_retrieve(self, client, citizen, incident_factory):
        """A private incident of another reporter must 404, same as retrieve."""
        other = incident_factory()  # reporter None, status submitted
        client.force_authenticate(user=citizen)
        detail = client.get(f"/api/v1/incidents/{other.id}/")
        export = client.get(f"/api/v1/incidents/{other.id}/export/pdf/")
        assert detail.status_code == status.HTTP_404_NOT_FOUND
        assert export.status_code == status.HTTP_404_NOT_FOUND
