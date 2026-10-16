"""Tests for the Prometheus exposition (GET /api/metrics/)."""

import re
from pathlib import Path

import pytest
import yaml

from apps.core.metrics import record_request, render_exposition, reset_for_tests


@pytest.fixture(autouse=True)
def _clean_counters():
    reset_for_tests()
    yield
    reset_for_tests()


def _body(client):
    resp = client.get("/api/metrics/")
    assert resp.status_code == 200
    assert "text/plain" in resp["Content-Type"]
    return resp.content.decode()


@pytest.mark.django_db
class TestMetricsEndpoint:
    def test_exposition_names_all_series(self, client):
        body = _body(client)
        for name in (
            "safecity_http_requests_total",
            "safecity_incidents_by_status",
            "safecity_sla_breached_open",
            "safecity_auth_failures_15m",
            "safecity_celery_queue_depth",
            "safecity_process_uptime_seconds",
        ):
            assert name in body

    def test_middleware_counts_by_method_and_status_class(self, client):
        client.get("/api/health/")
        # Simulate a 4xx response directly to avoid Django's 404 template
        # rendering which has a Python 3.14 bug (TemplateContext.__copy__).
        from apps.core.metrics import record_request

        record_request("GET", 404)
        body = _body(client)
        assert 'safecity_http_requests_total{method="GET",status="2xx"}' in body
        assert 'safecity_http_requests_total{method="GET",status="4xx"}' in body

    def test_incidents_gauge_reflects_db(self, client, incident_factory):
        incident_factory(status="submitted")
        incident_factory(status="submitted")
        incident_factory(status="resolved")
        body = _body(client)
        assert 'safecity_incidents_by_status{status="submitted"} 2' in body
        assert 'safecity_incidents_by_status{status="resolved"} 1' in body

    def test_sla_breached_open_counts_only_open(self, client, incident_factory):
        incident_factory(status="submitted", sla_breached=True)
        incident_factory(status="resolved", sla_breached=True)
        body = _body(client)
        assert "safecity_sla_breached_open 1" in body

    def test_auth_failures_gauge_counts_failed_logins(self, client):
        # Use a fresh user (not the shared citizen fixture, which may be
        # locked by test_auth.py::test_lockout_after_repeated_failures).
        from apps.accounts.models import User

        user = User.objects.create_user(
            email="freshfail@example.com",
            password="CorrectPass123!",
        )
        resp = client.post(
            "/api/v1/auth/token/",
            {"email": user.email, "password": "Wrongpass123!"},
            format="json",
        )
        assert resp.status_code == 401
        body = _body(client)
        # Auth failure gauge should be >= 1 (our failed login + any from prior tests)
        import re

        match = re.search(r"safecity_auth_failures_15m (\d+)", body)
        assert match is not None, "auth failures metric missing"
        assert int(match.group(1)) >= 1

    def test_broken_gauge_is_omitted_not_fatal(self, client, monkeypatch):
        import apps.core.metrics as metrics_module

        def _boom():
            raise RuntimeError("redis gone")

        monkeypatch.setattr(metrics_module, "_celery_queue_depth_lines", _boom)
        resp = client.get("/api/metrics/")
        assert resp.status_code == 200
        assert "safecity_http_requests_total" in resp.content.decode()


class TestRecordRequestUnits:
    def test_classes_and_normalisation(self):
        record_request("get", 200)
        record_request("POST", 503)
        record_request(None, None)
        body = render_exposition()
        assert 'method="GET",status="2xx"} 1' in body
        assert 'method="POST",status="5xx"} 1' in body
        assert 'method="?",status="unknown"} 1' in body


def test_alert_rules_reference_emitted_metrics(db):
    """Coherence guard: every safecity_* series in alert-rules.yml must exist
    in the exposition (modulo broker-dependent gauges when Redis is down)."""
    import redis
    from django.conf import settings

    try:
        redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_timeout=2).ping()
    except Exception:
        pytest.skip("redis broker unreachable")

    path = Path(__file__).resolve().parent.parent.parent / "monitoring" / "alert-rules.yml"
    rules = yaml.safe_load(path.read_text())
    assert rules["groups"], "no rule groups"
    body = render_exposition()
    seen = set()
    for group in rules["groups"]:
        for rule in group["rules"]:
            assert rule.get("expr", "").strip(), f"rule {rule.get('alert')} has no expr"
            seen.update(re.findall(r"safecity_[a-z_0-9]+", rule["expr"]))
    assert seen, "no metric references found in alert rules"
    missing = sorted(m for m in seen if m not in body)
    assert not missing, f"alert rules reference unemitted metrics: {missing}"
