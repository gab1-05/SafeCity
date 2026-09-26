"""
Public-map visibility tests: the map shows every active status (including
brand-new `submitted` reports) plus `resolved` incidents for 5 days, after
which they disappear. Anonymous reports are never public. Logged-in users
opt into the same view with ?scope=public (role scoping otherwise applies).
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status

pytestmark = pytest.mark.django_db

ACTIVE = ["submitted", "under_review", "verified", "assigned", "in_progress"]


def _ids(response):
    return [r["id"] for r in response.data["results"]]


class TestPublicMapVisibility:
    def test_anonymous_sees_all_active_statuses(self, client, incident_factory):
        made = {s: incident_factory(status=s) for s in ACTIVE}
        response = client.get("/api/v1/incidents/")
        assert response.status_code == status.HTTP_200_OK
        ids = _ids(response)
        for incident in made.values():
            assert str(incident.id) in ids

    def test_anonymous_does_not_see_closed_rejected(self, client, incident_factory):
        closed = incident_factory(status="closed")
        rejected = incident_factory(status="rejected")
        response = client.get("/api/v1/incidents/")
        ids = _ids(response)
        assert str(closed.id) not in ids
        assert str(rejected.id) not in ids

    def test_recently_resolved_shown_old_resolved_hidden(self, client, incident_factory):
        recent = incident_factory(status="resolved", resolved_at=timezone.now())
        old = incident_factory(
            status="resolved", resolved_at=timezone.now() - timedelta(days=10)
        )
        response = client.get("/api/v1/incidents/")
        ids = _ids(response)
        assert str(recent.id) in ids
        assert str(old.id) not in ids

    def test_anonymous_reports_never_public(self, client, incident_factory):
        anon = incident_factory(status="verified", is_anonymous=True)
        response = client.get("/api/v1/incidents/")
        assert str(anon.id) not in _ids(response)

    def test_citizen_gets_public_view_with_scope_param(
        self, client, citizen, incident_factory
    ):
        mine = incident_factory(reporter=citizen, status="submitted")
        other = incident_factory(status="verified")  # someone else's
        client.force_authenticate(user=citizen)
        plain = client.get("/api/v1/incidents/")
        assert _ids(plain) == [str(mine.id)]  # default scoping unchanged
        scoped = client.get("/api/v1/incidents/?scope=public")
        ids = _ids(scoped)
        assert str(mine.id) in ids
        assert str(other.id) in ids
