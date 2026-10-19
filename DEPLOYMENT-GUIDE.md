# SafeCity — Deployment Guide

Two ways to put SafeCity online:

1. **Render (permanent, free tier)** — the current live deployment. Frontend at <https://safecity-1-rvk7.onrender.com>, backend at <https://safecity-6xje.onrender.com>. See **Part 1** below.
2. **Cloudflare quick tunnel (temporary)** — expose a local stack in seconds, no cloud account or credit card. See **Part 2**.

---

## Part 1: Render (Live Deployment)

### Architecture on Render

| Render resource | Name | Purpose |
|---|---|---|
| Web Service | SafeCity backend | Docker image from `backend/Dockerfile`, runs Daphne (ASGI) on `:8000` |
| Static Site | SafeCity frontend | React build (`npm run build` → `dist`) served from Render's CDN |
| PostgreSQL | `safecity-db` | Managed Postgres (Singapore region, **free tier — expires 2026-11-17**) |
| Key Value (Redis) | — | Cache, Channel layers, Celery broker (optional — see note) |

### Step 1: Backend web service

1. **New → Web Service** → connect the GitHub repo.
2. Settings that matter (a `"/requirements": not found` error almost always means the build context is wrong):
   - **Docker Build Context Directory:** `backend`
   - **Dockerfile Path:** `backend/Dockerfile`
3. There is **no Shell or Pre-Deploy Command on the free plan**, so migrations and seeding run inside the container `CMD`:

   ```dockerfile
   CMD python manage.py migrate --noinput && python manage.py seed_demo_data && daphne -b 0.0.0.0 -p 8000 config.asgi:application
   ```

   `seed_demo_data` is idempotent, so re-running it on every boot is safe.

### Step 2: Backend environment variables

Web Service → **Environment**:

```bash
DJANGO_SETTINGS_MODULE=config.settings.prod
SECRET_KEY=<rotate-this>
DEBUG=false
ALLOWED_HOSTS=safecity-6xje.onrender.com
CORS_ALLOWED_ORIGINS=https://safecity-1-rvk7.onrender.com,http://localhost:5174
CSRF_TRUSTED_ORIGINS=https://safecity-6xje.onrender.com,https://safecity-1-rvk7.onrender.com,http://localhost:5174

# Postgres — copy from the database's Connections page
DATABASE_URL=postgresql://…
POSTGRES_DB=…  POSTGRES_USER=…  POSTGRES_PASSWORD=…  DB_HOST=…  DB_PORT=5432

# Redis — copy the full Internal URL from the Key Value's Connections page,
# then append /0 (cache) and /1 (Celery broker). Optional but recommended.
REDIS_URL=redis://…:6379/0
CELERY_BROKER_URL=redis://…:6379/1

GOOGLE_CLIENT_ID=<google-oauth-client-id>
WEB_CONCURRENCY=1
```

> **Redis is optional.** With no `REDIS_URL`, `config/settings/base.py` falls back to LocMem cache, the in-memory Channel layer and eager Celery — the API still works, you just lose shared caching / WebSockets / background workers. A *wrong* Redis URL is worse than none (connection errors on every rate-limited request), so copy it exactly, don't retype it.

### Step 3: Frontend static site

1. **New → Static Site** → connect the same repo.
2. Build command `npm run build`, publish directory `dist`.
3. Environment:
   ```bash
   VITE_API_BASE_URL=https://safecity-6xje.onrender.com/api/v1
   VITE_WS_URL=wss://safecity-6xje.onrender.com/ws/
   ```
4. **Redirects/Rewrites tab → Add Rule → Save Changes:**

   | Source | Destination | Action |
   |---|---|---|
   | `/*` | `/index.html` | **Rewrite** |

   Without this rule every deep link (`/report`, `/login`, a refresh on any route) returns a 404 — the static server has no file at that path, so it must fall back to the SPA shell.

> **CSP is automatic:** `vite.config.ts` derives the extra `connect-src` origins from `VITE_API_BASE_URL` / `VITE_WS_URL` at build time. If you ever see `Connecting to '<backend>' violates the following Content Security Policy directive`, the static site is missing `VITE_API_BASE_URL`.

### Step 4: Google OAuth origins

Google Cloud Console → **Credentials** → your OAuth Client ID → **Authorized JavaScript origins**:

```
http://localhost:5174
http://127.0.0.1:5174
https://safecity-1-rvk7.onrender.com
```

The origin must be the **frontend** that renders the sign-in button — using only the backend URL yields `Error 400: origin_mismatch`.

### Step 5: Verify

```bash
curl https://safecity-6xje.onrender.com/api/health/        # {"status": "ok", …}
curl https://safecity-6xje.onrender.com/api/meta/config/   # 17 categories, google_client_id set
curl -i https://safecity-6xje.onrender.com/api/v1/incidents/   # 200 (public list) or 401 — never 500
curl -i https://safecity-1-rvk7.onrender.com/report        # 200 HTML shell (rewrite rule works)
```

### Render free-tier caveats

| Caveat | Effect | Mitigation |
|---|---|---|
| Instance spins down after ~15 min idle | First request takes up to ~50 s (cold start) | Repeats are fast once warm; upgrade to paid for always-on |
| Postgres free DB expires **2026-11-17** | Database is deleted after expiry | Upgrade or dump/restore elsewhere before that date |
| Shell / Pre-Deploy Command are paid | Cannot run one-off commands in the dashboard | Startup logic lives in the Dockerfile `CMD` |
| Deploys auto-run on push to `main` | Every push rebuilds/restarts | Push only when you intend to deploy |

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `/requirements": not found` on deploy | Wrong build context | Set **Docker Build Context Directory** to `backend` |
| Deep link returns 404 (black page) | Missing SPA rewrite | Add `/*` → `/index.html` as **Rewrite** |
| Page loads, but every API call blocked | CSP `connect-src` missing the API origin | Set `VITE_API_BASE_URL` on the static site and redeploy |
| Every DRF endpoint returns 500 (plain views 200) | Cache/Redis unreachable | Set a correct `REDIS_URL`, or remove it to use the in-process fallback |
| Google button missing / `origin_mismatch` | Frontend origin not registered | Add `https://safecity-1-rvk7.onrender.com` to Authorized JavaScript origins |
| Login says credentials invalid | Demo account deactivated | Reactivate it (User management) or re-run `seed_demo_data` |

