# SafeCity — Full Build Prompt

> Copy everything below this line into a capable coding AI (or agent team). It is a complete,
> self-contained specification for rebuilding the SafeCity platform from zero, with the same
> feature set as the reference app plus stronger workflow, security, demo data, performance,
> UI craft, routing, and a production-grade Docker / Kubernetes / Terraform / AWS deployment.

---

## 0. ROLE & WORKING METHOD

You are a senior full-stack + platform engineer. Build the **entire** application in one
repository, working in phases, committing after each phase, and keeping every gate green at all
times. Do not stub, skip, or "TODO" anything that appears in this document.

Rules of engagement:

- Prefer working software over prose. Every phase ends with passing tests, not with a summary.
- Never commit secrets. All configuration comes from environment variables validated at boot.
- Every endpoint, model, and component named in this document must exist and behave as specified.
- If you must choose between two reasonable designs, pick the one that is easier to test, then
  document the choice in `docs/decisions.md`.
- Definition of Done for the whole build: `make verify` (defined in §13) passes on a clean clone.

---

## 1. PRODUCT SUMMARY

**SafeCity** is a civic incident-reporting platform: citizens report urban problems (potholes,
leaks, fires, garbage, hazards), the backend routes them to the right department, staff work them
through a governed status workflow under SLA, citizens track progress on a public map, and
administrators monitor everything through analytics, audit logs, and demo data tooling.

### 1.1 Personas & roles (enum `UserRole`)

| Role | Key |
|---|---|
| Citizen | `citizen` |
| Volunteer | `volunteer` |
| Department staff | `department_staff` |
| Emergency responder | `emergency_responder` |
| City administrator | `city_admin` |
| Superuser | `superuser` |

- **citizen** — report incidents, comment, attach evidence, confirm resolution, reopen, track own
  reports, manage consents/privacy, 2FA, sessions.
- **volunteer** — all citizen abilities + read-only view of verified/in-progress/resolved public
  incidents (field verification support, no workflow authority).
- **department_staff** — queue for their own department, review/verify/assign/resolve, internal
  notes, department analytics, CSV/PDF export.
- **emergency_responder** — works `assigned → in_progress → resolved`, may escalate from
  `in_progress`; sees high/critical/emergency incidents.
- **city_admin** — everything, all transitions (except where `superuser`-only is declared), user
  management, announcements, demo data, admin overview, audit logs.
- **superuser** — same as city_admin plus Django-admin and destructive operations.

Volunteers/citizens never receive workflow authority. Role checks are enforced on the **server**
for every mutation; the UI merely mirrors them.

### 1.2 Domain model (Django apps)

- `accounts` — `User` (UUID pk, email login, hashed password, role, department FK, phone, language,
  `prefers_anonymous_reporting`, `two_factor_enabled`, `two_factor_secret`,
  `two_factor_recovery_codes`, `failed_login_count`, `locked_until`, `email_verified_at`,
  `deleted_at`), `Department` (name, code, `is_emergency_department`, `is_active`),
  `ConsentRecord`, `DeletionRequest`, `SavedLocation`, `NotificationPreference`.
- `core` — `Zone`, `Ward` (zone FK, name, code, lat/lng), `SLAConfiguration` (severity →
  resolution hours, default low=120 / medium=72 / high=24 / critical=6), `SystemConfig`.
- `incidents` — `Incident`, `IncidentCategory` (name, slug, default_department, display_order,
  icon), `IncidentComment` (public vs `is_internal`, author, optional media),
  `IncidentMedia` (file, media_type image/video/document, mime, size, thumbnail, caption,
  `exif_stripped`, `scan_status pending|clean|infected|skipped`), `IncidentStatusHistory`
  (from, to, actor, note, is_public), `EscalationRule` (condition → auto-escalate + notify).
- `notifications` — `Notification` (recipient, verb, title, body, incident FK, `read_at`),
  preferences per channel.
- `announcements` — `Announcement` (title, body, `is_published`, publish/expiry windows, audience).
- `audit` — `AuditLog` (actor, action, object_type, object_id, changes JSON, ip, user_agent,
  request_id, created_at) written by a single `log_action()` helper used everywhere.
- `ai` — `AIRecommendation` (incident, kind `category|severity|summary|duplicate`, provider,
  output JSON, confidence, accepted/rejected by human).
- `analytics` — read-only aggregated endpoints (no separate model required).

`Incident` fields (minimum): UUID pk, `reference_number` (human-readable, unique, e.g.
`SC-2026-000123`), title, description, category FK, severity, urgency, status, ward FK,
department FK, reporter FK (nullable for anonymous), `is_anonymous`, `is_emergency`, latitude /
longitude (exact) + optional jittered public coordinates, address_public, address_internal,
assigned_staff FK, assigned_responder FK, `sla_deadline`, `sla_breached`, `is_overdue`,
`citizen_confirmed_resolution`, `resolution_summary`, `search_vector` (Postgres GIN),
timestamps `submitted_at / verified_at / assigned_at / resolved_at / closed_at / created_at /
updated_at / deleted_at` (soft delete).

### 1.3 Status enum (13 states)

`draft, submitted, under_review, verified, rejected, duplicate, assigned, in_progress,
awaiting_info, escalated, resolved, closed, reopened`

### 1.4 Workflow — canonical transition table (server-enforced)

Format: `from → { to: allowed roles }`. `"citizen"` means the reporter may perform it.

```
draft        → submitted            : citizen, city_admin, superuser
submitted    → under_review         : department_staff, city_admin, superuser
             → verified             : city_admin, superuser
             → rejected             : city_admin, superuser
             → duplicate            : city_admin, superuser
             → assigned             : department_staff, city_admin, superuser   (fast-track)
under_review → verified             : department_staff, city_admin, superuser
             → rejected             : department_staff, city_admin, superuser
             → duplicate            : city_admin, superuser
verified     → assigned             : department_staff, city_admin, superuser
assigned     → in_progress          : department_staff, city_admin, superuser, emergency_responder
             → awaiting_info        : department_staff, city_admin, superuser
             → reopened             : city_admin, superuser
in_progress  → awaiting_info        : department_staff, city_admin, superuser
             → resolved             : department_staff, city_admin, superuser, emergency_responder
             → escalated            : department_staff, city_admin, superuser, emergency_responder
             → assigned             : city_admin, superuser                     (reassign)
awaiting_info→ in_progress          : citizen, department_staff, city_admin, superuser
             → escalated            : city_admin, superuser
escalated    → in_progress          : department_staff, city_admin, superuser, emergency_responder
             → resolved             : department_staff, city_admin, superuser
resolved     → closed               : department_staff, city_admin, superuser
             → reopened             : citizen, city_admin, superuser
reopened     → in_progress          : department_staff, city_admin, superuser
             → assigned             : city_admin, superuser
rejected     → closed               : city_admin, superuser
duplicate    → closed               : city_admin, superuser
```

