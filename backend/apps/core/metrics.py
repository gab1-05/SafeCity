"""
Prometheus exposition for SafeCity (`GET /api/metrics/`).

Dependency-free: request counters live in-process, business gauges are read
live from Postgres/Redis on every scrape, and the exposition text is rendered
by hand. No client library, no new settings.

Scope and limits (read before alerting on these):
* Counters reset when the process restarts. Prometheus `rate()` handles resets,
  but absolute totals are per-process, not cluster-wide.
* Under a multi-worker server each worker keeps its own counters; the gauges
  (DB/Redis reads) are exact regardless of workers.
* A gauge that cannot be collected (e.g. Redis unreachable) is omitted from the
  output — never fabricated as zero.
"""

import logging
import re
import threading
import time
from contextlib import suppress

logger = logging.getLogger(__name__)

_STARTED_AT = time.time()
_lock = threading.Lock()
_requests_total: dict[tuple[str, str], int] = {}


def reset_for_tests() -> None:
    """Clear in-process counters (test isolation only)."""
    with _lock:
        _requests_total.clear()


def record_request(method: str | None, status_code: int | None) -> None:
    """Count one served response by method and 1xx..5xx class."""
    if isinstance(status_code, int):
        status_class = f"{status_code // 100}xx"
    else:
        status_class = "unknown"
    key = (str(method or "?").upper(), status_class)
    with _lock:
        _requests_total[key] = _requests_total.get(key, 0) + 1


_LABEL_UNSAFE = re.compile(r"[^a-zA-Z0-9_]")


def _label(value: str | None) -> str:
    return _LABEL_UNSAFE.sub("_", value or "unknown")


def _counter_lines() -> list[str]:
    with _lock:
        items = sorted(_requests_total.items())
    lines = [
        "# HELP safecity_http_requests_total HTTP responses served since process start, by method and status class.",
        "# TYPE safecity_http_requests_total counter",
    ]
    lines.extend(
        f'safecity_http_requests_total{{method="{method}",status="{status}"}} {count}'
        for (method, status), count in items
    )
    return lines


def _uptime_lines() -> list[str]:
    return [
        "# HELP safecity_process_uptime_seconds Seconds since this backend process started.",
        "# TYPE safecity_process_uptime_seconds gauge",
        f"safecity_process_uptime_seconds {time.time() - _STARTED_AT:.0f}",
    ]


def _incidents_by_status_lines() -> list[str]:
    from django.db.models import Count

    from apps.incidents.models import Incident

    rows = Incident.objects.values("status").annotate(n=Count("id")).order_by("status")
    lines = [
        "# HELP safecity_incidents_by_status Current incidents by workflow status.",
        "# TYPE safecity_incidents_by_status gauge",
    ]
    lines.extend(
        f'safecity_incidents_by_status{{status="{_label(row["status"])}"}} {row["n"]}'
        for row in rows
    )
    return lines


def _sla_breached_open_lines() -> list[str]:
    from apps.incidents.models import Incident, IncidentStatus

    count = (
        Incident.objects.filter(sla_breached=True)
        .exclude(status__in=(IncidentStatus.RESOLVED, IncidentStatus.CLOSED))
        .count()
    )
    return [
        "# HELP safecity_sla_breached_open Open incidents past their SLA deadline.",
        "# TYPE safecity_sla_breached_open gauge",
        f"safecity_sla_breached_open {count}",
    ]


def _auth_failures_15m_lines() -> list[str]:
    from datetime import timedelta

    from django.utils import timezone

    from apps.audit.models import AuditLog

    since = timezone.now() - timedelta(minutes=15)
    count = AuditLog.objects.filter(
        action__in=("auth.login_failed", "auth.2fa_login_failed"),
        created_at__gte=since,
    ).count()
    return [
        "# HELP safecity_auth_failures_15m Failed login attempts in the last 15 minutes (audit log).",
        "# TYPE safecity_auth_failures_15m gauge",
        f"safecity_auth_failures_15m {count}",
    ]


def _celery_queue_depth_lines() -> list[str]:
    import redis
    from django.conf import settings

    client = None
    try:
        client = redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_timeout=2)
        depth = client.llen("celery")
    except Exception:
        logger.warning("metrics: celery broker unreachable, omitting queue depth", exc_info=True)
        return []
    finally:
        if client is not None:
            with suppress(Exception):
                client.close()
    return [
        "# HELP safecity_celery_queue_depth Length of the default celery queue in Redis.",
        "# TYPE safecity_celery_queue_depth gauge",
        f"safecity_celery_queue_depth {depth}",
    ]


_GAUGE_COLLECTORS = (
    _incidents_by_status_lines,
    _sla_breached_open_lines,
    _auth_failures_15m_lines,
    _celery_queue_depth_lines,
)


def render_exposition() -> str:
    """Render the full exposition text. A failing gauge is omitted, never fatal."""
    sections = [_counter_lines(), _uptime_lines()]
    for collector in _GAUGE_COLLECTORS:
        try:
            sections.append(collector())
        except Exception:
            logger.warning(
                "metrics: %s failed, omitting from exposition",
                collector.__name__,
                exc_info=True,
            )
    return "\n".join(line for section in sections for line in section) + "\n"
