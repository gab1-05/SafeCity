"""
Audit retention: purge audit rows older than AUDIT_RETENTION_DAYS.

Append-only within the window; the sweep keeps the table bounded.
Set AUDIT_RETENTION_DAYS=0 to disable (not recommended outside dev).
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("safecity")


@shared_task(name="apps.audit.tasks.purge_old_logs")
def purge_old_logs() -> int:
    from apps.audit.models import AuditLog

    days = int(settings.SAFECITY.get("AUDIT_RETENTION_DAYS", 365))
    if days <= 0:
        return 0
    cutoff = timezone.now() - timedelta(days=days)
    deleted, _ = AuditLog.objects.filter(created_at__lt=cutoff).delete()
    if deleted:
        logger.info("Audit retention sweep purged %s rows older than %s days", deleted, days)
    return deleted
