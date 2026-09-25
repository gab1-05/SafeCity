# SafeCity — DevOps Guide

Covers containerisation, the task runner, the test strategy, observability, backup and
recovery, and the intended CI/CD pipeline.

> **Scope note:** the infrastructure code in this repository is delivered as code and is
> reviewed, but it is **never applied automatically**. Nothing in this document
> provisions cloud resources. See [COST-CONTROL.md](COST-CONTROL.md) before running any
> `terraform apply`.

---

## 1. Local development

### Docker Compose (recommended)

`docker-compose.yml` brings up the full stack with source mounted for hot reload.

| Service | Image / build | Host port | Purpose |
|---------|---------------|-----------|---------|
| `db` | `postgres:16-alpine` | 5432 | Primary datastore |
| `redis` | `redis:7-alpine` | 6379 | Cache, Celery broker, Channels layer |
| `minio` | `minio/minio` | 9000 (API), 9001 (console) | Optional S3-compatible storage |
| `backend` | `./backend` | `${BACKEND_PORT:-9080}` → 8000 | Django dev server |
| `celery` | `./backend` | — | Async worker |
| `celery-beat` | `./backend` | — | Scheduled sweeps (database scheduler) |
| `frontend` | `node:20-alpine` | 5173 | Vite dev server |

`db` and `redis` declare healthchecks, and `backend` uses
`depends_on: condition: service_healthy`, so the API does not start against a database
that is still initialising. This removes the most common local-startup race.

MinIO is optional: the backend defaults to `MEDIA_BACKEND=local` and writes to disk.
Use MinIO only when exercising the S3 code path.

```bash
cp .env.example .env
make docker-up        # build + start
make migrate          # apply migrations (explicit, never automatic)
make seed             # demo data
make docker-logs      # tail backend logs
make docker-down      # stop
```