Hard rules:

1. Self-assignment forbidden: an authority may not assign an incident to themselves.
2. No-op transitions (from == to) return success without writing history.
3. Every successful transition atomically: stamps the matching timestamp
   (`verified_at/assigned_at/resolved_at/closed_at`), writes `IncidentStatusHistory`, writes an
   `AuditLog` entry, updates SLA flags (`sla_breached = sla_breached or is_overdue` when moving to
   `resolved/closed/rejected/duplicate`), and enqueues notifications (reporter + assigned staff +
   department members for escalation), all in one DB transaction.
4. Illegal or unauthorized transitions return **409** with
   `{"detail": "Transition <from> → <to> is not allowed for you.", "code": "invalid_transition"}`.
5. Frontend's action map must be a literal mirror of this table, filtered per role, so the user
   never sees a button the API would refuse.

### 1.5 SLA

- `sla_deadline = submitted_at + SLAConfiguration(resolution_hours for severity)`.
- `is_overdue` computed on read; `sla_breached` latched on close-type transitions.
- A Celery beat task every minute scans `sla_deadline < now() AND NOT sla_breached` → latches,
  notifies department + admins, and raises `EscalationRule` matches (age, severity, queue depth).
- Admin overview lists the top 10 open breached incidents.

---

## 2. FEATURE CHECKLIST (all mandatory)

### 2.1 Auth & account security

- [ ] Email+password registration with terms acceptance recorded as `ConsentRecord`.
- [ ] Login with brute-force lockout: after 5 consecutive failures lock 15 minutes (HTTP **423**
      with `code: account_locked`, countdown in message); counters reset on success; lock check
      happens *before* credential verification.
- [ ] JWT access (short, 5–15 min) + refresh (days) with **rotation and blacklisting**; refresh
      endpoint rotates and blacklists the old token; logout blacklists.
- [ ] **Two-factor (TOTP) with a challenge flow** — this exact protocol:
  1. `POST /api/v1/auth/token/` for a 2FA-enabled user returns
     `{"requires_2fa": true, "access": "<2-minute challenge JWT>", "user": {...}}` and **no
     refresh token** (and no usable access token).
  2. The challenge JWT carries a `2fa_pending: true` claim. A project-wide
     `StrictJWTAuthentication` (default auth class) **rejects** any token with that claim on every
     endpoint with 401 `code: 2fa_pending`.
  3. Only `POST /api/v1/auth/token/2fa/` opts into stock `JWTAuthentication` + `AllowAny`, accepts
     `{token}` (6-digit TOTP **or** 8-char recovery code), and on success returns a real
     `{access, refresh, user}`. Wrong code → 400; missing/expired challenge → 401.
  4. Recovery codes: 10 single-use codes, hashed (SHA-256 or better) at rest, consumed on use,
     regenerable while authenticated. TOTP setup stores the secret in session until the first
     valid code confirms, then persists it; QR/otpauth URI returned once.
