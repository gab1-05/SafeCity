# SafeCity — SDP Project
**The Bombay Salesian Society**

SafeCity is a Smart City Incident Management and Civic Response Platform. Citizens report civic incidents (road damage, flooding, fire hazards, broken streetlights, garbage, water leaks, electrical hazards, public-safety threats, etc.), and authorized authorities — department staff, emergency responders, volunteers, city admins and superusers — verify, prioritize, assign, monitor, escalate and resolve them, with full transparency, SLA tracking, auditability and citizen feedback.

**How it works (end to end):** single reporting wizard (category → location → evidence → severity) → automatic routing to the owning department → enforced status workflow (`draft → submitted → under_review → verified → assigned → in_progress → resolved → closed`, plus `rejected / duplicate / awaiting_info / escalated / reopened`) → per-(category, severity) SLA deadlines with breach sweeps → assignment (manual / auto / workload-aware) → resolution with evidence → citizen confirmation + satisfaction rating. Every state change writes an append-only audit row in the same transaction; public views strip PII and jitter coordinates; AI suggestions are advisory only and always require human review.

> ⚠️ SafeCity is an **incident coordination tool for the SDP project**. It is *not* an official emergency service and is *not* an officially integrated government system. In a real emergency always call your local emergency number.

---

## Functionality by role

### Public (no login)
- Landing, About, Announcements, Live public map (all active statuses + recently resolved), Nearby incidents (geolocation + radius filter, live WebSocket refresh), Track a report by reference number (`SC-…`) or shareable token link, Login / Register (incl. Google sign-in, elevated-role request) / Forgot password / 2FA verify.

### Citizen (authenticated)
- Personal dashboard (active / resolved reports, status cards, notifications, feedback history), 7-step report wizard (category, geocoded address + reverse-geocode, duplicate warning, media upload with type/size validation, EXIF stripping, anonymous-report option), My Reports (search/filter), Incident detail (public timeline, comments, media lightbox, PDF/CSV export, confirm resolution + satisfaction rating), Notifications center + channel preferences, Profile (edit, password change, TOTP 2FA setup/disable/recovery codes, active sessions revoke, role-change request, saved locations/filters, consent + account-deletion request).

### Department staff / Emergency responder / Volunteer
- Authority operations dashboard (KPIs, queues, workload), Incident triage queue (filter by status / severity / category / ward / SLA / emergency, full-text search), verify / reject with reason, assign / auto-assign / transfer, status transitions (enforced matrix), internal vs public comments, escalate with levels, merge duplicates, reopen, similar-incident lookup, high/critical emergency queue for responders, community feed for volunteers, analytics trends + CSV export.

### City admin / Superuser (all authority powers plus)
- Administration overview (platform health, people, SLA breaches, category/ward breakdowns, department load, governance quick links), User management (list by role, change role + department, activate/deactivate, unlock login lockouts, unblock reporting, approve/reject role requests), Announcements (create / publish / pin, audience targeting), Audit-log viewer (filterable, immutable), SLA configurations + escalation rules, Django admin (`/admin/`), reference data (categories, wards/zones) via seed/shell.

### Backend modules (`backend/apps/`)
- `accounts` — JWT access (15 min) + rotating refresh (7 d) with blacklist, lockout/throttling, TOTP 2FA, Google OAuth, sessions, profile/privacy, consents, deletion requests, role requests.
- `incidents` — CRUD, transition-matrix enforcement, SLA computation + breach flags, assignment, escalation, merge/reopen/confirm, media (strict validation), comments (public/internal), timelines, similarity/duplicate check, public track/token views, CSV/PDF export.
- `notifications` — in-app + email (+SMS/push adapters), WebSocket fan-out (`/ws/notifications/`), per-user preferences.
- `analytics` — role-scoped KPIs, trends, by-category/ward/department/status/severity, CSV export, daily aggregates (Celery beat).
- `audit` — append-only log of every state change (actor, action, object, diff, request/IP).
- `departments` — department directory + workload view; `core` — wards/zones, geocode (Nominatim), SLA/escalation config, health/readiness/meta; `ai` — advisory category/severity/duplicate suggestions (mock default, OpenAI-compatible optional, PII-scrubbed, human decision recorded); `announcements` — city broadcasts.

## Working Features