> **Port consistency.** `docker-compose.yml` and `.env.example` must agree with the URLs
> quoted in `README.md` (backend on 8080). If the API is unreachable at the documented
> port, check `BACKEND_PORT` — this value has historically drifted between the compose
> files and the docs. See [Known limitations](PROJECT-MANAGEMENT.md#2-known-limitations).

### Native (no Docker)

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements/dev.txt
cp ../.env.example ../.env        # set DB_HOST=localhost
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver

# Frontend
cd frontend
npm ci
npm run dev
```

Native development still needs PostgreSQL and Redis running locally; the test settings
connect to `DB_HOST:DB_PORT` (`localhost:5432` by default).

---

## 2. Production-like stack

`docker-compose.prod.yml` builds real images and mounts no source. Use it to validate
image builds and startup before any cluster deployment.

| Difference from dev | Why |
|---------------------|-----|
| `DJANGO_SETTINGS_MODULE=config.settings.prod` | Debug off, hardened headers, mandatory `ALLOWED_HOSTS` |
| `SECRET_KEY` and `POSTGRES_PASSWORD` are required (`:?` syntax) | Compose refuses to start rather than silently using a dev default |
| Frontend served by nginx on `${FRONTEND_PORT:-8088}` | Static assets + SPA routing, not Vite |
| Backend served by Daphne on 8000 | HTTP **and** WebSocket in one process (Channels) |
| Database and Redis publish no host ports | Not reachable from outside the compose network |
| `restart: unless-stopped` | Survives host reboot |

### Image design

**Backend** (`backend/Dockerfile`) — multi-stage, non-root:

- `python:3.12-slim` base, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`
- Production requirements only (`requirements/prod.txt`)
- Static files collected at build time, served by WhiteNoise
- Dedicated system user/group `safecity`; the container runs as `USER safecity`
- `HEALTHCHECK` against `/api/health/`
- Serves via `daphne config.asgi:application`

**Frontend** (`frontend/Dockerfile`) — build then runtime:

- `node:20-alpine` build stage, `npm ci` for reproducible installs
- `nginx:1.27-alpine` runtime serving `/usr/share/nginx/html`
- nginx sets `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and
  `Referrer-Policy: same-origin`
- `HEALTHCHECK` on `GET /`

> The frontend image has no `USER` directive, so it runs as root. See
> [Security deviations](SECURITY-AND-PRIVACY.md#7-deviations-from-the-architecture-proposal) D-2.

### Migrations are explicit

No container runs `migrate` on start. Schema changes are applied deliberately:

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate
```

Automatic migration on boot makes a failed rollout ambiguous — you cannot tell whether the
old or new schema is live. In Kubernetes the same principle becomes a separate
`migration-job.yaml`.

---

## 3. Task runner

`Makefile` is the single entry point for routine operations.

| Target | Does |
|--------|------|
| `make help` | List all targets (self-documenting from `##` comments) |
| `make install` | Create the backend venv, install dev requirements, `npm ci` |
| `make dev` | Print the two commands to run backend + frontend natively |
| `make test` | Backend pytest suite |
| `make test-frontend` | Frontend Vitest suite |
| `make test-e2e` | Playwright suite against the compose stack |
| `make lint` | Ruff (backend) + ESLint (frontend) |
| `make format` | Ruff format + Prettier |
| `make migrate` | Apply migrations in the running compose backend |
| `make seed` | Load demo data |
| `make superuser` | Create a Django superuser |
| `make coverage` | pytest with `--cov=apps --cov=config --cov-report=term-missing` |
| `make openapi` | Regenerate `docs/api-schema.yaml` |
| `make docker-up` / `docker-down` / `docker-build` / `docker-logs` | Compose lifecycle |
| `make k8s-deploy` | `helm upgrade --install` with `values-dev.yaml` |
| `make terraform-plan` | `init` + `plan` for the dev environment |
| `make terraform-apply` | **Refuses to run.** Prints instructions and exits 1 |
| `make terraform-destroy` | **Refuses to run.** Prints instructions and exits 1 |

The two destructive Terraform targets deliberately fail with an explanatory message. A
`make` target that can destroy infrastructure should never be one keystroke away from a
typo.

Note `make k8s-deploy` references `infrastructure/helm/safecity/values-dev.yaml`, which
does not exist yet — see [Known limitations](PROJECT-MANAGEMENT.md#2-known-limitations).

---

## 4. Testing strategy

### Layers

| Layer | Tool | Location | Scope |
|-------|------|----------|-------|
| Backend unit/integration | pytest + pytest-django | `backend/tests/` | Auth, RBAC, incident CRUD, workflow, media validation, SLA, audit |
| Frontend unit/component | Vitest + React Testing Library | `frontend/tests/` | Forms, route guards, dashboard rendering, loading/error states |
| End-to-end | Playwright | `frontend/e2e/` | Full citizen → authority → resolution → feedback loop |

### Backend suite

```
backend/tests/
  conftest.py                  # fixtures: users per role, incident factory
  test_auth.py                 # registration, login, token rotation, lockout
  test_rbac.py                 # parametrized role × endpoint matrix
  test_incidents.py            # CRUD, validation, workflow transitions
  test_blocker_regressions.py  # regressions for previously-shipped blockers
```

Coverage is measured over `apps` and `config`:

```bash
make coverage
```

Gate: **backend ≥ 80%**.

Test settings (`config/settings/test.py`) are designed for determinism and speed:

| Setting | Value | Reason |
|---------|-------|--------|
| Database | PostgreSQL, `safecity_test` | Same engine as production; JSONB and `tsvector` behaviour must match |
| `--reuse-db` | on (`pytest.ini`) | Avoids re-creating the schema on each run |
| Password hasher | MD5 | Speed only — never used outside tests |
| Throttles | Disabled, rates still declared | Scoped throttle classes resolve rates at instantiation time |
| Celery | `TASK_ALWAYS_EAGER` | Tasks run inline so assertions are deterministic |
| Cache | LocMem | No Redis dependency for unit tests |
| Channel layer | InMemory | No Redis dependency |
| Email | LocMem | Assert on outbox, send nothing |

> **The backend suite needs PostgreSQL.** It does not fall back to SQLite by design —
> testing against a different engine than production would miss exactly the features this
> project depends on (full-text search, JSONB, partial unique constraints). If `pytest`
> appears to hang, it is almost always waiting on an unreachable database. Start the
> stack first (`make docker-up`) or point `DB_HOST`/`DB_PORT` at a reachable instance.

### Frontend suite

```bash
make test-frontend    # vitest --run
npm run typecheck     # tsc -b --noEmit
npm run lint          # eslint, max-warnings 0
```

Gate: **frontend ≥ 70% statements on `src/`**.

### End-to-end

Playwright runs against a seeded compose stack, so the E2E job must migrate and seed
before executing:

```bash
make docker-up && make migrate && make seed
make test-e2e
```

### What is deliberately not unit-tested

External side effects are not tested against real providers. Email, SMS, AI, and malware
scanning are exercised through their adapters with mocks, which keeps the suite hermetic
and free of credentials.

---

## 5. Continuous integration

`CONTRIBUTING.md` states the gate that must be green before merge:

> backend tests (coverage ≥ 80%), frontend tests + typecheck, lint, docker build,
> trivy scan, terraform fmt/validate (if infra touched).

The workflows that implement this are **not yet authored** — `.github/workflows/` exists
but is empty. This is the single largest delivery gap; see
[Known limitations](PROJECT-MANAGEMENT.md#2-known-limitations).

### Intended pipeline

| Workflow | Trigger | Jobs |
|----------|---------|------|
| `backend-ci.yml` | PR → `develop`/`main` | Ruff, pytest with PostgreSQL + Redis service containers, coverage ≥ 80% gate |
| `frontend-ci.yml` | PR | ESLint, `tsc`, Vitest, `vite build` |
| `docker-ci.yml` | PR / `main` | Build images, Trivy scan failing on HIGH/CRITICAL, push to ECR on `main` via OIDC (no long-lived keys) |
| `terraform-ci.yml` | PR touching `infrastructure/` | `fmt -check`, `validate`, `plan` for dev as an artifact |
| `k8s-validate.yml` | PR | `helm lint`, `kubeconform` |
| `e2e.yml` | nightly + PR label | Compose up, migrate, seed, Playwright |
| `deploy-staging.yml` | merge to `develop` | Build → push → `helm upgrade` staging |
| `deploy-production.yml` | tag `v*` | Protected environment with **manual approval**, then `helm upgrade` prod |

### Branching model

```
main        protected; releases tagged v*
develop     integration branch; protected
feature/*   feature work, branched from develop
fix/*       bug fixes
release/*   stabilization before main
hotfix/*    urgent fixes off main
```

All PRs target `develop`; changes reach `main` only through `release/*`. Conventional
Commits prefixes are required so history can be scanned and changelogs generated.

---

## 6. Observability

### Health probes

| Endpoint | Kind | Behaviour |
|----------|------|-----------|
| `/api/health/` | Liveness | Always 200 while the process is up. Checks no dependency, so a database outage does not cause the orchestrator to kill healthy pods. |
| `/api/readiness/` | Readiness | Checks database, cache, and storage. Returns **503** with a per-dependency map when degraded, so the pod is removed from the load balancer but not restarted. |

This split is the point: restarting a pod because the database is briefly unavailable
turns a transient dependency problem into a crash loop.

### Structured logging

```python
LOGGING = {
    "formatters": {"json": ...},
    "filters": {"request_id": {"()": "apps.core.logging.RequestIDFilter"}},
    ...
}
```

- JSON formatter for machine ingestion
- A `RequestIDFilter` injects the current request id into every record
- Middleware (`apps/core/middleware.py`) reads an inbound `X-Request-ID` or generates a
  UUID4 hex, stores it in a thread-local, and echoes it on the response

Because the same id lands in `AuditLog.request_id`, any logged action can be traced from
a user report → HTTP log line → audit row.

### What to alert on

| Signal | Source | Threshold |
|--------|--------|-----------|
| Readiness failing | `/api/readiness/` | Any sustained 503 |
| SLA breaches accumulating | `sla_breached` count | Rising trend over 24 h |
| Escalations unattended | Incident `escalated` with no recent activity | Age > SLA |
| Celery queue backlog | Redis queue depth | Growing for > 15 min |
| 5xx rate | Error logs | > 1% of requests |
| Auth failures | `auth` throttle + lockout counters | Spike above baseline |

Readiness alerts should be page-worthy; liveness alerts generally should not.

---

## 7. Backup and disaster recovery

### What to back up

| Asset | Method | Frequency (proposed) | Retention |
|-------|--------|----------------------|-----------|
| PostgreSQL | `pg_dump` / RDS automated snapshots | Daily full + point-in-time | 30 days |
| Media | S3 versioning + lifecycle rules | Continuous | 90 days, then IA |
| Configuration | Git (`config/settings/*`, Helm values, Terraform) | On change | History |
| Secrets | AWS Secrets Manager (not in backups) | On rotation | — |

### PostgreSQL backup and restore

```bash
# Backup
docker compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" \
  | gzip > safecity-$(date +%F).sql.gz

# Restore into a fresh database
gunzip -c safecity-2026-09-19.sql.gz \
  | docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

Always restore into a **separate database first** and verify row counts and a few
incidents before touching the live database.

### Recovery objectives (proposed)

| Metric | Target |
|--------|--------|
| RPO (max data loss) | 15 minutes |
| RTO (time to restore service) | 4 hours |

These are engineering proposals for an SDP-scale deployment, not committed SLAs.

### Recovery procedure

1. Provision the database (or restore the snapshot).
2. Restore the most recent dump; apply any WAL/PITR segments if available.
3. Restore media from the bucket or volume.
4. Deploy the application at the matching image tag.
5. Run `python manage.py migrate` to reconcile schema.
6. Verify: `/api/health/`, then `/api/readiness/` (must report `ok` on all checks).
7. Confirm data: incident count, latest reference number, and a sample audit row.
8. Confirm Celery worker and beat are consuming (run a manual sweep).

### Disaster recovery drills

Because an untested backup is not a backup, the recovery procedure should be rehearsed
against a scratch environment before any real deployment. A drill that has never been run
is an assumption, not a capability.

---

## 8. Scheduled background work

Celery beat (`config/celery.py`) registers:

| Task | Schedule | Purpose |
|------|----------|---------|
| `apps.incidents.tasks.sla_breach_sweep` | every 5 minutes | Flag incidents past `sla_deadline` as breached |
| `apps.incidents.tasks.escalation_sweep` | every 15 minutes | Raise escalations for stale/overdue work |
| `apps.analytics.tasks.aggregate_daily` | daily at 00:30 | Build `DailyIncidentAggregate` rows |

Ad-hoc tasks: `process_media` (EXIF strip + thumbnails, dispatched on upload) and
`update_search_vectors` (rebuild full-text search vectors).

The beat scheduler is `django_celery_beat.schedulers:DatabaseScheduler`, so schedules are
database-backed and can be changed without a redeploy.

> Run **exactly one** beat instance. Multiple beat processes duplicate every scheduled
> job, which would double-count escalations and SLA flags.

---

## 9. Operational runbook

| Situation | Action |
|-----------|--------|
| Stack won't start | `make docker-logs`; confirm `db` and `redis` are healthy — `backend` waits on both |
| API unreachable | Check `BACKEND_PORT` in `.env` against the documented port |
| `pytest` hangs | A database is unreachable; start the stack or fix `DB_HOST`/`DB_PORT` |
| Readiness degraded | Read the `checks` map in the 503 body — it names the failing dependency |
| Migrations needed | `make migrate` (never rely on container startup) |
| Reset local data | `make docker-down` then remove the `pgdata` volume and re-run migrate + seed |
| Celery not processing | Confirm Redis is reachable and one worker plus one beat are running |
| Realtime notifications silent | Expected today: no WebSocket client is wired in the SPA. Polling endpoints work |
| Regenerate API docs | `make openapi` |
| Rotate secrets | Update `.env` (or Secrets Manager), restart `backend`, `celery`, `celery-beat` |
