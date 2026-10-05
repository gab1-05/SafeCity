"""Notification preference enforcement + throttle header tests."""

import pytest
from django.core import mail
from rest_framework import exceptions

from apps.core.exceptions import safecity_exception_handler
from apps.notifications.models import Notification, NotificationPreference
from apps.notifications.services import notify

pytestmark = pytest.mark.django_db


class TestPreferenceEnforcement:
    def test_disabled_event_creates_nothing(self, citizen):
        NotificationPreference.objects.create(
            user=citizen, events_enabled={"status_change": False}
        )
        assert notify(user=citizen, verb="status_change", title="x") is None
        assert Notification.objects.count() == 0

    def test_enabled_event_creates_notification(self, citizen):
        result = notify(user=citizen, verb="status_change", title="hello")
        assert result is not None
        assert Notification.objects.count() == 1

    def test_email_opt_out_skips_email_only(self, citizen):
        NotificationPreference.objects.create(user=citizen, in_app=True, email=False)
        result = notify(user=citizen, verb="status_change", title="hello", body="world")
        assert result is not None  # in-app still delivered
        assert mail.outbox == []


class TestThrottleHeaders:
    def test_throttled_sets_retry_after(self):
        exc = exceptions.Throttled(wait=60)
        response = safecity_exception_handler(exc, {})
        assert response.status_code == 429
        assert response["Retry-After"] == "60"
        assert response["X-RateLimit-Remaining"] == "0"
        assert response.data["code"] == "throttled"