### Frontend (React 18 + TypeScript + Vite + Tailwind)
- **Modern Design System** — Comprehensive CSS variables for colors, spacing, typography, shadows, radii, transitions
- **Dark/Light Mode** — System preference detection with manual toggle, persisted to localStorage
- **Responsive Layout** — Mobile-first with sidebar navigation, sticky header, toast notifications
- **Role-Based Navigation** — Dynamic sidebar based on user role (citizen, department_staff, emergency_responder, city_admin, superuser)
- **Pages:**
  - Public: Landing, Live Map, Track Report, Announcements, About, Login/Register
  - Citizen: Dashboard, Report Incident, My Incidents, Incident Detail, Notifications, Profile
  - Authority: Operations Dashboard, Incident Queue, Analytics, Admin Overview, User Management, Audit Logs
- **Real-time Updates** — TanStack Query with 30s polling, WebSocket-ready architecture
- **Toast Notifications** — Sonner-based with success/error/warning/info/loading variants
- **Error Boundaries** — Graceful error handling with retry/reload options
- **PWA Ready** — Service worker registration for offline support
- **Accessibility** — Semantic HTML, ARIA labels, focus management, reduced motion support

### Backend (Django 5 + DRF)
- **Multi-role Authentication** — JWT with access/refresh tokens, 2FA support
- **Incident Management** — Full CRUD with status workflow, SLA tracking, severity classification
- **Role-Based Access Control** — Citizen, department_staff, emergency_responder, city_admin, superuser, volunteer
- **Notifications** — In-app + email with unread counts
- **Analytics** — Response time metrics, department performance, trend analysis
- **Audit Logging** — Comprehensive audit trail for all actions
- **API Documentation** — Swagger/OpenAPI at `/api/schema/swagger/`
- **Database** — PostgreSQL with full-text search, JSONB, GIN indexes, partial unique constraints
- **Async Processing** — Celery + Redis for background tasks, scheduled jobs

### Infrastructure
- **Docker Compose** — Full stack with db, redis, minio, backend, celery, celery-beat, frontend
- **Production Ready** — Multi-stage Dockerfiles, health checks, resource limits
- **CI/CD** — GitHub Actions workflow for lint, test, build, deploy
- **Monitoring** — Health endpoints, structured logging

---

## Quick Start (Docker — Recommended)

### Prerequisites
- Docker Desktop (with Compose v2)
- Make (optional, for convenience commands)
- Git

### 1. Clone & Configure
```bash
git clone <repository-url>
cd SafeCity
cp .env.example .env            # defaults work for local development
```

### 2. Start Full Stack
```bash
# Using Make (recommended)
make docker-up                  # builds + starts db, redis, minio, backend, celery, frontend
make migrate                    # apply migrations
make seed                       # demo data (users, incidents, departments…)

# Or directly with Docker Compose
docker compose up --build -d    # builds and starts all services
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_demo_data
```

> Ports come from `.env`: `BACKEND_PORT` (default `18081`) maps to the container's `:8000`, `FRONTEND_PORT` (default `5174`) maps to Vite `:5174`. This repo's `.env` uses `18081`/`5174`. If you change them, update `VITE_API_BASE_URL` / `VITE_WS_URL` to match.

### 3. Access Services (with this repo's `.env`: `BACKEND_PORT=18081`, `FRONTEND_PORT=5174`)
| Service | URL | Notes |
|---|---|---|
| **Frontend** | http://localhost:5174 | React dev server with HMR |
| **Backend API** | http://localhost:18081/api/v1/ | Django REST API |
| **Swagger UI** | http://localhost:18081/api/schema/swagger/ | Interactive API docs |
| **Django Admin** | http://localhost:18081/admin/ | Admin panel (no app models registered — reference data is shell/seed-managed) |
| **Health** | http://localhost:18081/api/health/ | Liveness (`{"status":"ok"}`) |
| **Readiness** | http://localhost:18081/api/readiness/ | DB / cache / storage checks |
| **MinIO Console** | http://localhost:9001 | minioadmin / minioadmin |
| **PostgreSQL** | localhost:5432 | safecity/safecity |
| **Redis** | localhost:6379 | No auth (dev) |

### Demo Credentials (LOCAL DEVELOPMENT ONLY)
| Role | Email | Password |
|---|---|---|
| Superuser / City Admin | admin@safecity.local | Admin@12345! |
| Department staff | staff.water@safecity.local | Staff@12345! |
| Emergency responder | responder@safecity.local | Responder@12345! |
| Volunteer | volunteer@safecity.local | Volunteer@12345! |
| Citizen | citizen1@safecity.local | Citizen@12345! |

> **Note:** All department staff accounts use `Staff@12345!` (roads, fire, swm, electricity, water). Citizens `citizen1@` through `citizen5@` use `Citizen@12345!`.

Verify the stack:
```bash
docker compose ps                                   # backend should be Up (healthy)
curl http://localhost:18081/api/health/             # {"status": "ok", ...}
curl http://localhost:18081/api/readiness/
```

