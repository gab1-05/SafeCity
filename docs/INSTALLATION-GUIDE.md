# SafeCity — Installation Guide

Covers three ways to get SafeCity running: Docker Compose (recommended), native
(no Docker), and Kubernetes. Also: running the tests, demo credentials, and
troubleshooting.

---

## 1. Prerequisites

| Method | Requirements |
|--------|--------------|
| **Docker (recommended)** | Docker Desktop with Compose v2, and `make`. Nothing else — no Python, no Node, no database. |
| Native | Python 3.12+, Node.js 20+, PostgreSQL 16, Redis 7 |
| Kubernetes | Helm 3.x, kubectl, a cluster, plus reachable PostgreSQL and Redis endpoints |
| Tests (backend) | PostgreSQL reachable at `DB_HOST:DB_PORT` — see [§5](#5-running-tests) |

Ports that must be free (defaults from `.env.example`; overridable via
`BACKEND_PORT` / `FRONTEND_PORT`): **5174** (frontend), **18081** (backend),
5432 (Postgres), 6379 (Redis), 9000/9001 (MinIO, optional).

---

## 2. Docker Compose — recommended

```bash
git clone <repository-url> safecity
cd safecity
cp .env.example .env      # the defaults work for local development
make docker-up            # builds and starts db, redis, minio, backend, celery, celery-beat, frontend
make migrate              # apply the database schema
make seed                 # load demo data (users, departments, categories, incidents)
```

`make docker-up` waits for the database and Redis healthchecks before starting the
backend, so there is no startup race to work around.

### What you get

| Service | URL | Notes |
|---------|-----|-------|
| Frontend | http://localhost:5174 | Vite dev server with hot reload |
| Backend API | http://localhost:18081/api/v1/ | Django dev server |
| Swagger UI | http://localhost:18081/api/schema/swagger/ | Interactive API docs |
| ReDoc | http://localhost:18081/api/schema/redoc/ | Alternative API docs |
| Django admin | http://localhost:18081/admin/ | Session-authenticated |
| Health | http://localhost:18081/api/health/ | Liveness |
| Readiness | http://localhost:18081/api/readiness/ | Checks DB, cache, storage |
| MinIO console | http://localhost:9001 | `minioadmin` / `minioadmin` (optional; unused by default) |

MinIO is started but **not used** by default: the backend writes media to local disk
(`MEDIA_BACKEND=local`). It is there if you want to exercise the S3 code path.

### Verify the install

```bash
curl -s http://localhost:18081/api/health/
# {"status": "ok", "service": "safecity-backend"}

curl -s http://localhost:18081/api/readiness/
# {"status": "ok", "checks": {"database": "ok", "cache": "ok", "storage": "local"}}
```

If readiness returns **503**, read the `checks` map — it names the failing dependency.

Then open http://localhost:5174 and log in with a demo account.

### Daily commands

```bash
make docker-logs      # tail backend logs
make migrate          # apply new migrations
make seed             # re-seed (idempotent — safe to re-run)
make docker-down      # stop everything, keep data
make docker-down -v   # stop and delete volumes (destroys all data)
```

---

## 3. Demo credentials

> ⚠️ **Local development only.** These are deliberately fake, documented in the README,
> and must never exist in any deployed environment. `make seed` creates them.

| Role | Email | Password |
|------|-------|----------|
| Superuser / City Admin | `admin@safecity.local` | `Admin@12345!` |
| Department staff (Water) | `staff.water@safecity.local` | `Staff@12345!` |
| Department staff (Roads) | `staff.roads@safecity.local` | `Staff@12345!` |
| Department staff (Fire) | `staff.fire@safecity.local` | `Staff@12345!` |
| Department staff (SWM) | `staff.swm@safecity.local` | `Staff@12345!` |
| Department staff (Electricity) | `staff.electricity@safecity.local` | `Staff@12345!` |
| Emergency responder | `responder@safecity.local` | `Responder@12345!` |
| Volunteer | `volunteer@safecity.local` | `Volunteer@12345!` |
| Citizens | `citizen1@safecity.local` … `citizen5@safecity.local` | `Citizen@12345!` |

The authoritative list is
`backend/apps/incidents/management/commands/seed_demo_data.py` — read it rather than
trusting any table, including this one.

The seed is idempotent: it uses `get_or_create` keyed on email and code, so re-running it
updates nothing and raises no duplicate errors.

---

## 4. Native install (no Docker)

Useful when you want a debugger attached or faster reloads.

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements/dev.txt
```

Create the database and point the app at it:

```bash
# In PostgreSQL:
#   CREATE DATABASE safecity OWNER safecity;
#   CREATE DATABASE safecity_test OWNER safecity;   -- needed for the test suite

cp ../.env.example ../.env
# Then edit .env and set:
#   DB_HOST=localhost
#   REDIS_URL=redis://localhost:6379/0
#   CELERY_BROKER_URL=redis://localhost:6379/1
```

```bash
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver 18081
```

Run Django's dev server on port **18081** to match the frontend's
`VITE_API_BASE_URL` (`http://localhost:18081/api/v1`). The frontend Vite
dev server proxies `/api`, `/media` and `/ws` there (see
`frontend/vite.config.ts`), so the default port 8000 would not match.

### Frontend

```bash
cd frontend
npm ci
npm run dev                        # http://localhost:5174
```

`npm ci` (not `npm install`) installs exactly `package-lock.json`, so you get the
versions CI will get.

### Background workers (optional natively)

```bash
cd backend
celery -A config worker -l info
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

Without them the app still works; SLA sweeps, escalations, thumbnails and daily
aggregates simply do not run.

---

## 5. Running tests

### Backend

```bash
make test          # cd backend && pytest
make coverage      # coverage over apps and config
```

> **The backend suite requires PostgreSQL.** There is no SQLite fallback, by design —
> the application depends on `tsvector` full-text search, JSONB, GIN indexes and partial
> unique constraints, and testing against a different engine would miss exactly the
> features that matter.
>
> **If `pytest` appears to hang, it is almost always waiting on an unreachable
> database.** Confirm `DB_HOST`/`DB_PORT` (default `localhost:5432`) point at a running
> PostgreSQL with a `safecity_test` database, or start the Docker stack first.

Test settings (`config/settings/test.py`) are tuned for determinism and speed: MD5
password hashing, throttles disabled, Celery eager, LocMem cache, in-memory channel
layer, and `--reuse-db` to avoid rebuilding the schema on every run. None of these
relaxations apply outside the test settings.

### Frontend

```bash
make test-frontend    # vitest
npm run typecheck     # tsc -b --noEmit
npm run lint          # eslint, max-warnings 0
```

### End-to-end

```bash
make docker-up && make migrate && make seed
make test-e2e         # Playwright
```

E2E runs against a **seeded** stack, so the migrate and seed steps are not optional.

### Lint and format

```bash
make lint     # ruff check + eslint
make format   # ruff format + prettier
```

---

## 6. Regenerating the API schema

```bash
make openapi      # writes docs/api-schema.yaml
```

Run this after changing serializers or viewsets.

---

## 7. Production-like stack (Docker)

To exercise the built images rather than the dev servers:

```bash
cp .env.example .env
# Set real values — compose refuses to start without them:
#   SECRET_KEY=<64+ random characters>
#   POSTGRES_PASSWORD=<something strong>
#   ALLOWED_HOSTS=<your hostnames>

docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate
```

| | Dev | Production-like |
|---|---|---|
| Settings | `config.settings.dev` | `config.settings.prod` |
| Frontend | Vite dev server on 5174 (`FRONTEND_PORT`) | nginx serving built assets on 8088 |
| Backend | `runserver` on 18081 (`BACKEND_PORT` → container 8000) | Daphne on 9080 |
| Secrets | defaults acceptable | `SECRET_KEY` and `POSTGRES_PASSWORD` **required** |
| DB / Redis ports | published | not published |

The production-like stack deliberately uses different host ports (9080/8088) so it can
run alongside the dev stack.

---

## 8. Kubernetes

See [KUBERNETES-AND-AWS.md](KUBERNETES-AND-AWS.md). Short version:

```bash
helm template safecity infrastructure/helm/safecity \
  -f infrastructure/helm/safecity/values-dev.yaml \
  --set secret.secretKey=... --set secret.postgresPassword=... > /tmp/rendered.yaml

helm upgrade --install safecity infrastructure/helm/safecity \
  -f infrastructure/helm/safecity/values-dev.yaml -n safecity-dev --create-namespace
```

The chart does not create PostgreSQL or Redis — you must supply endpoints in the overlay.

---

## 9. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| **API unreachable at the backend port** | `BACKEND_PORT` overridden in `.env` | Check `BACKEND_PORT` (`docker compose ps` shows the actual host mapping; this repo's `.env` uses `18081`) |
| **`pytest` hangs with no output** | PostgreSQL unreachable | Start the stack or fix `DB_HOST`/`DB_PORT`; the suite has no SQLite fallback |
| **Readiness returns 503** | A dependency is down | Read the `checks` map — it names it |
| **Frontend loads but API calls fail** | `VITE_API_BASE_URL` mismatch, or CORS | Check `VITE_API_BASE_URL` and `CORS_ALLOWED_ORIGINS` |
| **401 immediately after login** | Access token expired (15 min) | Expected; the client should refresh. Check the refresh flow |
| **Upload rejected** | Type, size, or magic-byte validation | Images ≤ 10 MB, video ≤ 100 MB, docs ≤ 5 MB; JPEG/PNG/WebP/HEIC only |
| **No email arrives** | Console email backend | Expected locally — emails print to the backend log. Set `EMAIL_HOST` for real SMTP |
| **No realtime notifications** | No WebSocket client in the SPA | Expected — see [Known limitations](PROJECT-MANAGEMENT.md#2-known-limitations). The notification API works |
| **Celery tasks never run** | Worker/beat not started | Start both; beat must be exactly one instance |
| **Migrations not applied** | Compose never auto-migrates | Run `make migrate` |
| **`make k8s-deploy` fails** | It passes `values-dev.yaml`, which must exist | It does; if Helm still fails, `helm template` first to see the actual error |
| **Port already in use** | Another stack running | `make docker-down`, or set `BACKEND_PORT`/`FRONTEND_PORT` |
| **Permission errors on volumes (Windows/WSL)** | Files owned by root | `make docker-down -v` and re-run, or fix ownership |

### Starting over

```bash
make docker-down -v     # stop and delete volumes — DESTROYS ALL DATA
make docker-up
make migrate
make seed
```

There is no way to recover data destroyed by `docker-down -v`. Take a dump first if it
matters:

```bash
docker compose exec -T db pg_dump -U safecity safecity | gzip > backup-$(date +%F).sql.gz
```
