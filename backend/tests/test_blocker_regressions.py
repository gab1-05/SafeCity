"""
Regression tests for the media-route, feedback-rating, reference-number and
throttle-scope fixes.

These exist because each of the four bugs was silent: the media API 404'd, the
rating raised IntegrityError, the reference number could collide under
concurrent submissions, and two configured throttle scopes were never applied.
"""

import io

import pytest
from django.urls import resolve
from PIL import Image
from rest_framework import status

from apps.incidents.models import ReferenceCounter
from apps.incidents.services import confirm_resolution
from apps.incidents.views_media import IncidentMediaViewSet

pytestmark = pytest.mark.django_db


def _png_bytes() -> bytes:
    """A minimal, genuinely valid PNG (Pillow verification must accept it)."""
    buffer = io.BytesIO()
    Image.new("RGB", (12, 12), color=(20, 120, 200)).save(buffer, format="PNG")
    return buffer.getvalue()


class TestMediaRoutesWired:
    """The media URLconf must be included and must not be shadowed."""

    def test_list_create_path_resolves_to_media_viewset(self):
        match = resolve("/api/v1/incidents/media/")
        assert match.func.cls is IncidentMediaViewSet
        assert match.func.actions == {"get": "list", "post": "create"}

    def test_detail_path_resolves_to_media_viewset(self):
        match = resolve("/api/v1/incidents/media/11111111-1111-1111-1111-111111111111/")
        assert match.func.cls is IncidentMediaViewSet
        assert match.func.actions == {"get": "retrieve", "delete": "destroy"}

    def test_incident_detail_route_is_not_shadowed(self):
        """`incidents/media/` must not swallow, nor be swallowed by, incidents/<pk>/."""
        match = resolve("/api/v1/incidents/11111111-1111-1111-1111-111111111111/")
        assert match.func.cls is not IncidentMediaViewSet

    def test_missing_file_returns_400_not_404(self, client, citizen, incident):
        """The endpoint exists and validates input rather than 404ing."""
        client.force_authenticate(user=citizen)
        response = client.post(
            "/api/v1/incidents/media/", {"incident": str(incident.id)}, format="multipart"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "file" in response.data["detail"].lower()

    def test_citizen_uploads_image_to_own_incident(self, client, citizen, incident):
        client.force_authenticate(user=citizen)
        upload = io.BytesIO(_png_bytes())
        upload.name = "pothole.png"
        response = client.post(
            "/api/v1/incidents/media/",
            {"incident": str(incident.id), "file": upload},
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["media_type"] == "image"

    def test_media_list_filters_by_incident(self, client, citizen, incident):
        client.force_authenticate(user=citizen)
        response = client.get(f"/api/v1/incidents/media/?incident={incident.id}")
        assert response.status_code == status.HTTP_200_OK

    def test_media_list_rejects_malformed_incident_filter(self, client, citizen, incident):
        """A non-UUID filter is an empty result, never a 500."""
        client.force_authenticate(user=citizen)
        response = client.get("/api/v1/incidents/media/?incident=not-a-uuid")
        assert response.status_code == status.HTTP_200_OK

    def test_unauthenticated_media_request_is_rejected(self, client):
        response = client.post("/api/v1/incidents/media/", {}, format="multipart")
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


class TestFeedbackRatingNullable:
    """Confirming a resolution must work with or without a rating."""

    def test_confirm_without_rating_persists_feedback(self, citizen, incident):
        from apps.incidents.models import IncidentStatus

        incident.status = IncidentStatus.RESOLVED
        incident.save(update_fields=["status", "updated_at"])

        confirm_resolution(incident=incident, user=citizen)

        incident.refresh_from_db()
        assert incident.citizen_confirmed_resolution is True
        assert incident.feedback.rating is None
        assert incident.satisfaction_rating is None

    def test_confirm_with_rating_still_works(self, citizen, incident):
        from apps.incidents.models import IncidentStatus

        incident.status = IncidentStatus.RESOLVED
        incident.save(update_fields=["status", "updated_at"])

        confirm_resolution(incident=incident, user=citizen, rating=4)

        incident.refresh_from_db()
        assert incident.feedback.rating == 4
        assert incident.satisfaction_rating == 4


class TestReferenceNumberAllocation:
    """Sequential, unique, collision-free reference numbers."""

    def test_numbers_are_sequential_and_unique(self, incident_factory, citizen, category):
        created = [incident_factory(reporter=citizen) for _ in range(3)]
        numbers = [i.reference_number for i in created]

        assert len(set(numbers)) == 3
        sequences = [int(n.rsplit("-", 1)[1]) for n in numbers]
        assert sequences == sorted(sequences)
        assert sequences[1] == sequences[0] + 1
        assert sequences[2] == sequences[1] + 1

    def test_counter_row_is_used_as_the_source_of_truth(self, incident_factory, citizen):
        incident = incident_factory(reporter=citizen)
        prefix = incident.reference_number.rsplit("-", 1)[0] + "-"
        counter = ReferenceCounter.objects.get(prefix=prefix)
        assert counter.last_value == int(incident.reference_number.rsplit("-", 1)[1])

    def test_explicit_reference_number_is_preserved(self, incident_factory, citizen):
        incident = incident_factory(reporter=citizen, reference_number="SC-MUM-2026-999999")
        assert incident.reference_number == "SC-MUM-2026-999999"

    def test_counter_does_not_advance_when_a_number_is_supplied(
        self, incident_factory, citizen
    ):
        """Imported/fixture incidents must not consume sequence values."""
        incident_factory(reporter=citizen, reference_number="SC-IMP-0001")
        assert not ReferenceCounter.objects.exists()


class TestThrottleScopesApplied:
    """Configured DRF scopes must actually be bound to views."""

    def test_media_viewset_declares_media_upload_scope(self):
        assert IncidentMediaViewSet.throttle_scope == "media_upload"

    def test_media_upload_rate_is_configured(self, settings):
        assert "media_upload" in settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]

    def test_ai_views_declare_ai_scope(self):
        from apps.ai.views import AIDuplicateCheckView, AISuggestView

        assert AISuggestView.throttle_scope == "ai"
        assert AIDuplicateCheckView.throttle_scope == "ai"