---

## Quick Start (Without Docker)

### Backend (Python 3.12+)
```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements/dev.txt

# Configure environment (use local DB/Redis)
cp ../.env.example ../.env
# Edit .env: DB_HOST=localhost, REDIS_URL=redis://localhost:6379/0

# Start PostgreSQL & Redis (if not running)
docker run -d --name postgres -e POSTGRES_DB=safecity -e POSTGRES_USER=safecity -e POSTGRES_PASSWORD=safecity -p 5432:5432 postgres:16-alpine
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Initialize database
python manage.py migrate
python manage.py seed_demo_data

# Run development server
python manage.py runserver 0.0.0.0:8000
# API available at http://localhost:8000/api/v1/
```

### Frontend (Node 20+)
```bash
cd frontend

# Install dependencies
npm ci

# Configure API URL (if backend on different port)
# Create .env.local:
# VITE_API_BASE_URL=http://localhost:18081/api/v1
# VITE_WS_URL=ws://localhost:18081/ws/

# Run development server
npm run dev
# Frontend at http://localhost:5174
```

---

## Running Frontend & Backend Separately

### Option 1: Frontend Only (with Backend API Proxy)
```bash
cd frontend

# Configure proxy in vite.config.ts (already configured)
# Server runs on 5174, proxies /api/* to http://localhost:18081
# (http://backend:8000 inside Docker via DOCKER=true)

npm run dev
# Access at http://localhost:5174
```

### Option 2: Backend Only (API Server)
```bash
cd backend
source .venv/bin/activate
python manage.py runserver 0.0.0.0:18081
# API at http://localhost:18081/api/v1/
# Admin at http://localhost:18081/admin/
```

### Option 3: Frontend + External Backend
```bash
# Frontend
cd frontend
# Set VITE_API_BASE_URL in .env.local to your backend URL
echo "VITE_API_BASE_URL=https://api.yourdomain.com/api/v1" > .env.local
npm run dev

# Backend runs independently (any host)
# Ensure CORS_ALLOWED_ORIGINS includes http://localhost:5174
```

### Option 4: Docker Backend + Local Frontend
```bash
# Start only backend services in Docker
cd SafeCity
docker compose up -d db redis minio backend celery celery-beat

# Frontend runs locally
cd frontend
npm run dev
# Frontend proxies to http://localhost:18081 (BACKEND_PORT from .env)
```

### Option 5: Local Backend + Docker Frontend
```bash
# Start backend locally (as in "Without Docker" section)
# Ensure .env has DB_HOST=localhost, REDIS_URL=redis://localhost:6379/0

# Frontend in Docker (uses host.docker.internal for backend)
cd SafeCity
docker compose up -d frontend
# Frontend at http://localhost:5174
```

---

## Development Commands

### Using Make (Root Directory — see `Makefile` for the full list)
```bash
make help              # Show all available targets
make docker-up         # Start full stack (builds + starts all services)
make docker-down       # Stop all services (keeps data; use -v to destroy)
make docker-logs       # Follow backend logs
make docker-build      # Build all Docker images
make migrate           # Run Django migrations (in backend container)
make seed              # Seed demo data (in backend container)
make test              # Run backend tests (pytest)
make test-frontend     # Run frontend tests (vitest --run)
make test-e2e          # Run Playwright E2E suite (needs seeded stack)
make lint              # Lint both (ruff check + eslint)
make format            # Format both (ruff + prettier)
make coverage          # Backend coverage report
make openapi           # Regenerate OpenAPI schema to docs/api-schema.yaml
make superuser         # Create admin user interactively (in backend container)
```

### Frontend Commands
```bash
cd frontend
npm run dev            # Dev server with HMR (Vite :5174)
npm run build          # Production build (tsc -b && vite build)
npm run preview        # Preview production build
npm run lint           # ESLint (max-warnings 0)
npm run format         # Prettier write
npm run format:check   # Prettier check
npm run typecheck      # TypeScript check (tsc -b --noEmit)
npm run test           # Vitest unit tests (watch); use `npm run test -- --run` for CI
```

### Backend Commands
```bash
cd backend
source .venv/bin/activate

python manage.py migrate
python manage.py makemigrations
python manage.py seed_demo_data
python manage.py createsuperuser
python manage.py runserver
python manage.py shell
python manage.py dbshell

# Celery (separate terminals)
celery -A config worker -l info
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

---

## Docker Commands Reference

```bash
# Build specific service
docker compose build frontend
docker compose build backend

# View logs
docker compose logs -f frontend
docker compose logs -f backend
docker compose logs -f db