- [ ] **OAuth 2.0 / OpenID Connect with Google (the ONLY identity provider)** — implement both
      entry points, sharing one account-linking + session-issuance service:

  **A. Server-side Authorization Code + PKCE (primary, recommended path)**
  - `GET /api/v1/auth/oauth/google/login/` → 302 to `https://accounts.google.com/o/oauth2/v2/auth`
    with `client_id`, `redirect_uri` (`{APP_URL}/auth/oauth/google/callback` — exact match
    registered in Google Cloud Console), `response_type=code`, `scope=openid email profile`,
    `state=<signed random nonce stored in a short-lived HttpOnly cookie>`, `code_challenge`
    (S256) + `code_challenge_method=S256`, `access_type=offline`, `prompt=select_account`,
    `nonce` in the ID token check.
  - `GET /api/v1/auth/oauth/google/callback/` (or the SPA route that forwards `code`+`state` to
    the API): validate `state` (timing-safe, single-use, ≤10 min), then
    `POST https://oauth2.googleapis.com/token` exchanging `code` + `client_secret` +
    `redirect_uri` + `code_verifier`. Exchange is server-side only — the client secret never
    reaches the browser.
  - Validate the resulting ID token: `iss` ∈ {`https://accounts.google.com`,
    `http://accounts.google.com`}, `aud` == our client ID (or `azp` for multi-audience),
    `exp`/`iat` sanity, `nonce` match, signature verified via Google JWKS
    (`https://www.googleapis.com/oauth2/v3/certs`) with **JWKS caching + `kid` rotation support**
    (do not hand-roll crypto — use a maintained library such as `google-auth`/`authlib`/`jose`).
  - **B. Google Identity Services (One Tap / button) front-end flow (secondary path)**: the SPA
    receives a Google `id_token`/`credential` and POSTs it to
    `POST /api/v1/auth/oauth/google/` (`{id_token}`); the server verifies signature + audience +
    expiry + nonce via the same JWKS path.

  **Account linking & provisioning rules (both paths):**
  - Normalize email lowercase; `email_verified` must be true, otherwise reject 401.
  - Existing account with the same email → **link** it (record `socialaccount` row with provider,
    `sub`, tokens) and log in *only if* the account already has a password or the email is
    Google-verified — never silently bypass 2FA: **if `two_factor_enabled` is true, issue the same
    2-minute `2fa_pending` challenge as password login** and require `POST /auth/token/2fa/`.
  - First sign-in → auto-provision a `citizen` account (marked `email_verified_at=now`,
    consent prompt on first use), audit `auth.oauth_registered`.
  - Deactivated/soft-deleted account → 403; Google account without email → 401.
  - Store only what is needed (`sub`, refresh token if scopes granted, expiry) encrypted at rest;
    never persist the raw ID token.
  - Refresh-token handling: if `access_type=offline` granted, rotate Google tokens server-side for
    future people-API calls (avatar, etc.); revoke on unlink.
  - `GET/DELETE /api/v1/auth/oauth/google/unlink/` — unlink only if a password is set (prevents
    lock-out); require recent auth (password or 2FA) to unlink.
  - Providers are config-driven (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`,
    `GOOGLE_OAUTH_ENABLED`); unknown/disabled provider → **503** `code: oauth_unconfigured`.
  - No other providers (no GitHub, no Facebook, no generic OIDC) — the code may be written to make
    adding one trivial, but only Google is enabled, tested, and documented.
  - Full test coverage: happy path both variants, `state` mismatch/CSRF, `code` replay, wrong
    `aud`, expired token, unverified email, 2FA-required Google login, unlink lock-out guard,
    disabled-provider 503.
- [ ] Password reset by emailed UID+token link (always 202, no user enumeration), confirm sets
      password and invalidates other sessions; change-password invalidates sessions.
- [ ] Session list + revoke (blacklisted refresh tokens) in the profile UI.
- [ ] Per-account audit trail: register, login, failed login, lockout, 2FA enable/disable,
      password reset/change, session revoke, role change.

### 2.2 Incident lifecycle

- [ ] Create (draft or submitted) with category, severity, urgency, location (map picker),
      anonymous toggle (respects `prefers_anonymous_reporting`), media upload (≤6 files, images
      get EXIF stripped, async virus scan hook setting `scan_status`, thumbnail generation).
- [ ] Public/anonymous incidents are hidden from anonymous API consumers until `verified`.
- [ ] Draft → submit; duplicate linking; reject with reason; verify; assign (department + optional
      staff/responder); request info; resume; escalate; resolve (requires `resolution_summary`);
      citizen confirm-or-reopen (reopen requires a comment); close.
- [ ] Comments: public and internal (`is_internal`), attachments, timeline view combining
      status history + comments + media.
- [ ] Reference numbers, copy-to-clipboard, deep linkable detail page.
- [ ] Exports: `GET /api/v1/incidents/export/csv/` (filtered, streaming, respects role scope) and
      `GET /api/v1/incidents/<id>/export/pdf/` (hand-rolled minimal PDF writer — **no new PDF
      dependency** — with incident summary, timeline and SLA block).
- [ ] Search: `q` across reference/title/description plus Postgres `search_vector` (GIN) with
      trigram fallback; filters `status` (multi), `severity`, `category`, `department`, `ward`,
      `created_after/before`, `overdue=true`, `sla_state=breached`, `emergency=true`.
- [ ] Object-level permission on every detail route (`can_view_incident`), soft delete for admins,
      GDPR-style deletion requests (auto-rejected while open incidents exist).

### 2.3 Public surfaces

- [ ] Public map: clusterized Leaflet map of verified incidents, category/severity/ward filters,
      read-only popups, ward boundaries.
- [ ] Track-by-reference page: status timeline + ETA, no auth required.
- [ ] Announcements list (published only) and admin composer with scheduling + audience.
- [ ] Public/landing pages: hero, how-it-works, live stats strip, CTA, footer, about page.

### 2.4 Authority surfaces

- [ ] Operations dashboard: KPI cards (open, overdue, emergency, avg response, avg resolution,
      SLA %), ward/department breakdown, recent activity.
- [ ] Queue: virtualized/paginated table with saved filters in the URL, bulk status actions,
      column sort, quick assign.
- [ ] Analytics: time-series (created vs resolved), top categories/wards/departments, severity
      mix, responder performance — all scoped by role (`department_staff` sees only their
      department; responders see assigned + high/critical/emergency).
- [ ] User management: list/search, role change (with department), unlock, deactivate.
- [ ] Admin overview endpoint: per-department open counts, pending deletion requests, recent
      audit entries, satisfaction, status/category/ward distributions, breached SLA list.
- [ ] Demo data admin UI: one click to seed/reset demo fixtures, visible progress, admin-only.

### 2.5 Realtime — WebSockets for **all** data (not just notifications)

- [ ] In-app notifications for every workflow event (list, unread count, mark read, mark all,
      per-type preferences) — REST CRUD plus live push over the socket below.
- [ ] Email channel for security events (lockout, password reset, 2FA changes, OAuth link/unlink)
      — console/locmem backend in dev, SES in prod.

- [ ] One authenticated WebSocket endpoint `ws://<host>/ws/v1/?token=<JWT>` (Django Channels +
      Redis channel layer) that is the **single realtime transport for the whole app**. Every
      read-model the UI displays can be pushed over it; REST remains the source of truth for
      first load, mutations, pagination, and reconnect catch-up.
- [ ] **Connection lifecycle**: JWT verified on connect (same `StrictJWTAuthentication` rules —
      `2fa_pending` challenge tokens are rejected); user bound to per-user + per-role group(s);
      server sends `{"type":"hello","server_time":...,"user":{...}}`; heartbeat
      `ping`/`pong` every 25 s with a 60 s liveness timeout; clean `bye` + code 1000 on logout;
      max connections per user (e.g. 5) with oldest-closed policy; per-connection message rate
      limit and max payload size.
