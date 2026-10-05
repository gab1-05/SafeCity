"""Audit retention sweep tests."""

from datetime import timedelta

import pytest
from django.conf import settings
from django.test import override_settings
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.audit.tasks import purge_old_logs

pytestmark = pytest.mark.django_db


def _log(days_old=0, action="test.action"):
    log = AuditLog.objects.create(action=action, object_type="test", object_id="x")
    if days_old:
        AuditLog.objects.filter(pk=log.pk).update(
            created_at=timezone.now() - timedelta(days=days_old)
        )
    return log


class TestPurgeOldLogs:
    def test_purges_only_expired(self):
        _log(days_old=400)
        _log(days_old=10)
        assert purge_old_logs() == 1
        assert AuditLog.objects.count() == 1

    def test_disabled_when_zero(self):
        _log(days_old=400)
        with override_settings(
            SAFECITY={**settings.SAFECITY, "AUDIT_RETENTION_DAYS": 0}
        ):
            assert purge_old_logs() == 0
        assert AuditLog.objects.count() == 1