# Restart single service
docker compose restart frontend

# Rebuild after dependency changes
docker compose up -d --build frontend

# Run one-off commands
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
docker compose exec frontend npm run build

# Shell access
docker compose exec backend bash
docker compose exec frontend sh

# Stop everything
docker compose down

# Stop + remove volumes (clears database!)
docker compose down -v

# Scale workers
docker compose up -d --scale celery=3
```

---

## Environment Configuration

### Key Environment Variables (.env)
```bash
# Core
DJANGO_SETTINGS_MODULE=config.settings.dev
SECRET_KEY=your-secret-key-here
DEBUG=true
ALLOWED_HOSTS=localhost,127.0.0.1,backend
BACKEND_PORT=18081
FRONTEND_PORT=5174

# Database
POSTGRES_DB=safecity
POSTGRES_USER=safecity
POSTGRES_PASSWORD=safecity
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1

# Frontend
VITE_API_BASE_URL=http://localhost:18081/api/v1
VITE_WS_URL=ws://localhost:18081/ws/

# CORS (must match frontend port)
CORS_ALLOWED_ORIGINS=http://localhost:5174,http://127.0.0.1:5174
CSRF_TRUSTED_ORIGINS=http://localhost:5174

# Optional: S3/MinIO
MEDIA_BACKEND=local
S3_ENDPOINT_URL=http://minio:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_S3_BUCKET=safecity
```

### Frontend Environment Files
```bash
# frontend/.env.local (development)
VITE_API_BASE_URL=http://localhost:18081/api/v1
VITE_WS_URL=ws://localhost:18081/ws/

# frontend/.env.production
VITE_API_BASE_URL=https://api.yourdomain.com/api/v1
VITE_WS_URL=wss://api.yourdomain.com/ws/
```

---

## Project Structure

```
SafeCity/
├── backend/                 # Django 5 + DRF
│   ├── apps/
│   │   ├── accounts/        # Auth (JWT, 2FA, OAuth), users, roles, profiles, deletion/role requests
│   │   ├── incidents/       # Incident CRUD, workflow matrix, SLA, media, comments, exports
│   │   ├── departments/     # Department directory + workload (models live in accounts)
│   │   ├── notifications/   # In-app, email, WebSocket fan-out, preferences
│   │   ├── announcements/   # City broadcasts (audience, pin/publish)
│   │   ├── analytics/       # Role-scoped KPIs, trends, aggregates, CSV export
│   │   ├── audit/           # Immutable audit log
│   │   ├── ai/              # Advisory suggestions (mock / OpenAI-compatible)
│   │   └── core/            # Wards/zones, geocode, SLA/escalation config, health/readiness
│   ├── config/              # Django settings
│   ├── requirements/        # pip requirements (base/dev/prod)
│   ├── Dockerfile
│   └── manage.py
├── frontend/                # React 18 + TypeScript + Vite
│   ├── src/
│   │   ├── api/             # API clients (axios + tanstack query)
│   │   ├── components/      # Reusable UI components
│   │   │   ├── ui/          # Base components (Button, Card, Input, etc.)
│   │   │   ├── incident/    # Incident-specific components
│   │   │   └── layout/      # Layout components
│   │   ├── features/        # Feature modules
│   │   ├── hooks/           # Custom React hooks
│   │   ├── layouts/         # Page layouts (PublicLayout, AppLayout)
│   │   ├── lib/             # Utilities (cn, formatters, etc.)
│   │   ├── pages/           # Page components
│   │   │   ├── public/      # Public pages
│   │   │   ├── citizen/     # Citizen dashboard
│   │   │   ├── authority/   # Authority pages
│   │   │   └── shared/      # Shared pages
│   │   ├── routes/          # Router configuration
│   │   ├── services/        # WebSocket, geolocation, etc.
│   │   ├── store/           # Zustand stores (auth, theme)
│   │   ├── types/           # TypeScript types
│   │   ├── utils/           # Helper functions
│   │   ├── App.tsx          # Root component (routes)
│   │   ├── main.tsx         # Entry point
│   │   └── index.css        # Global styles + design system
│   ├── public/              # Static assets
│   ├── Dockerfile
│   ├── nginx.conf           # Production nginx config
│   ├── package.json
│   ├── tailwind.config.cjs
│   ├── tsconfig.json
│   └── vite.config.ts
├── infrastructure/          # IaC (Terraform, Kubernetes, Helm)
├── docs/                    # SDP Documentation
├── scripts/                 # Helper scripts
├── docker-compose.yml       # Development stack
├── docker-compose.prod.yml  # Production stack
├── Makefile
└── .env.example
```

---

## Production Deployment

### Docker Compose (Production)
```bash
# Use production compose file
docker compose -f docker-compose.prod.yml up -d --build

