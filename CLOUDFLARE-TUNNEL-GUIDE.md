# SafeCity — Free Public Deployment with Cloudflare Tunnel

> **Note:** The permanent live deployment now runs on **Render** (free tier) — see [`DEPLOYMENT-GUIDE.md`](DEPLOYMENT-GUIDE.md) Part 1: frontend at <https://safecity-1-rvk7.onrender.com>, backend at <https://safecity-6xje.onrender.com>. This guide remains useful for temporarily exposing a **local** stack at $0.

This guide shows how to expose your local SafeCity development stack to the public internet at **$0 cost** — no cloud account, no credit card required — using Cloudflare quick tunnels.

> ⚠️ **Quick tunnels are ephemeral** — URLs change every time `cloudflared` is restarted. This is perfect for demos/vivas but not for persistent hosting. For a permanent URL, add a domain to Cloudflare and use `cloudflared` as a Windows service.

---

## Prerequisites

- Docker Desktop (with Compose v2)
- Node.js 20+
- `cloudflared.exe` — download from https://developers.cloudflare.com/cloudflare-one/connections/connect-apps

---

## Step 1: Start the Local Stack

```powershell
cd C:\projects\safecity0
docker compose up -d
```

Wait for all services to be healthy:

```powershell
docker compose ps
```

Verify backend health:

```powershell
curl http://localhost:18081/api/health/
# Should return: {"status": "ok", "service": "safecity-backend"}
```

---

## Step 2: Start Cloudflare Quick Tunnels

Open **two PowerShell windows**. In each:

**Window 1 — Backend tunnel:**

```powershell
& "C:\path\to\cloudflared.exe" tunnel --url http://127.0.0.1:18081
```

**Window 2 — Frontend tunnel:**

```powershell
& "C:\path\to\cloudflared.exe" tunnel --url http://127.0.0.1:5176
```

Each outputs a URL like:

```
https://abc123.trycloudflare.com
```

**Copy both URLs** — you need them in Step 3.

---

## Step 3: Configure Backend CORS for the Frontend Tunnel

The backend must allow cross-origin requests from your frontend tunnel URL:

```powershell
cd C:\projects\safecity0
$env:BACKEND_PUBLIC_HOST = "https://<BACKEND_TUNNEL_URL>"
$env:FRONTEND_PUBLIC_HOST = "https://<FRONTEND_TUNNEL_URL>"
docker compose -f docker-compose.yml -f docker-compose.tunnel.yml up -d backend
```

Verify:

```powershell
curl https://<BACKEND_TUNNEL_URL>/api/health/
# Should return: {"status": "ok", "service": "safecity-backend"}
```

---

## Step 4: Rebuild Frontend Pointed at the Backend Tunnel

```powershell
cd C:\projects\safecity0\frontend
$env:VITE_API_BASE_URL = "https://<BACKEND_TUNNEL_URL>/api/v1"
$env:VITE_WS_URL = "wss://<BACKEND_TUNNEL_URL>/ws/"
$env:VITE_CSP_EXTRA = "https://<BACKEND_TUNNEL_URL> wss://<BACKEND_TUNNEL_URL>"
npm run build
npm run preview -- --port 5176 --host 127.0.0.1
```

Verify:

```powershell
curl https://<FRONTEND_TUNNEL_URL>/
# Should return HTTP 200
```

---

## Step 5: Run End-to-End Tests Through Public Tunnels

```powershell
cd C:\projects\safecity0\frontend
$env:E2E_BASE_URL = "https://<FRONTEND_TUNNEL_URL>"
$env:E2E_NO_SERVER = "1"
npx playwright test smoke.spec.ts a11y.spec.ts
```

**Expected result: 5 passed**

- smoke.spec.ts:27 — landing and public map render
- smoke.spec.ts:34 — citizen login reaches dashboard and report wizard opens
- smoke.spec.ts:43 — admin login reaches the incident queue
- a11y.spec.ts:44 — public pages have no serious a11y violations
- a11y.spec.ts:48 — citizen dashboard has no serious a11y violations

---

## Persistent Tunnel (Optional — Requires a Domain)

Quick tunnel URLs are ephemeral (change every restart). For a stable URL:

1. Add your domain to Cloudflare at [dash.cloudflare.com](https://dash.cloudflare.com)
2. Create a tunnel in [Zero Trust Dashboard → Networks → Tunnels](https://one.dash.cloudflare.com/)
3. Install as Windows service:
   ```powershell
   cloudflared.exe service install <TOKEN>
   cloudflared.exe service start
   ```
4. Add public hostnames pointing to `http://localhost:18081` and `http://localhost:5176`

---

## Important Notes

| Item | Details |
|------|---------|
| Cost | **$0** — no cloud account, no credit card |
| Tunnel URLs | **Ephemeral** — change every time `cloudflared` restarts |
| Machine must stay on | If your computer sleeps, tunnels die |
| Google OAuth | **Does not work** on tunnel URLs (Google requires pre-registered redirect URIs) |
| Both tunnels must stay open | Close either window and that service becomes unreachable |

---

## What's Verified Working Through Public Tunnels

| Test | Status |
|------|--------|
| Landing page render | ✅ Pass |
| Citizen login + report wizard | ✅ Pass |
| Admin incident queue | ✅ Pass |
| Public pages a11y (axe wcag2a/wcag2aa) | ✅ Pass |
| Dashboard a11y (axe wcag2a/wcag2aa) | ✅ Pass |
| API health endpoint | ✅ Pass |
| JWT login token issuance | ✅ Pass |

---

## What's NOT Working Through Public Tunnels

| Feature | Reason |
|---------|--------|
| Google OAuth | Google requires pre-registered redirect URIs; tunnel URLs change each restart |

---

## Files Modified for Tunnel Deployment

| File | Change |
|------|--------|
| `docker-compose.tunnel.yml` | Adds `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `ALLOWED_HOSTS` for public tunnel hosts |
| `frontend/index.html` | Added `%VITE_CSP_EXTRA%` placeholder to Content-Security-Policy `connect-src` |
| `frontend/vite.config.ts` | Added `process.env.VITE_CSP_EXTRA ??= ""` default |
| `docker-compose.tunnel.yml` docs | Added usage instructions |

---

## Quick Reference

```powershell
# 1. Start stack
docker compose up -d

# 2. Start tunnels (two PowerShell windows)
cloudflared.exe tunnel --url http://127.0.0.1:18081
cloudflared.exe tunnel --url http://127.0.0.1:5176

# 3. Update CORS + rebuild frontend
# (see steps 3-4 above)

# 4. Test
npx playwright test smoke.spec.ts a11y.spec.ts  # Should show: 5 passed
```
