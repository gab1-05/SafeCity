# Step 4b: Free Online Deployment Evidence ($0, Cloudflare Quick Tunnel)

Captured: 2026-10-16
Purpose: operator asked for the app "online for free". Full AWS apply is blocked
(no credentials; dev ≈ $185/mo, over the free-tier-only constraint — see
`step4-terraform-kind.md`). This records the $0 public deployment actually built
and verified: Cloudflare quick tunnels (no account, no cost) in front of the
local compose stack.

## Public endpoints (live while the tunnel processes run on this machine)

| Service | Public URL | Local origin |
|---------|-----------|--------------|
| API | https://lamb-lips-diamonds-regard.trycloudflare.com | compose `backend` on 127.0.0.1:18081 |
| SPA | https://brand-lucy-gaming-shuttle.trycloudflare.com | `vite preview` (fresh build) on 127.0.0.1:5176 |

The tunnel URLs are random per run and die with the processes — a shop window for
demos, not production hosting. The machine must stay on.

## What was required (all real issues hit during the work)

1. **Tunnel rejects unknown hosts.** First public request returned 400
   (Django `DisallowedHost`). Fixed with the new `docker-compose.tunnel.yml`
   overlay, which adds both tunnel hosts to `ALLOWED_HOSTS` plus the matching
   `CORS_ALLOWED_ORIGINS` / `CSRF_TRUSTED_ORIGINS`, and recreates only the
   `backend` service. Verified: preflight `OPTIONS` returns 200 with the correct
   `Access-Control-Allow-Origin`.
2. **Content-Security-Policy blocked the API.** Browser logins failed (token never
   landed) with `connect-src` violations: the CSP in `frontend/index.html` (and
   `nginx.conf`) hardcodes `localhost:18081`. This was a genuine
   production-readiness bug — *any* non-localhost deployment would hit it.
   Fixed by adding a build-time `%VITE_CSP_EXTRA%` placeholder to `connect-src`
   in `index.html`, with an empty default in `vite.config.ts`
   (`process.env.VITE_CSP_EXTRA ??= ""`) so local/CI builds are byte-identical
   in behavior to before. Verified both ways: default build has no literal
   placeholder and keeps the localhost entries; tunnel build carries the tunnel
   origins in `connect-src`.
3. **Frontend bundle bakes the API URL.** Rebuilt with
   `VITE_API_BASE_URL=https://<backend-tunnel>/api/v1` and
   `VITE_WS_URL=wss://<backend-tunnel>/ws/`; bundle confirmed to contain the
   tunnel host; served on :5176 (compose dev frontend on :5174 untouched).

## Verification (all executed, none assumed)

- `GET <backend-tunnel>/api/health/` → `{"status": "ok", "service": "safecity-backend"}`
- `GET <frontend-tunnel>/` → HTTP 200
- `POST <backend-tunnel>/api/v1/auth/token/` (citizen1) → JWT access token issued
- **Playwright smoke + a11y (5/5) against the PUBLIC frontend**: landing + public
  map, citizen login + report wizard, admin queue, public-pages a11y, dashboard
  a11y — all green over the internet (53–84s, tunnel latency).

## Security and limits (read before sharing the URLs)

- This publishes a `DEBUG=true` dev stack with default seed credentials
  (`citizen1@…` / `Admin@12345!`): anyone with the URL can log in as admin.
  Demo data only, share narrowly, kill the tunnels afterwards
  (stop the `cloudflared` processes + the `:5176` preview).
- Google OAuth will not work on the tunnel origin (client-ID allowlist) —
  username/password login is the demo path.
- `nginx.conf` still carries the localhost-only CSP header: the docker-frontend
  production image needs the same `VITE_CSP_EXTRA`-style treatment (entrypoint
  templating) before any real deployment. Tracked as follow-up, not done here.

## Gate status

**PASS (demo-grade)** — public URLs live and 5/5 e2e green through them at $0.
**NOT DONE**: durable hosting (needs AWS credentials + spend approval, or another
free-tier host with an account) and the nginx CSP header follow-up.
