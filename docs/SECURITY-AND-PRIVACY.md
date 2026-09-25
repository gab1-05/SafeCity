# SafeCity — Security, Privacy, and Governance

This document states what SafeCity **actually enforces today**, distinguishes it from what
the architecture proposes, and records the deviations in
[§7 Deviations](#7-deviations-from-the-architecture-proposal).

SafeCity handles reports that routinely reveal where a person lives and, in the case of
safety hazards, what they observed. A leak is not an abstract risk, so privacy controls
are treated as correctness requirements, not extras.

---

## 1. Threat model

### Assets

| Asset | Why it matters |
|-------|----------------|
| Reporter identity and contact details | Exposure can deter reporting or enable retaliation |
| Precise residential coordinates | Enables locating a specific person |
| Internal authority notes | Candid operational discussion not meant for public view |
| Credentials and tokens | Account takeover, impersonation of officials |
| Audit trail | The evidence base for accountability; worthless if mutable |
| Uploaded media | Often contains faces, number plates, and EXIF geolocation |
| Administrative capability | Ability to reconfigure SLA, roles, and visibility |

### Adversaries and abuse cases

| # | Adversary | Abuse case | Primary controls |
|---|-----------|-----------|------------------|
| T1 | Anonymous internet user | Mass fake reports to bury real ones | `anon` and `incident_create` throttles, duplicate detection, verification gate before work is assigned |
| T2 | Curious authenticated user | Enumerate incidents to find a neighbour's report | UUID PKs, role-scoped querysets, 404 (not 403) for objects the caller cannot see |
| T3 | Privilege-seeking user | Escalate their own role | Role changes restricted to `city_admin`/`superuser`; role is not settable by self-registration |
| T4 | Credential thief | Replay a stolen token | 15-minute access TTL, refresh rotation with blacklist, session listing and revocation |
| T5 | Brute-force attacker | Guess passwords | `auth` throttle, failed-login counter, lockout with expiry |
| T6 | Malicious uploader | Smuggle malware or a polyglot file | Extension + MIME + size validation, Pillow verification, scan-status field with provider interface, EXIF stripping |
| T7 | Data scraper | Harvest exact locations from public pages | Coordinate jitter ≥ 150 m, unguessable public tokens, PII-stripping serializers |
| T8 | Insider with database access | Cover tracks by editing history | Append-only `AuditLog` written in-transaction; no API path mutates it |
| T9 | Malicious admin | Silently reassign or delete to hide failure | Audit is not role-exempt; deletes are soft; `PROTECT` on categories with incidents |
| T10 | Third-party AI provider | Harvest citizen text | Mock provider by default, no external call without configuration, scrub layer, no PII by default |
| T11 | XSS via user content | Steal tokens from another user's browser | React escaping, no `dangerouslySetInnerHTML`, announcement HTML sanitized server-side |
| T12 | CSRF | Forge state-changing requests | API is stateless JWT in a header (`CORS_ALLOW_CREDENTIALS = False`), so no cookie is auto-attached; Django admin keeps CSRF middleware |

---

## 2. Authentication

| Control | Implementation |
|---------|----------------|
| Identifier | Email (`USERNAME_FIELD = "email"`), unique and indexed, normalized to lowercase |
| Password storage | Django password hashers, Argon2 preferred with PBKDF2 fallback (see note below) |
| Access token | JWT, HS256, 15 minutes (`ACCESS_TOKEN_MINUTES`) |
| Refresh token | JWT, 7 days (`REFRESH_TOKEN_DAYS`) |
| Rotation | `ROTATE_REFRESH_TOKENS = True` |
| Reuse detection | `BLACKLIST_AFTER_ROTATION = True` — a replayed rotated token fails |
| Logout | Blacklists the presented refresh token |
| Session management | `RefreshTokenRecord` whitelist; users can list and revoke sessions |
| Brute force | `auth` throttle at 10/min plus `failed_login_count` / `locked_until` |
| Email verification | Modelled (`email_verified_at`) |
| 2FA | Modelled (`two_factor_enabled`, `two_factor_secret`), flag-gated for admins |

`PASSWORD_HASHERS` lists Argon2 **first**, with PBKDF2 and PBKDF2SHA1 as fallbacks. This
is a *preference order*, not a guarantee: if the `argon2-cffi` package is not installed,
Django silently uses PBKDF2. Verify which hasher is actually active before claiming
Argon2 in an evaluation:

```bash
cd backend && python -c "import django; from django.conf import settings; print(settings.PASSWORD_HASHERS[:1])"
```

Tokens live in browser storage under `safecity.access` and `safecity.refresh`. This is
the accepted trade-off for a stateless SPA API; it is recorded as a residual risk in
[§6](#6-residual-risks) because `localStorage` is readable by any script that achieves
XSS, which is why the XSS controls matter so much here.

---

## 3. Authorization

Three independent layers, described fully in
[ROLES-AND-ACCESS.md](ROLES-AND-ACCESS.md):

1. **Role permission class** — what kind of user is this?
2. **Object-level check** — may they touch *this* row?
3. **Service-layer workflow check** — is this transition legal from here?

The separation matters because each answers a different question. A role check cannot
tell you whether a staff member owns a given department's incident, and an object check
cannot tell you whether `resolved → submitted` is a legal move (it is not).

### Non-disclosure on lookup

An object the caller may not see returns **404**, not 403. A 403 would confirm the
record exists, which is exactly the enumeration signal T2 is looking for.

### Enforcement location

Every state-changing operation routes through `apps/*/services.py`. Viewsets are thin.
This means the workflow rules cannot be bypassed by a management command, a Celery task,
or the Django admin, because those paths call the same services.

---

## 4. Input, upload, and output controls

### Uploads

| Control | Value |
|---------|-------|
| Image MIME allowlist | `image/jpeg`, `image/png`, `image/webp`, `image/heic` |
| Image size cap | 10 MB |
| Video size cap | 100 MB |
| Document size cap | 5 MB |
| Extension check | Yes |
| MIME / content-type check | Yes |
| Magic-byte / Pillow verification | Yes |
| EXIF stripping | Yes, in the `process_media` Celery task (`exif_stripped` flag) |
| Thumbnails | Generated asynchronously |
| Malware scanning | `scan_status` field with a provider interface; no-op mock locally (`MALWARE_SCAN_PROVIDER=mock`) |
| Storage | Private bucket with presigned access in production; local disk in development |
| Rate limit | `media_upload`, 30/hour |

Validation repeats server-side regardless of what the frontend accepted. Client-side
checks exist for responsiveness, never as the boundary.

### Announcement HTML

Announcement bodies are sanitized server-side before storage/render, because announcements
are the one place an administrator authors rich text that other users' browsers render.

### Output redaction

Redaction lives in the **serializers**, not in views. Internal models can therefore gain
new PII fields without silently leaking them, because a public serializer only emits the
fields it explicitly declares.

Public projections omit: reporter identity (name, email, phone, user id), private address
line, internal comments, internal timeline entries, and exact coordinates (jittered).

---

## 5. Privacy and governance

### Data minimisation

| Principle | Implementation |
|-----------|----------------|
| Collect only what is needed | Reporting requires description and location; contact details come from the account, not a separate form |
| Anonymous reporting | Available when `ALLOW_ANONYMOUS_REPORTS` is on; `reporter` is null and `is_anonymous` is set |
| Separate public/private address | `address_public` (shareable) vs `address_private` (authority-only) |
| Purpose limitation | Consent is recorded per kind and version, not as one blanket checkbox |

### Consent

`ConsentRecord` stores `(user, kind, version, granted_at, revoked_at, ip_address)` with
kinds `terms`, `privacy`, `data_processing`, and `marketing`. `marketing` is deliberately
separate from the required consents: bundling optional marketing into required terms is
not valid consent, so the two are different records.

### Coordinate jitter

Public map and public tracking views offset coordinates by at least
`PUBLIC_COORD_JITTER_METERS` (default 150 m). 150 m is the threshold at which a point
stops identifying a specific building while remaining useful for "which neighbourhood is
this in". Authority views show exact coordinates.

### Right to erasure

`User.soft_delete()` deactivates the account, clears first/last name and phone, rewrites
the email to `deleted-<uuid>@safecity.invalid`, and sets an unusable password. The row is
retained so foreign keys from `AuditLog` and incidents stay valid.

This is a deliberate resolution of the conflict between erasure and auditability: the
personal data is destroyed, but the accountability record's structural integrity is not.
`AuditLog.actor` and `Incident.reporter` use `on_delete=SET_NULL`, so the trail reads as
"a now-anonymized account" rather than pointing at a dangling id.

### Deletion workflow

1. The user raises a request (`POST /profile/deletion-request/`) — status `pending`.
2. An administrator reviews and processes it
   (`POST /users/deletion-requests/{id}/process/`), moving it through `processing` to
   `completed` or `rejected`, recording `processed_by` and `processed_at`.

Processing is a human step on purpose. Automatic irreversible deletion on request is easy
to weaponize by an attacker who briefly holds a session.

### Audit as a governance instrument

Every workflow action writes an `AuditLog` row **inside the same transaction** as the
change, carrying actor, action, target, JSON diff, `request_id`, IP, and user agent. The
`request_id` matches the `X-Request-ID` response header and the structured log line, so a
complaint about one specific action can be traced end to end.

There is no API route to create, modify, or delete audit rows. There is no role that
bypasses auditing — including `superuser` — because the write happens in the service
layer beneath any permission check.

### Retention

| Data | Behaviour |
|------|-----------|
| Closed incidents | Targeted for anonymization after a configurable period |
| Deleted accounts | PII erased immediately; row retained for referential integrity |
| Audit logs | Append-only, retained |
| Media | EXIF stripped; private storage with presigned access |

> The configurable retention sweep for closed incidents is specified and modelled but
> **not yet implemented**. It is listed as future work.

### AI and privacy

The default provider is `mock`, so a fresh install makes no outbound call. Directing
SafeCity at an external provider is opt-in (`AI_PROVIDER`, `OPENAI_API_KEY`). Free-text
passes through a scrub layer that removes direct identifiers before any external request.
Even with a provider configured, the output is an advisory row: it cannot change an
incident's state, and the human decision is recorded alongside it.

---

## 6. Residual risks

| # | Risk | Why it remains | Mitigation / next step |
|---|------|----------------|------------------------|
| R1 | Tokens in `localStorage` | Stateless SPA API with no cookie session | Short TTL, rotation, XSS controls; a refresh-token-only httpOnly cookie is a future option |
| R2 | Coordinate jitter is not cryptographic | A precise location can sometimes be inferred by triangulating several reports | Jitter is applied per public request; a differential-privacy budget is future work |
| R3 | Excel/CSV formula injection in exports | Analytics CSV is opened in spreadsheets | Not currently neutralized — a cell beginning `=`, `+`, `-`, or `@` can execute in some spreadsheet clients |
| R4 | Malware scanning is a mock | No ClamAV instance in the demo | Provider interface is in place; wire a real scanner for any non-demo deployment |
| R5 | No CSP header | Not yet configured | See deviation D-1 below |
| R6 | Relying party must protect the object store | Demo uses local disk | Production should use a private bucket with presigned, time-limited URLs |
| R7 | Email/SMS providers unset by default | Zero-credential requirement | Console email locally; configure SMTP for real notification delivery |

R3 deserves emphasis because it is easy to overlook: the CSV export writes user-supplied
text (titles, descriptions) into cells. A title of `=HYPERLINK(...)` is inert on the web
but active when the file is opened in Excel. Prefixing risky cells with an apostrophe is
the standard fix and is not yet done.

---

## 7. Deviations from the architecture proposal

The architecture document is the approved Phase 1 baseline. Where the delivered code
diverges, the divergence is recorded here rather than quietly editing the baseline.

| # | Architecture proposal | Delivered behaviour | Impact |
|---|----------------------|---------------------|--------|
| D-1 | "CSP header with nonce strategy" | **No `Content-Security-Policy` header is set.** nginx sets `X-Content-Type-Options`, `X-Frame-Options`, and `Referrer-Policy`; Django sets XSS filter, frame-deny, and nosniff | Defence-in-depth gap (R5). The primary XSS control remains React's escaping and the absence of `dangerouslySetInnerHTML` |
| D-2 | "Every container: non-root user" | The **backend** image runs as `USER safecity`. The **frontend** nginx image has no `USER` directive and therefore runs as root | Should be fixed before any real deployment; nginx can run unprivileged |
| D-3 | "violations return **409** with machine-readable code" | Illegal transitions return **400** (DRF `ValidationError`), with `code: "invalid_transition"` | Contract difference for API consumers; clients must branch on `code`, not the status |
| D-4 | Announcement rendering with server-side sanitization | Sanitization is intended; verify the current sanitizer before accepting untrusted admin HTML | Confirm before opening authoring to non-superusers |
| D-5 | Argon2 password hashing | Argon2 is only *first in the preference list*; PBKDF2 is used unless `argon2-cffi` is installed | Verify with the command in [§2](#2-authentication) before claiming Argon2 |
| D-6 | ClamAV adapter for uploads | Mock (`MALWARE_SCAN_PROVIDER=mock`) | Interface present, implementation absent (R4) |

> Note on D-3: the error `code` field was previously being overwritten with DRF's generic
> `"invalid"`, which defeated the purpose of a machine-readable code. The exception
> handler now preserves an explicitly raised code. See
> [PROJECT-MANAGEMENT.md](PROJECT-MANAGEMENT.md#2-known-limitations).

---

## 8. Security controls checklist

### Application

- [x] Passwords hashed with a strong hasher (verify Argon2 — D-5)
- [x] Short-lived access tokens with rotation and reuse detection
- [x] Session listing and revocation
- [x] Brute-force throttling and lockout
- [x] Server-side authorization on every endpoint
- [x] Object-level checks with non-disclosure (404 over 403)
- [x] Workflow enforced in the service layer
- [x] Upload type, size, and magic-byte validation
- [x] EXIF stripping and thumbnail generation
- [x] Rate limiting on auth, submission, upload, and AI
- [x] Consistent error envelope without internal leakage
- [x] Structured logs with request correlation
- [x] Append-only audit trail written in-transaction
- [x] PII redaction in public serializers
- [x] Coordinate jitter for public views
- [x] Consent records per kind and version
- [x] Soft deletion with PII anonymization
- [ ] CSP header (D-1)
- [ ] CSV formula-injection neutralization (R3)
- [ ] Real malware scanning (D-6 / R4)

### Configuration

- [x] `DEBUG = False` in production
- [x] `ALLOWED_HOSTS` mandatory in production (asserted at startup)
- [x] HSTS with subdomains and preload, 1 year
- [x] `SECURE_SSL_REDIRECT` with proxy header support
- [x] Secure session and CSRF cookies in production
- [x] CORS from an explicit allowlist; `CORS_ALLOW_CREDENTIALS = False`
- [x] `CSRF_TRUSTED_ORIGINS` explicit
- [x] `X_FRAME_OPTIONS = DENY`
- [x] `SECURE_CONTENT_TYPE_NOSNIFF`
- [x] `Referrer-Policy: same-origin`
- [x] Secrets from environment only; `.env` gitignored
- [x] `.env.example` contains placeholders only
- [ ] Frontend container runs non-root (D-2)

### Container and supply chain

- [x] Pinned base images
- [x] Backend runs as a non-root user
- [x] `HEALTHCHECK` on services
- [x] No secrets baked into images
- [ ] Trivy image scanning wired into CI (workflows not yet authored)
- [ ] Dependency scanning wired into CI

### Process

- [x] Threat model documented (this document)
- [x] Risk register maintained
- [x] Branch protection and review expectations stated in `CONTRIBUTING.md`
- [ ] CI security gates enforced on PRs
- [ ] External penetration test (out of scope for the SDP; noted for real deployments)

**Honest summary:** the application layer is well controlled, and authorization, auditing,
and privacy redaction are enforced in depth. The main outstanding security work is
infrastructure and process — CSP, the frontend container's user, CSV export hardening,
real malware scanning, and getting these gates into CI. Nothing above should be read as
a claim of production readiness.

---

## 9. Reporting a vulnerability

See [`SECURITY.md`](../SECURITY.md) at the repository root. Do not open a public issue for
a security problem. Never include real citizen data, credentials, or exploit payloads
against systems you do not own in a report.
