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

| Signal | Source | Alert threshold | Severity |
|--------|--------|-----------------|----------|
| Readiness failing | `/api/readiness/` | Any sustained 503 > 2m | critical |
| Backend unreachable | `/api/health/` scrape | `up == 0` > 1m | critical |
| 5xx error rate | Request metrics | > 1% of requests > 5m | warning |
| Celery queue backlog | Redis queue depth | > 100 for 15m | warning |
| SLA breaches | `safecity_sla_breached_total` | > 10 in 24h | warning |
| Auth failure spike | `safecity_auth_failures_total` | > 50 in 15m | warning |

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