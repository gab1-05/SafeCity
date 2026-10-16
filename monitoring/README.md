# SafeCity Monitoring

Continuous monitoring for the SafeCity platform, addressing the DBIT Notice 3
monitoring requirements (service availability, health, failures).

## Stack

| Component | Purpose | Config |
|-----------|---------|--------|
| Prometheus | Metrics scrape + alert evaluation | `prometheus.yml`, `alert-rules.yml` |
| Grafana | Dashboards | `grafana-dashboard.json` |
| Alertmanager | Alert routing (optional) | Configure per environment |

## Quick start

```bash
# From the repository root
docker compose -f docker-compose.monitoring.yml up -d

# Open Grafana:  http://localhost:3000  (admin / admin — change on first login)
# Open Prometheus: http://localhost:9090
```

## What is monitored

| Signal | Source (`/api/metrics/`) | Alert threshold | Severity |
|--------|---------------------------|-----------------|----------|
| Backend unreachable | scrape target `up{job="safecity"}` | `== 0` > 1m | critical |
| 5xx error rate | `safecity_http_requests_total` | > 1% of requests > 5m | warning |
| Celery queue backlog | `safecity_celery_queue_depth` (Redis LLEN) | > 100 for 15m | warning |
| SLA breaches accumulating | `safecity_sla_breached_open` gauge | net +10 in 24h | warning |
| Auth failure spike | `safecity_auth_failures_15m` gauge (audit log) | > 50 in 15m | warning |

`/api/readiness/` stays the orchestrator probe (kubelet/compose healthcheck), not a
Prometheus scrape target — it returns JSON, and Prometheus needs text exposition.

This mirrors the "What to alert on" table in `docs/DEVOPS.md` §6.

## Dashboard

`grafana-dashboard.json` can be imported into Grafana via
**Dashboards → New → Import → Upload JSON file**.

Panels:

1. **Service Health** — readiness up/down
2. **Request Rate** — requests/sec by status class
3. **5xx Error Rate** — error ratio timeseries
4. **Celery Queue Depth** — background job backlog
5. **SLA Breaches (24h)** — business metric
6. **Auth Failures (15m)** — security signal

## Production equivalents

- **AWS:** the Terraform `cloudwatch` module (`infrastructure/terraform/modules/cloudwatch`)
  provisions log groups, metric alarms, and an operations dashboard; alarms publish
  to an SNS topic (set `alert_email` in `terraform.tfvars` to subscribe).
- **Kubernetes:** install `kube-prometheus-stack` via Helm and apply the same
  alert rules from `alert-rules.yml`.

## Verification

```bash
# Prometheus target health
curl -s http://localhost:9090/api/v1/targets | python -m json.tool

# Firing alerts
curl -s http://localhost:9090/api/v1/alerts | python -m json.tool

# Grafana health
curl -s http://localhost:3000/api/health
```