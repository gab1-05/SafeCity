# Step 5: Monitoring Evidence

Captured: 2026-10-16
Purpose: DBIT Notice 3 continuous-monitoring proof (F3–F5) — live Prometheus +
Grafana stack against the running compose backend, with alert rules and dashboard
aligned to the real `/api/metrics/` exposition.

## Stack (all verified live)

| Component | URL | Status |
|-----------|-----|--------|
| Prometheus | http://localhost:9090 | ✅ up, both scrape targets healthy |
| Grafana | http://localhost:3000 (admin/admin) | ✅ database ok, v13.2.4 |

## Prometheus targets (live API output)

```json
{
  "status": "success",
  "data": {
    "activeTargets": [
      {
        "job": "prometheus",
        "instance": "localhost:9090",
        "health": "up",
        "lastScrape": "2026-10-16T15:18:30.222591962Z"
      },
      {
        "job": "safecity",
        "instance": "backend:8000",
        "metrics_path": "/api/metrics/",
        "health": "up",
        "lastScrape": "2026-10-16T15:18:35.777940932Z"
      }
    ],
    "droppedTargets": []
  }
}
```

Both targets `up` — including the backend scrape of `/api/metrics/` on
`backend:8000` inside compose networking.

## Grafana health

```json
{ "database": "ok", "version": "13.2.4" }
```

## Alert rules (`monitoring/alert-rules.yml`) — aligned to emitted metrics

| Alert | Series (`/api/metrics/`) | Threshold | Severity |
|-------|--------------------------|-----------|----------|
| SafeCityBackendDown | `up{job="safecity"}` | `== 0` for 1m | critical |
| SafeCityHighErrorRate | `safecity_http_requests_total` | > 1% 5xx over 5m | warning |
| SafeCityCeleryBacklog | `safecity_celery_queue_depth` | > 100 for 15m | warning |
| SafeCitySlaBreachesAccumulating | `safecity_sla_breached_open` | net +10 over 24h | warning |
| SafeCityAuthFailureSpike | `safecity_auth_failures_15m` | > 50 in 15m | warning |

Coherence guard: `backend/tests/test_metrics.py` fails the CI build if any
alert-rule series is not emitted by `/api/metrics/` (rule: rules and code cannot
drift apart silently). Passes.

## Live exposition snapshot (`curl http://localhost:18081/api/metrics/`)

```
# HELP safecity_http_requests_total ...
safecity_http_requests_total{method="GET",status="2xx"} 143
...
# HELP safecity_incidents_by_status ...
safecity_incidents_by_status{status="submitted"} 83
safecity_incidents_by_status{status="resolved"} 3
...
safecity_sla_breached_open 116
safecity_auth_failures_15m 0
safecity_celery_queue_depth 0
safecity_process_uptime_seconds 4282
```

All gauges read live from Postgres/Redis; the celery broker gauge omits itself
gracefully if Redis is unreachable (never fabricates zero).

## Grafana dashboard (`monitoring/grafana-dashboard.json`)

6 panels, queries retargeted to the real series:
1. Service Health — `up{job="safecity"}` (stat, UP/DOWN mapping)
2. Request Rate — `sum(rate(safecity_http_requests_total[5m])) by (status)`
3. 5xx Error Rate — `rate(...{status=~"5.."}) / rate(...)`
4. Celery Queue Depth — `safecity_celery_queue_depth`
5. Open SLA Breaches — `safecity_sla_breached_open`
6. Auth Failures (15m) — `safecity_auth_failures_15m`

Import path: Grafana → Dashboards → New → Import → upload JSON file.

## Test verification

`backend/tests/test_metrics.py` (8 tests): exposition series names, middleware
counting by method/status class, gauge reflects DB state, SLA gauge excludes
closed incidents, auth-failures gauge counts audit-log entries, broken gauge
omitted without failing the endpoint, unit-level `record_request` classes,
plus the alert-rules coherence guard. 8/8 pass. Full suite: 227 passed, backend
coverage 82% (gate 80% enforced in CI).

## Gate status

**PASS** — monitoring stack running, both targets scraping `/api/metrics/` as
`up`, Grafana healthy, alert rules + dashboard aligned to live metrics, tests
green, coverage gate enforced.
