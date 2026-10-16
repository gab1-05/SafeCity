# SafeCity — Public Deployment Guide (Cloudflare Tunnel)

This document describes how to expose the SafeCity local development stack to the public internet using **Cloudflare Tunnel** at **$0 cost** (no cloud account, no credit card required).

> ⚠️ **Quick tunnels are ephemeral** — URLs change every time `cloudflared` is restarted. For a persistent URL, add a domain to Cloudflare and use `cloudflared` as a Windows service (see "Persistent Tunnel" section below).

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