# Production uses:
# - Nginx for frontend (serves static, proxies API)
# - Gunicorn for backend
# - Proper health checks
# - Resource limits
# - SSL termination (configure in nginx.conf)
```

### Static Hosting (Frontend Only)
```bash
cd frontend
npm run build
# Deploy dist/ to Vercel, Netlify, Cloudflare Pages, S3+CloudFront, etc.
```

### Kubernetes (Helm)
```bash
cd infrastructure/kubernetes
helm install safecity ./safecity -f values-prod.yaml
```

### CI/CD (GitHub Actions)
```yaml
# .github/workflows/ci.yml runs on push/PR:
# 1. Lint (ruff, eslint, prettier)
# 2. Type check (tsc)
# 3. Test (pytest, vitest, playwright)
# 4. Build Docker images
# 5. Push to GHCR
# 6. Deploy to staging (on develop branch)
# 7. Deploy to production (on main branch, manual approval)
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|---|---|
| Frontend can't reach API | Check `VITE_API_BASE_URL` in frontend/.env.local; verify `CORS_ALLOWED_ORIGINS` in backend .env |
| Database connection refused | Ensure db container is healthy: `docker compose logs db` |
| Redis connection refused | Ensure redis container is healthy: `docker compose logs redis` |
| Port already in use | Change `FRONTEND_PORT` or `BACKEND_PORT` in .env |
| Migration errors | `docker compose exec backend python manage.py migrate --fake-initial` |
| CORS errors | Verify `CSRF_TRUSTED_ORIGINS` includes frontend origin |
| WebSocket fails | Check `VITE_WS_URL` and nginx proxy config for `/ws/` |

### Debug Commands
```bash
# Check container health
docker compose ps

# View all logs
docker compose logs --tail=100

# Test API health
curl http://localhost:18081/api/health/

# Test frontend
curl http://localhost:5174

# Check database
docker compose exec db psql -U safecity -d safecity -c "\dt"

# Check Redis
docker compose exec redis redis-cli ping
```

---

## Testing

### Backend
```bash
cd backend
source .venv/bin/activate

# Unit tests
pytest

# With coverage
pytest --cov=apps --cov-report=html

# Specific app
pytest apps/incidents/tests/
```

### Frontend
```bash
cd frontend

# Unit/Component tests (watch mode)
npm run test

# Single run (CI)
npm run test -- --run

# E2E tests (Playwright, needs seeded Docker stack)
npx playwright test
```

---

## Security

See `SECURITY.md`. Key points:
- **Never commit real `.env` files** — use `.env.example` as template
- **Rotate SECRET_KEY** in production
- **Use strong passwords** for database/Redis
- **Enable HTTPS** in production (configure SSL in nginx)
- **Restrict CORS** to known origins only
- **Audit dependencies** regularly: `npm audit`, `pip-audit`

---

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feat/your-feature`
3. Make changes with tests
4. Run lint/format: `make format && make lint`
5. Commit with conventional commits: `git commit -m 'feat: add your feature'`
6. Push branch: `git push origin feat/your-feature`
7. Open Pull Request

### Code Style
- **Backend**: Ruff (lint + format), pytest
- **Frontend**: ESLint (lint), Prettier (format), TypeScript strict mode

---

## Documentation

- **`docs/README.md`** — SDP documentation index
- `docs/ARCHITECTURE.md` — Architecture proposal
- `docs/REQUIREMENTS.md` — Functional & non-functional requirements
- `docs/DATA-MODEL.md` — Data model
- `docs/API-REFERENCE.md` — REST API reference
- `docs/ROLES-AND-ACCESS.md` — RBAC design
- `docs/SECURITY-AND-PRIVACY.md` — Security & privacy
- `docs/DEVOPS.md` — Deployment guide
- `docs/USER-MANUAL.md` — End-user guide
- `docs/ADMINISTRATOR-MANUAL.md` — Admin guide
- `docs/DEMO-SCRIPT.md` — Demonstration script
- `docs/VIVA-QA.md` — Evaluation support

---

## License

MIT — see `LICENSE`.

---

## Acknowledgments

- **Django** & **Django REST Framework** — Backend framework
- **React** & **Vite** — Frontend framework
- **Tailwind CSS** — Utility-first styling
- **TanStack Query** — Server state management
- **Zustand** — Client state management
- **Leaflet** & **React Leaflet** — Mapping
- **PostgreSQL** — Relational database with full-text search + JSONB
- **Redis** — Caching & message broker
- **Celery** — Distributed task queue