- [ ] **Subscription model (client → server)**:
  `{"type":"subscribe","topics":["incident:<id>","queue:dept:roads","feed:all","user:me",
  "notifications:me","analytics:ops"]}` and `unsubscribe`. The server **authorizes every topic**
  against the same RBAC/scope rules as REST (a citizen may only subscribe to their own incidents
  + public verified topics; staff to their department's queue/analytics; admins to everything) —
      subscribing to an unauthorized topic returns
      `{"type":"error","code":"forbidden","topic":...}` and never leaks data.
- [ ] **Server → client envelope** for every event:
  `{"type":"<event>","topic":"<topic>","seq":<monotonic int per connection>","ts":"<iso8601>",
  "data":<payload>,"meta":{"request_id":"...","actor":{...}}}` with event types at minimum:
  `incident.created`, `incident.updated`, `incident.status_changed` (with `from`/`to`/actor/note),
  `incident.assigned`, `incident.comment_added`, `incident.media_added`, `incident.sla_warning`
  (at 75%/100% of deadline), `incident.sla_breached`, `incident.escalated`,
  `notification.new`, `announcement.published`, `queue.updated` (counts/badges),
  `analytics.tick` (KPI deltas), `presence.update`, `demo_data.progress`.
- [ ] **Every data change made through REST is broadcast** from a single
      `emit(event, topic, data)` helper called inside the same transaction (`transaction.on_commit`
      so rolled-back/never-committed changes are never broadcast). No view may forget to emit:
      add a test that walks each mutating endpoint and asserts a broadcast arrives on a
      subscribed socket.
- [ ] **Live UI**: a small typed client (`services/realtime.ts`) with auto-reconnect
      (exponential backoff + jitter), topic resubscription on reconnect, `seq` gap detection →
      targeted REST refetch, and a visible "live/offline" indicator. React Query integration:
      incoming events `setQueryData`/invalidate the matching keys instead of bespoke state, so
      the feed, detail page, queue, dashboards and notification bell all update **without a page
      reload** (optimistic mutations still reconcile with the broadcast).
- [ ] **Presence**: authority statuses (online/idle) visible to their department; optional
      per-incident "3 staff are viewing".
- [ ] **Scale/safety**: fan-out through Redis pub/sub groups (not per-row socket sends), coalesce
      high-frequency updates (typing/queue ticks) to ≤4 msg/s per topic, drop stale payloads by
      `seq`, backpressure handling, and a documented `ws` → REST fallback when the socket is
      unavailable (the app must be fully functional with WebSockets blocked by a proxy).
- [ ] Tests: auth handshake (valid/expired/challenge token), topic authorization matrix,
      event → React Query cache update, reconnect/resubscribe + `seq` gap refetch, rate limiting,
      transaction rollback produces **no** broadcast.

### 2.6 Social feed — scroll-through of incidents with images

The primary way citizens *browse* the city's activity: an infinite, image-forward feed that feels
like a modern social app, while still being an incident tracker.

- [ ] **Route** `/feed` (auth, first entry in the sidebar/nav) and **`/feed/:id`** — a deep-linkable
      full-view of one incident (browser back returns to the exact scroll position).
- [ ] **Endpoint** `GET /api/v1/incidents/feed/?cursor=&category=&severity=&ward=&near=lat,lng`
      returning pages of **role-scoped, verified-and-above** incidents shaped for the feed:
      `id, reference_number, title, media[] (thumbnails + full), category {slug,name,icon,color},
      severity, status, ward, distance_m?, author_public_name|anonymous, created_at, time_ago,
      comment_count, reaction_count, has_confirmed, is_bookmarked, realtime_ref` — no internal
      fields (never `department` notes, addresses, SLA internals, or reporter PII).
      Cursor pagination (opaque `created_at,id` cursor), page size 10, stable ordering
      `-created_at`, `?mode=nearby|newest|trending` (trending = comments+reactions velocity in
      the last 24 h, computed in SQL).
- [ ] **Card design (image-first)**: edge-to-edge media (16:9 hero, swipeable carousel for
      multiple images/video poster), author + relative time + ward chip overlay, title and 2-line
      clamped description, status/severity pills, like/save/comment counts, tap → detail; video
      uses `preload="none"` poster + click-to-play.
- [ ] **Infinite scroll**: TanStack Query `useInfiniteQuery` + `IntersectionObserver` sentinel,
      skeleton card placeholders that match final layout, "end of feed" state, filters reflected in
      the URL (`/feed?category=road-damage&mode=nearby`), pull-to-refresh on mobile.
- [ ] **Live feed**: subscribed to the `feed:<scope>` topic — new incidents insert at the top with
      a soft "12 new posts — refresh" pill (never yank scroll position), status/comment/reaction
      counts on visible cards update in place, deleted/hidden incidents fade out.
- [ ] **Interactions**: like/save (optimistic + rollback), follow a category/ward, report
      (create) launched from a floating action button with image picker, share (copy link),
      "report this post" moderation flag. Reactions/comments are themselves streamed live on the
      detail view (`incident:<id>` topic).
- [ ] **Media pipeline**: feed serves responsive variants (`thumb 320w`, `card 800w`, `full`) via
      signed short-lived URLs, `srcset`/`sizes`, `loading="lazy"` + `decoding="async"`,
      blurhash/LQIP placeholder while loading, EXIF stripped before storage, AV scan gate
      (`scan_status != clean` → never appears in the feed).
- [ ] **Performance**: first 10 cards LCP < 2.5 s on a mid-range phone, feed query ≤ 10 SQL
      queries (no N+1 — one query for incidents, one for media, one for counts/reactions),
      images served from S3/CloudFront (not through Django), feed endpoint cached with
      stale-while-revalidate and invalidated on `incident.created`.
- [ ] **Safety**: anonymous posts show no identity; blocked/muted categories respected; adult/
      sensitive content flag hides media behind a tap-to-reveal; the feed never exposes
      `is_internal` comments or unverified reports; every card's detail link enforces the same
      `can_view_incident` rules.
- [ ] Tests: feed scoping per role, cursor pagination stability (no dupes/skips when new items
      arrive), media eligibility (unscanned/quarantined excluded), realtime insert pill,
      optimistic like rollback, `/feed/:id` deep link + scroll restoration.

### 2.7 AI advisory (strictly optional and non-authoritative)

- [ ] Provider interface: `MockAIProvider` (default, deterministic keyword/token heuristics, zero
      network) and `OpenAICompatibleProvider` (only when `OPENAI_API_KEY` set).
- [ ] Suggestions: category, severity, one-sentence summary, duplicate candidates
      (token-set similarity > 0.45 → candidate list).
- [ ] **Word-boundary matching only** (no substring false positives: `dog` must not match
      `hotdog`, `wire` must not match `airwire`); score = matched keyword weight, confidence
      capped and calibrated (`0.35 + 0.15·hits`, max 0.95).
- [ ] Every call PII-scrubbed first (phones, emails, national IDs, vehicle IDs) and persisted as
      `AIRecommendation` with provider + confidence; a human must accept before anything applies.
- [ ] AI never changes status, severity, or assignment by itself.

---

## 3. SECURITY REQUIREMENTS (non-negotiable)

1. **AuthN/AuthZ**: single default `StrictJWTAuthentication`; per-object permission checks on
   every detail route; role/department scoping applied inside `get_queryset()` (never in the UI
   only); 403 vs 404 chosen to avoid leaking existence.
2. **Throttling**: DRF scopes — `auth` scope on register/login/reset, burst limits on incident
   create and comment, IP-based anonymous limits on public endpoints.
3. **Headers & cookies**: Django `SecurityMiddleware` with HSTS, `SECURE_SSL_REDIRECT` (prod),
   `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `X-Content-Type-Options`, `Referrer-Policy`,
   strict **CSP** (no `unsafe-inline`; hashes/nonces for the SPA), `Permissions-Policy`,
   frame-ancestors none.
4. **Validation**: zod schemas + react-hook-form on the client; DRF serializers with explicit
   field-level validators on the server; never trust client-provided role, department,
   `sla_deadline`, `is_overdue`, or reference number.
5. **Uploads**: extension+MIME sniffing, size cap, randomized storage keys, private bucket,
   short-lived signed GET URLs, async AV scan with `infected` quarantine and per-user quota.
6. **Rate limiting & abuse**: login lockout (§2.1), per-user write limits, WebSocket message
   rate limit, comment length caps.
7. **Audit**: every mutation writes `AuditLog` (actor, action, object, diff, ip, request_id) via
   one helper; audit log is append-only and admin-only to read; audit queries indexed by
   `(actor, -created_at)` and `(object_type, object_id)`.
8. **Secrets**: everything from env / AWS Secrets Manager / Kubernetes Secrets; `.env.example`
   documents names only; no secret in git history; pre-commit secret scan (gitleaks).
9. **Privacy**: anonymous reporting strips reporter from public serializers; public coordinates
   support optional jitter (`jitter_location` guard, default off for authorities);
   PII scrubbing before any external AI call; data export/delete flows.
10. **Dependencies & CI gates**: `pip-audit` / `npm audit --audit-level=high` in CI; Docker images
    non-root, read-only rootfs where possible, pinned digests; no `latest` tags.
11. **OWASP checklist**: CSRF, XSS (React escaping + CSP), SQLi (ORM only), IDOR, mass assignment
    (explicit `fields`), broken auth, security misconfiguration (`DEBUG=False`, allowed hosts),
    sensitive data exposure, CSRF on state-changing GETs (never), insufficient logging.

---

## 4. DEMO DATA (rich, idempotent, reproducible)

`python manage.py seed_demo_data` must be **idempotent and self-healing**:

- 8 departments (Roads & Infrastructure, Water, Fire Services [emergency], Solid Waste,
  Electricity, Health Services [emergency], Law & Order, Disaster Management [emergency]).
- 3 zones × 4 wards with real-ish coordinates.
- ≥12 categories mapped to default departments with icons.
- SLA configurations for all 4 severities.
- Users: `admin@safecity.local / Admin@12345!` (city_admin), `citizen1..8@safecity.local /
  Citizen@12345!` (**role `citizen` — verify and repair existing rows**), `staff1..8` per
  department (`Staff@12345!`), `responder@` , `volunteer@`, `super@` (superuser).
  Re-seeding **must update** role/department/name of existing users (use `update_or_create`
  semantics — a stale wrong role is a bug).
- ≥250 incidents spread over the last 120 days, across every status (including at least 5 in each
  of draft/under_review/awaiting_info/escalated/reopened/duplicate/rejected), all severities,
  10% emergencies, realistic titles/descriptions from templates, geographically distributed
  across wards, with status history + comments + media for a **feed-ready ≥60% of incidents**
  (1–3 images each, varied aspect ratios, some multi-image and one video), SLA breaches
  on a believable fraction, citizen confirmations on some resolved ones, and like/save/comment
  counts populated so trending mode has data.
- Announcements (2 published, 1 scheduled), notifications for each user, audit log entries,
  escalation rules, AI recommendations for a subset.
- Deterministic (`--seed 42` style) so screenshots and tests are stable.
- A `reset_demo_data` command that purges and reseeds (dev only, guarded by an env flag).

---

## 5. PERFORMANCE & OPTIMIZATION

**Backend**

- Composite indexes for every hot query, declared on the model and verified with `EXPLAIN ANALYZE`:
  `(status, -created_at)`, `(reporter, -created_at)`, `(department, status, -created_at)`,
  `(sla_breached, sla_deadline)`, `(is_emergency, status)`, `(created_at)` for analytics ranges,
  `(recipient, read_at)` notifications, `(actor, -created_at)` audit, `(object_type, object_id)`,
  GIN on `search_vector`.
- Zero N+1: `select_related` the incident's category/department/ward/staff/responder;
  `prefetch_related` comments, media, history in serializers; assert with
  `django.test.utils.CaptureQueriesContext` in tests (budget: list endpoint ≤ 25 queries).
- Pagination everywhere (cursor or page/limit with `count` only when needed), `HEAD`-cheap list
  responses, `only()`/`defer()` on list serializers.
- Redis caching for reference data (wards, categories, departments) with explicit invalidation;
  `cache_page` on public stats; analytics endpoints cached per role scope with short TTL.
- Celery for anything >200 ms: media processing, notification fan-out, email, exports >5k rows,
  SLA scan, analytics rollups.
- Streaming/iterator for CSV export; DB-level aggregation for analytics (never Python loops).
- DB connection pooling (`CONN_MAX_AGE` / pgBouncer in k8s), proper transaction boundaries
  (`select_for_update` only where contended).

**Frontend**

- Route-level `React.lazy` + `Suspense` for every page; manual vendor chunking; bundle budget
  enforced in CI (initial JS gzip ≤ 250 kB, warn at 200 kB).
- TanStack Query with sensible `staleTime`, key design (`["incident", id]`, `["incidents", filters]`),
  invalidation on mutation, infinite/placeholder data for tables.
- Virtualize the queue table (>200 rows), debounce filters, memoize derived data, avoid inline
  object/function props in lists.
- Images: thumbnails from the backend, lazy loading, `content-visibility`.
- Maps: cluster heavy layers, defer tile loads until visible.
- No unnecessary re-renders: stable callbacks, zustand selectors, WebSocket payloads normalized.

---

## 6. UI/DESIGN — "designed by a human, not generated"

Goal: a credible civic product that never reads as AI boilerplate. No purple/blue gradient hero
with two buttons, no uniform grid of identical rounded cards with emoji icons, no Lorem, no
default Tailwind look.

1. **Tokens first** (`styles/tokens.css` + Tailwind theme): a restrained palette built around a
   single civic hue (e.g. deep teal/green `#0F766E` family) with a warm neutral scale
   (`stone`-like, not pure grey), semantic colors (`success`, `warning`, `danger`, `info`) with
   light/dark variants, a type scale (12/14/16/20/24/30/38/48), a 4-pt spacing scale, radii
   (4/6/8/12/full), 3 shadow levels (never the default `shadow-md` everywhere), and motion
   tokens (120/180/260 ms, `cubic-bezier(.2,.8,.2,1)`).
2. **Typography**: system-ui stack plus one distinctive display face for headings (self-hosted,
   subset), tabular numerals for all metrics, `max-w-[68ch]` for prose, uppercase micro-labels
   with `tracking-wider` for table headers and chips.
3. **Layout system**: app shell with a collapsible icon+label sidebar, a slim top bar with global
   command palette (`⌘K`), breadcrumb on detail pages, content max-width 1440 px, 12-col grid with
   deliberate asymmetry on dashboards (KPI row → 2/3 + 1/3 chart split → full-width table).
4. **Density & craft**: tables with sticky headers, zebra-free hover rows, right-aligned numerics,
   inline status chips with dot + text (never color alone), avatars with initials, keyboard
   navigation, focus rings (`ring-2 ring-offset-2`), 44 px touch targets.
5. **Every state is designed**: skeleton loaders that match final layout (not spinners), empty
   states with an illustration + primary action, error states with retry, optimistic mutations
   with rollback toasts, inline field errors, disabled/loading button labels.
6. **Charts**: hand-styled (no default recharts look) — thin strokes, direct labels, subtle
   gridlines, one accent + one comparison color, no 3D, no rainbow legends, empty state text.
7. **Map**: muted basemap (Carto light/dark), custom SVG markers per category, cluster counts,
   slide-over details panel instead of tiny popups.
8. **Feed**: image-first cards with real photography of the reported problem (not stock heroes),
   consistent media aspect ratios, overlay chips that stay legible on any image (backdrop blur +
   gradient scrim), carousel dots, and skeletons that hold the exact card geometry while images
   stream in — it should feel like a civic Instagram, not a Bootstrap image list.
9. **Dark mode**: system + manual toggle, persisted, no FOUC (inline bootstrap script), all
   tokens defined for both schemes, charts re-themed.
10. **Accessibility**: WCAG 2.1 AA contrast, semantic landmarks, labelled controls, `aria-live`
   for toasts, full keyboard path through workflow dialogs, reduced-motion respect.
11. **Voice**: real civic copy everywhere ("Report a pothole", "Roads & Infrastructure is
    reviewing your report"), human date formatting, pluralization, no "Lorem" or "TODO".
12. Responsive from 360 px: sidebar → bottom nav on mobile, tables → card lists, map fullscreen,
    feed single-column with full-bleed media.

Use a headless component layer (Radix) + Tailwind + CVA for variants; keep primitives in
`components/ui/*` (button, input, select, dialog, dropdown, tabs, tooltip, toast, table, badge,
card, skeleton, empty-state) and feature components in `components/<domain>/`.

---

## 7. ROUTING

### 7.1 Frontend (React Router, data-router)

```
/                      Landing (public layout)
/about                 About
/map                   Public map
/track                 Track by reference (?ref=)
/announcements         Public announcements
/login                 Login (incl. inline 2FA step)
/register              Register
/forgot-password       Request reset
/reset-password        Confirm reset (?uid&token)
/2fa/setup             2FA enrollment (auth)
/2fa/verify            Standalone 2FA challenge (needs challenge token, else redirect /login)
/dashboard             Citizen dashboard (auth)
/feed                  Social incident feed — infinite scroll, image-first (auth)
/feed/:id              Single incident in feed view; back restores scroll position (auth)
/incidents             My incidents (auth) — filters in URL query string
/report                Create incident (role: citizen, staff, admin, superuser)
/incidents/:id         Incident detail (auth) — tabs: overview | timeline | media
/notifications         Notifications (auth)
/profile               Profile / security / sessions / 2FA / consents (auth)
/operations            Authority dashboard (staff, responder, admin, superuser)
/queue                 Incident queue (same roles)
/analytics             Analytics (staff, admin, superuser)
/admin                 Admin overview (admin, superuser)
/admin/users           User management (admin, superuser)
/admin/announcements   Announcement composer (admin, superuser)
/admin/audit           Audit log (admin, superuser)
/admin/demo-data       Demo data seeding (admin, superuser)
*                      404 page (designed, with search + links)
```

Rules: `<RequireAuth>` redirects to `/login` preserving `state.from`; `<RequireRole>` redirects
home on mismatch; guards read a **single** auth source (token store + zustand session, hydrated
from `/auth/me/`), never raw `localStorage` scattered across files; every list page keeps its
filters/sort/page in the URL so views are shareable; route transitions animated with a shared
`PageShell`; code splitting per route; scroll restoration; a global error boundary per layout.

### 7.2 Backend API (`/api/v1/`, documented with drf-spectacular)

Realtime lives on a parallel WebSocket route `ws/v1/` (Channels): `ws/v1/?token=<JWT>` with the
subscribe/unsubscribe protocol specified in §2.5 — it mirrors REST permissions exactly and is
documented in the same OpenAPI description.

Conventions: plural nouns, nested only one level, `?page=&page_size=` (or cursor), envelope
`{count, next, previous, results}` for lists, single JSON object otherwise, errors always
`{"detail", "code"?}` or `{"field": ["msgs"]}`, `Location` header on 201, `204` on delete,
`ETag`/`If-Match` optional on detail.

```
/auth/            register, token, token/2fa, token/refresh, token/verify, logout, me,
                  oauth/google, password/reset, password/reset/confirm, password/change,
                  sessions/, sessions/<id>/, 2fa/setup, 2fa/disable, 2fa/recovery/regenerate
/users/           list (role/department filters), <id>/role/, <id>/unlock/, <id>/
/profile/         consents, saved-locations, notification-preferences, deletion-requests
/incidents/       CRUD (create/list/retrieve), feed/, <id>/status/, <id>/assign/,
                  <id>/escalate/, <id>/resolve/, <id>/reopen/, <id>/confirm/, <id>/comments/,
                  <id>/media/, <id>/timeline/, <id>/ai-suggestions/, export/csv/,
                  <id>/export/pdf/, <id>/react/ (like/save), <id>/bookmark/
/incidents/media/ moderation list
/departments/     CRUD + members + open-count
/wards/  /categories/  /zones/   public reference data (cached)
/notifications/   list, <id>/read/, read-all/
/announcements/   public list + admin CRUD
/analytics/       overview, timeseries, breakdowns, performance
/audit-logs/      filtered, paginated (admin)
/ai/              recommend, accept/reject, duplicates
/admin/overview/  admin dashboard payload
/health/  /readiness/  /meta/config/  /schema/ (+ /schema/swagger/ /schema/redoc/)
```

URL ordering matters: literal subroutes (`incidents/export/csv/`) before router patterns whose
`pk` regex would swallow them; keep all `api/v1/` includes grouped and below generic paths so no
anonymous route sits above them.

---

## 8. TECHNOLOGY STACK (pinned major versions)

**Backend**: Python 3.12, Django 5.x, Django REST Framework, drf-spectacular (OpenAPI),
djangorestframework-simplejwt (blacklist), Django Channels + Daphne (WebSocket), Celery + beat,
psycopg 3, Redis, Pillow (+ optional python-magic), requests (OpenAI adapter), whitenoise (static),
pytest + pytest-django + pytest-cov + factory_boy, ruff, mypy (optional), django-environ.

**Frontend**: TypeScript 5 (strict), React 18, Vite 5, React Router 6 (data router), TanStack
Query 5, zustand 4, react-hook-form + zod, axios (interceptors for auth/refresh), Tailwind CSS 3 +
CVA + Radix UI, sonner (toast), recharts, Leaflet + react-leaflet + markercluster,
socket.io-client or native WebSocket, vitest + @testing-library/react + jsdom, Playwright (e2e),
ESLint (`--max-warnings 0`) + Prettier, `tsc -b --noEmit` gate.

**Data/infra**: PostgreSQL 16, Redis 7, MinIO (dev S3), Docker multi-stage images,
docker-compose for dev (`db`, `redis`, `minio`, `backend`, `celery`, `celery-beat`, `frontend`)
with healthchecks + `depends_on: condition: service_healthy`, plus `docker-compose.prod.yml`.

---

## 9. INFRASTRUCTURE — Docker, Kubernetes, Terraform, AWS

### 9.1 Containers

- `backend.Dockerfile`: multi-stage (deps → build wheels → slim runtime), non-root user, healthcheck
  hitting `/api/health/`, `gunicorn`/`uvicorn` in prod, Daphne only for dev, `entrypoint.sh` that
  waits for DB, runs migrations, collects static, then execs the app.
- `frontend.Dockerfile`: `node` build stage → nginx (or `nginx-unprivileged`) serving `dist` with
  SPA fallback, gzip/brotli, hashed asset caching, security headers, `/api` reverse proxy.
- Images tagged `repo:git-sha`; built for `linux/amd64`.

### 9.2 Terraform (`infrastructure/terraform`)

Roots per environment (`environments/dev|staging|prod`), reusable modules:

- `network` — VPC, 3 AZ public/private subnets, IGW, NAT (single in dev), route tables, VPC
  endpoints (S3, ECR, Secrets Manager, CloudWatch Logs), flow logs.
- `eks` — cluster, managed node groups (system + app, mixed spot/on-demand in prod), IRSA OIDC,
  aws-auth/Access Entries, cluster autoscaler or Karpenter annotations, encryption at rest.
- `rds` — PostgreSQL: Multi-AZ in prod, encrypted, parameter group, 7-day retention, subnet +
  security group, Secrets Manager-managed credentials, `auto_minor_version_upgrade`.
- `elasticache` — Redis: private, auth token from Secrets Manager, encrypted at rest/transit.
- `s3` — media bucket (private, versioned, SSE-KMS, lifecycle to IA/Glare), assets bucket (public
  via CloudFront in prod), CORS, bucket policies least-privilege.
- `ecr` — repositories with lifecycle policies, scan-on-push.
- `alb` — ALB + target groups + HTTPS listener (ACM cert), HTTP→HTTPS redirect, access logs.
- `iam` — IRSA roles (`safecity-backend`, `safecity-media-worker`), node role least-privilege.
- `secrets` — AWS Secrets Manager entries + replication; values written once via CI, never in TF state
  (use `value_wo`/external secrets or mark sensitive).
- `cloudwatch` — log groups (retention), metric alarms (5xx, latency, CPU, RDS CPU/connections,
  Redis evictions), SNS topic for alarms.

State: S3 backend with DynamoDB locking (`backend.tf.example` documents it). `terraform fmt`,
`tflint`, `checkov`/`tfsec` in CI; `plan` on PR, `apply` on merge to main with manual approval for prod.

### 9.3 Kubernetes (`infrastructure/kubernetes` + Helm chart)

- **Base** manifests + **Kustomize overlays** (`dev`, `staging`, `production`) *or* a Helm chart
  `safecity` with `values-{dev,staging,prod}.yaml` — provide both a raw-manifest path and a chart.
- Workloads: `backend` (Deployment, ≥2 replicas, probes `/api/health/` + `/api/readiness/`,
  resource requests/limits, rolling update, PDB), `celery-worker` (Deployment, concurrency-tuned),
  `celery-beat` (single replica), `frontend` (nginx Deployment), `migrations` (Job/hook running
  before rollout, `backoffLimit: 0`), optional `socket` deployment.
- Autoscaling: HPA on CPU + custom metric (queue depth), KEDA ScaledObject for celery workers.
- Networking: Ingress (ALB or nginx) with TLS (cert-manager / ACM), HTTP→HTTPS, rewrite rules,
  rate-limit annotations; `NetworkPolicy` default-deny + allow backend→db/redis only; backend
  service ClusterIP only.
- Config/Secrets: `ConfigMap` for non-secret env, External Secrets Operator or CSI/Secrets Manager
  sync for credentials; per-environment overlays patch replicas/images/resources.
- Ops: PodDisruptionBudgets, topology-spread constraints, node selectors/taints, seccomp
  `RuntimeDefault`, read-only root filesystem with `emptyDir` for tmp, drop ALL capabilities,
  `startupProbe` for slow boots.
- Observability: Prometheus ServiceMonitors + Grafana dashboards, Loki/Fluent Bit log shipping,
  OpenTelemetry traces (OTel sidecar/agent) exported to AWS X-Ray or ADOT collector, structured
  JSON logs with `request_id` correlation.
- Migrations, backups (pg_dump CronJob + RDS automated backups), and a documented restore drill.

### 9.4 CI/CD (GitHub Actions, `.github/workflows`)

- `ci.yml` (PR): backend `ruff`, `pytest --cov` (fail <80% on services), `pip-audit`; frontend
  `typecheck`, `lint --max-warnings 0`, `vitest --run`, `build`, bundle-size check; `terraform
  fmt/validate/tflint/checkov`; `hadolint`; `kubeconform` on manifests; Playwright e2e against
  docker-compose; gitleaks.
- `deploy.yml` (main): build+push images (multi-arch), `terraform plan` → apply per env, image
  tag bump in overlay, `kustomize build | kubectl apply` or `helm upgrade --atomic`, run
  migration job, smoke test (`/api/health/`, login, create incident), automatic rollback on
  failed smoke test.
- Environments: `dev` (auto), `staging` (auto), `prod` (manual approval).

---

## 10. TESTING STRATEGY

- **Unit**: services (workflow table exhaustively — every legal and illegal transition × every
  role), SLA math, TOTP/recovery codes, PII scrubber, keyword matcher, serializers.
- **API**: pytest + DRF client for every endpoint happy/sad path, role matrix tests, permission
  tests (anonymous, wrong role, cross-department), 2FA challenge protocol, throttling/lockout,
  export CSV/PDF, public visibility rules.
- **Regression**: named tests for each historical bug (media route shadowing by router `pk` regex,
  recovery-code length validation, seed role repair, no-refresh-before-2FA, self-assignment).
- **Query budget**: `assertNumQueries` on list endpoints; a test asserting the N+1 guards
  (`select_related`/`prefetch_related`) stay in place.
- **Frontend**: vitest + Testing Library for components and critical flows (login incl. 2FA step,
  create incident, workflow actions per role, feed scroll/live insert/optimistic like, toasts);
  Playwright e2e: register → login → report → staff verify → assign → resolve → citizen confirm →
  export CSV/PDF, plus a feed journey (scroll, open post, live comment arrives over WebSocket) and
  admin seed demo data.
- **Infra**: `terraform validate`, `checkov`, `kubeconform`, helm lint; optional `terratest` for VPC.
- All gates in `make verify`.

---

## 11. PHASED EXECUTION PLAN

1. **Scaffold** — repo layout (`backend/`, `frontend/`, `infrastructure/`, `docs/`, `scripts/`),
   venvs, pre-commit, lint/test configs, Dockerfiles, compose dev stack, `.env.example`, CI stub,
   Makefile. Gate: empty app boots, `/api/health/` 200, `typecheck`/`lint` pass.
2. **Domain + auth** — models/migrations/indexes, custom user, JWT + lockout + 2FA challenge flow,
   consents, sessions, audit helper, seed command v1. Gate: auth test suite green.
3. **Incidents core** — CRUD, workflow service + transition table, SLA, comments, media, timeline,
   exports, permissions, search/filter, notifications (DB), audit on every mutation, feed endpoint
   (`/incidents/feed/`) and the `emit()` realtime hooks (§2.5–2.6). Gate: workflow
   matrix + permission tests green, query budgets met.
4. **Reference + public surfaces** — wards/categories/departments, public map, track page,
   announcements, health/readiness/meta, OpenAPI schema complete.
5. **Authority + analytics + AI** — dashboards, queue, analytics endpoints, admin overview, user
   management, audit UI, AI provider + advisory flow, escalation rules + Celery beat.
6. **Frontend** — design tokens + primitives → layouts/routing/guards → citizen flows → social
   feed (`/feed` infinite scroll, live inserts, media carousel) → realtime client integration
   (React Query + WebSocket) → authority flows → admin flows → maps/charts/dark mode/a11y pass.
   Gate: typecheck 0, lint 0, vitest green, Playwright e2e green, bundle budget met.
7. **Hardening** — headers/CSP, throttles, upload security, secret scanning, dependency audit,
   load test (locust) on list endpoints, EXPLAIN ANALYZE review, cache tuning.
8. **Demo data & docs** — rich idempotent seed (§4), README quickstart, architecture diagram,
   API docs from OpenAPI, runbook (`docs/ops.md`), ADRs, SECURITY.md.
9. **Infra** — Docker hardening, Terraform modules + dev apply, K8s base/overlays + Helm, CI/CD
   pipelines, observability, backups, staging apply, prod plan with approval.

---

## 12. ACCEPTANCE CRITERIA (verify before declaring done)

- [ ] `docker compose up` from a clean clone yields a working app in ≤5 minutes with seeded data.
- [ ] Every persona can complete their full journey end-to-end (see §10 e2e).
- [ ] Workflow matches §1.4 exactly — tested for every role.
- [ ] 2FA challenge protocol (§2.1) works with **no refresh token before the second factor**, and
      recovery codes are accepted (length validation permits them).
- [ ] No endpoint returns another role's scoped data; anonymous users see only verified public data.
- [ ] List endpoints ≤25 queries; `EXPLAIN ANALYZE` shows index usage on status/SLA/reporter scans.
- [ ] `pytest` 100% green, coverage ≥80% on services, `tsc --noEmit` 0, `eslint --max-warnings 0` 0,
      `vitest` green, `ruff check` 0, bundle budget enforced.
- [ ] Terraform `plan` clean, `checkov` no high findings, manifests pass `kubeconform`, Helm chart
      installs into a kind/minikube cluster and serves the app.
- [ ] Demo seed is idempotent and repairs wrong roles; re-running twice produces identical data.
- [ ] WebSocket `ws/v1/` connects with the JWT, rejects `2fa_pending` challenge tokens, authorizes
      every subscription against the REST RBAC rules, and every mutating REST endpoint broadcasts
      a corresponding event (proven by test).
- [ ] The UI is fully usable with WebSockets unavailable (REST polling fallback) — no data
      disappears, only the "live" indicator changes.
- [ ] `/feed` renders an image-first infinite scroll of role-scoped, scan-clean incidents, updates
      live without reload, preserves scroll on back-navigation, and its endpoint stays ≤10 queries.
- [ ] UI passes a design review against §6 (no generic AI look, all states designed, dark mode,
      a11y AA, responsive to 360 px).
- [ ] Security checklist §3 fully implemented and smoke-tested (lockout, CSP headers, signed media
      URLs, RBAC matrix, audit entries for every mutation).

---

## 13. REPOSITORY COMMANDS (Makefile)

```
make bootstrap     # install everything, copy .env.example, build images
make dev           # docker compose up dev stack
make backend-shell / make frontend-dev / make celery-worker
make migrate / make seed / make reset-demo
make test-backend  # pytest -q --cov
make test-frontend # vitest --run
make test-e2e      # playwright
make typecheck / make lint / make fmt
make verify        # typecheck + lint + test-backend + test-frontend + ruff + build
make infra-plan ENV=dev / make deploy ENV=staging
```

Build it in the order above, keep `make verify` green after every phase, and finish with a short
`docs/build-report.md` listing what was implemented, measured performance numbers, and any
deviations from this prompt with justification.
