"""
Celery application for SafeCity background jobs and scheduled sweeps.
"""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("safecity")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "sla-breach-sweep": {
        "task": "apps.incidents.tasks.sla_breach_sweep",
        "schedule": crontab(minute="*/5"),
    },
    "escalation-sweep": {
        "task": "apps.incidents.tasks.escalation_sweep",
        "schedule": crontab(minute="*/15"),
    },
    "daily-analytics-aggregate": {
        "task": "apps.analytics.tasks.aggregate_daily",
        "schedule": crontab(hour=0, minute=30),
    },
}