---

## Part 2: Cloudflare Tunnel (Temporary / Local Stacks)

This document describes how to expose the SafeCity local development stack to the public internet using **Cloudflare Tunnel** at **$0 cost** (no cloud account, no credit card required).

> ⚠️ **Quick tunnels are ephemeral** — URLs change every time `cloudflared` is restarted. For a persistent URL, add a domain to Cloudflare and use `cloudflared` as a Windows service (see "Persistent Tunnel" section below). For a permanent free URL, use **Part 1 (Render)** instead.

---

## Prerequisites

- Docker Desktop running
- `cloudflared.exe` installed (download from https://developers.cloudflare.com/cloudflare-one/connections/connect-apps)
- SafeCity compose stack built (`docker compose build`)

---

## Step 1: Start the Local Stack

```powershell
cd C:\projects\safecity0
docker compose up -d
```

Wait for all 7 services to be healthy:
- `safecity0-backend-1` (healthy)
- `safecity0-db-1` (healthy)
- `safecity0-redis-1` (healthy)
- `safecity0-minio-1` (healthy)
- `safecity0-frontend-1` (up)
- `safecity0-celery-1` (healthy)
- `safecity0-celery-beat-1` (up)

Verify locally:
```powershell
curl http://localhost:18081/api/health/
# Should return: {"status": "ok", "service": "safecity-backend"}
```

---

## Step 2: Start Cloudflare Quick Tunnels

Open **two PowerShell windows**. In each, run:

**Window 1 — Backend tunnel:**
```powershell
& "C:\path\to\cloudflared.exe" tunnel --url http://127.0.0.1:18081
```

**Window 2 — Frontend tunnel:**
```powershell
& "C:\path\to\cloudflared.exe" tunnel --url http://127.0.0.1:5176
```

Each will output a URL like:
```
https://xxx.trycloudflare.com
```

**Copy both URLs** — you'll need them in Step 3.

---

## Step 3: Configure Backend CORS for Frontend Tunnel

The backend needs to allow cross-origin requests from the frontend tunnel URL. Update `docker-compose.tunnel.yml` or set environment variables before restarting the backend:

```powershell
cd C:\projects\safecity0
$env:BACKEND_PUBLIC_HOST = "<BACKEND_TUNNEL_URL>"
$env:FRONTEND_PUBLIC_HOST = "<FRONTEND_TUNNEL_URL>"
docker compose -f docker-compose.yml -f docker-compose.tunnel.yml up -d backend
```

Verify backend is reachable:
```powershell
curl https://<BACKEND_TUNNEL_URL>/api/health/
# Should return: {"status": "ok", "service": "safecity-backend"}
```

---

## Step 4: Rebuild Frontend with Tunnel URLs

```powershell
cd C:\projects\safecity0\frontend
$env:VITE_API_BASE_URL = "https://<BACKEND_TUNNEL_URL>/api/v1"
$env:VITE_WS_URL = "wss://<BACKEND_TUNNEL_URL>/ws/"
$env:VITE_CSP_EXTRA = "https://<BACKEND_TUNNEL_URL> wss://<BACKEND_TUNNEL_URL>"
npm run build
npm run preview -- --port 5176 --host 127.0.0.1
```

Verify frontend:
```powershell
curl https://<FRONTEND_TUNNEL_URL>/
# Should return HTTP 200
```

---

## Step 5: Run End-to-End Tests

```powershell
cd C:\projects\safecity0\frontend
$env:E2E_BASE_URL = "https://<FRONTEND_TUNNEL_URL>"
$env:E2E_NO_SERVER = "1"
npx playwright test smoke.spec.ts a11y.spec.ts
# Should show: 5 passed
```

---

## Persistent Tunnel (Optional)

If you own a domain and want a stable URL:

1. Add your domain to Cloudflare at [dash.cloudflare.com](https://dash.cloudflare.com)
2. In Zero Trust Dashboard → Networks → Tunnels, create a tunnel
3. Install cloudflared as a Windows service:
   ```powershell
   cloudflared.exe service install <TOKEN>
   cloudflared.exe service start
   ```
4. Add public hostnames pointing to `http://localhost:18081` and `http://localhost:5176`
5. Update `docker-compose.tunnel.yml` with your domain names

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Tunnel returns 1033 error | `cloudflared` process stopped. Restart it. |
| Tunnel returns 502 | Backend not running. Check `docker compose ps`. |
| Frontend shows blank page | CSP blocking API calls. Add tunnel URL to `VITE_CSP_EXTRA`. |
| Login fails | CORS blocking API. Add frontend tunnel URL to `CORS_ALLOWED_ORIGINS`. |
| Tunnel URL changes | Quick tunnel URLs are ephemeral. Restart `cloudflared` and get new URL. |

---

## Important Notes

- **Quick tunnel URLs are ephemeral** — they die when `cloudflared` stops or your machine sleeps
- **Keep both tunnel windows open** while using the public URLs
- **Google OAuth does not work** on tunnel URLs (Google requires pre-registered redirect URIs)
- **Tunnels are $0** — no Cloudflare account or credit card required for quick tunnels
