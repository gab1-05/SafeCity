# SafeCity — Requirements Specification

Traceability note: requirement IDs are stable and referenced by tests where they exist.
"NFR" = non-functional requirement, "FR" = functional requirement, "UC" = use case,
"US" = user story.

---

## 1. Functional requirements

### 1.1 Authentication and accounts (`accounts`)

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| FR-A1 | Citizens self-register with email + password; email is the login identifier | ✅ | `accounts/views_auth.py` `RegisterView`, custom `User.USERNAME_FIELD = "email"` |
| FR-A2 | Passwords are hashed with a strong hasher; never stored or logged in plaintext | ✅ | Django auth hashers; `PASSWORD_HASHERS` only relaxed (MD5) under `settings/test.py` |
| FR-A3 | Login issues a short-lived access token and a longer rotating refresh token | ✅ | `simplejwt`, `ACCESS_TOKEN_MINUTES=15`, `REFRESH_TOKEN_DAYS=7` |
| FR-A4 | Refresh tokens rotate and are blacklisted on rotation/logout | ✅ | `token/refresh/`, `auth/logout/` blacklist the presented refresh token |
| FR-A5 | Repeated failed logins lock the account with a backoff | ✅ | `User.failed_login_count`, `User.locked_until`, throttle scope `auth` |
| FR-A6 | Users can list active sessions (refresh tokens) and revoke any one | ✅ | `GET /auth/sessions/`, `DELETE /auth/sessions/{id}/` |
| FR-A7 | Users can change password; all other sessions are invalidated | ✅ | `POST /auth/password/change/` |
| FR-A8 | Password reset request/confirm flow exists with a console email backend locally | ✅ | `POST /auth/password/reset/`, `/auth/password/reset/confirm/` |
| FR-A9 | Email-verification state is modelled and enforced where configured | ✅ structure | `User.email_verified_at` |
| FR-A10 | Optional TOTP 2FA is modelled for privileged accounts | ✅ structure | `User.two_factor_enabled`, `two_factor_secret` |
| FR-A11 | Users may record consent per policy version, and withdraw it | ✅ | `ConsentRecord`, `GET /profile/consents/` |
| FR-A12 | Users may request account deletion; an administrator completes it | ✅ | `DeletionRequest`, `POST /profile/deletion-request/`, `POST /users/deletion-requests/{id}/process/` |

### 1.2 Incident reporting (`incidents`)

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| FR-I1 | Authenticated users with reporting rights create incidents | ✅ | `IncidentViewSet.create` |
| FR-I2 | Reports may be submitted anonymously when the feature is enabled | ✅ | `ALLOW_ANONYMOUS_REPORTS`, `Incident.is_anonymous`, `_anonymous_allowed()` |
| FR-I3 | Each incident is classified by category and routed to an owning department | ✅ | `IncidentCategory.default_department`, `assign_department_for_category()` |
| FR-I4 | Each incident carries a unique, human-readable reference number | ✅ | `SC-MUM-<YEAR>-000001`, allocated under row lock (`ReferenceCounter`) |
| FR-I5 | Severity (low/medium/high/critical) and urgency are recorded | ✅ | `Severity`, `Urgency` choices |
| FR-I6 | Location is captured as coordinates plus public and private address lines | ✅ | `latitude`, `longitude`, `address_public`, `address_private`, `ward`, `landmark` |
| FR-I7 | Media (image/video/document) can be attached, with type and size validation | ✅ | `IncidentMedia`, upload limits in `settings.UPLOAD_LIMITS` |
| FR-I8 | Uploaded media has EXIF metadata stripped and thumbnails generated | ✅ | `incidents/tasks.py` `process_media`, `exif_stripped`, `thumbnail` |
| FR-I9 | Media scan status is tracked through a provider interface | ✅ | `scan_status`, `MALWARE_SCAN_PROVIDER`, no-op mock locally |
| FR-I10 | Duplicate reports are detected and surfaced before submission | ✅ | `POST /incidents/duplicates/check/`, `DuplicateCheckView` |
| FR-I11 | Incidents have a public timeline and an authority-only timeline | ✅ | `IncidentStatusHistory.is_public`, `can_view_internal_notes()` |
| FR-I12 | Public comments and internal notes are distinct | ✅ | `IncidentComment.is_internal` |
| FR-I13 | Incidents can be shared via an unguessable public link | ✅ | `PublicByTokenView`, `GET /incidents/public/{token}/` |
| FR-I14 | Public lookup by reference number is supported | ✅ | `GET /incidents/track/{reference}/` |
| FR-I15 | Incidents support soft deletion so audit history survives | ✅ | `Incident.deleted_at` |

### 1.3 Workflow

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| FR-W1 | Status moves only along explicitly allowed transitions, by allowed roles | ✅ | `TRANSITIONS` matrix, `services.change_status()` |
| FR-W2 | Illegal transitions are rejected with a machine-readable error | ✅ | `WorkflowError` → HTTP 400/409 |
| FR-W3 | Every transition records a `IncidentStatusHistory` row with actor and note | ✅ | inside `change_status()` transaction |
| FR-W4 | Incidents can be verified, rejected, or marked duplicate | ✅ | `submitted/under_review` → `verified/rejected/duplicate` |
| FR-W5 | Incidents can be assigned and reassigned, with assignment history | ✅ | `IncidentAssignment`, `assign_incident()` |
| FR-W6 | Auto-assignment can pick the least-loaded eligible staff member | ✅ | `pick_staff_workload_aware()` |
| FR-W7 | Incidents can be escalated with a level and reason | ✅ | `IncidentEscalation` (level_1..level_3), `escalate_incident()` |
| FR-W8 | Duplicate incidents can be merged into a parent | ✅ | `merge_incident()`, `duplicate_of`, `merged_into` |
| FR-W9 | Resolved incidents require a resolution summary and evidence | ✅ | `IncidentResolution`, `change_status(..., extra_updates=...)` |
| FR-W10 | Citizens can reopen a resolved/closed incident they reported | ✅ | `resolved → reopened` allows the `citizen` role |
| FR-W11 | Citizens can confirm resolution and leave a 1–5 rating | ✅ | `confirm_resolution()`, `IncidentFeedback` |
| FR-W12 | Emergency incidents are flagged and routed to an emergency queue | ✅ | `Incident.is_emergency`, `EMERGENCY_MODE_ENABLED` |

### 1.4 SLA, escalation, and background work

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| FR-S1 | Deadlines are configurable per (category, severity) | ✅ | `SLAConfiguration.response_hours` / `resolution_hours` |
| FR-S2 | Each incident stores the deadline computed at creation time | ✅ | `compute_sla_deadline()`, `Incident.sla_deadline` |
| FR-S3 | Breached deadlines are detected automatically | ✅ | `sla_breach_sweep` every 5 minutes |
| FR-S4 | Escalation is swept on a schedule | ✅ | `escalation_sweep` every 15 minutes |
| FR-S5 | Daily analytics are pre-aggregated | ✅ | `aggregate_daily` at 00:30, `DailyIncidentAggregate` |
| FR-S6 | Search vectors are refreshed for full-text search | ✅ | `update_search_vectors` task, PostgreSQL `tsvector` + GIN index |

### 1.5 Notifications

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| FR-N1 | In-app notifications are created for lifecycle events | ✅ | `notify()`, `Notification` |
| FR-N2 | Notifications are pushed over WebSocket when connected | ✅ backend | Channels consumer at `ws/notifications/`; frontend client not wired — see limitations |
| FR-N3 | Email delivery uses an adapter; console backend when unconfigured | ✅ | `send_email_adapter()` |
| FR-N4 | SMS and push are available as provider interfaces | ✅ interface | `send_sms_adapter()`, `send_push_adapter()` (no-op) |
| FR-N5 | Users control which channels they receive | ✅ | `NotificationPreference`, `_event_enabled()` |
| FR-N6 | Notifications can be marked read individually or in bulk | ✅ | `notifications/{id}/read/`, `notifications/read-all/` |

### 1.6 Analytics and reporting

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| FR-AN1 | Headline KPIs: totals, open, overdue, emergency, resolution rate, SLA compliance | ✅ | `GET /analytics/summary/` |
| FR-AN2 | Trend of incidents over a configurable window | ✅ | `GET /analytics/trends/?days=N` |
| FR-AN3 | Breakdowns by category, ward, department, status, severity | ✅ | `GET /analytics/by-*/` |
| FR-AN4 | Analytics are scoped to the caller's role and department | ✅ | `_scope_queryset()` |
| FR-AN5 | CSV export of the same data | ✅ | `GET /analytics/export.csv/` |
| FR-AN6 | PDF export of an incident | ⚠️ interface only | PDF export is not implemented; CSV export is |

### 1.7 Administration and audit

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| FR-AD1 | Administrators manage users and assign roles | ✅ | `users/{id}/role/` |
| FR-AD2 | Administrators deactivate accounts | ✅ | `users/{id}/deactivate/` |
| FR-AD3 | Departments, categories, zones, wards, and SLA rules are administrable | ✅ | DRF viewsets + Django admin |
| FR-AD4 | Announcements are published publicly and managed by admins | ✅ | `Announcement`, `AnnouncementViewSet` |
| FR-AD5 | Every state-changing action is auditable | ✅ | `apps/audit`, `GET /audit-logs/` |
| FR-AD6 | Audit records are immutable and filterable | ✅ | append-only model, filterable list endpoint |

### 1.8 Optional AI assistance

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| FR-AI1 | Category and severity suggestions for staff | ✅ | `POST /ai/incidents/{id}/suggest/` |
| FR-AI2 | Duplicate similarity assistance | ✅ | `POST /ai/duplicates/` |
| FR-AI3 | Every suggestion records provider, output, confidence | ✅ | `AIRecommendation` |
| FR-AI4 | A human decision (accept/edit/reject) is recorded | ✅ | `POST /ai/recommendations/{id}/decide/` |
| FR-AI5 | AI never causes a workflow transition by itself | ✅ design | recommendations are advisory rows only |
| FR-AI6 | A mock provider is the default; no external call without configuration | ✅ | `AI_PROVIDER=mock` |
| FR-AI7 | PII is scrubbed before any external AI call | ✅ design | scrub layer in `apps/ai/services.py` |

---

## 2. Non-functional requirements

### 2.1 Security

| ID | Requirement | Target | Status |
|----|-------------|--------|--------|
| NFR-SEC1 | All authorization decided server-side | 100% of endpoints | ✅ DRF permission classes + object checks |
| NFR-SEC2 | Access tokens short-lived | 15 minutes | ✅ `ACCESS_TOKEN_MINUTES` |
| NFR-SEC3 | Refresh tokens rotate with reuse detection | Rotation + blacklist | ✅ `simplejwt` blacklist app |
| NFR-SEC4 | Uploads validated by extension, MIME, magic bytes, and size | Reject on any failure | ✅ image 10 MB, video 100 MB, doc 5 MB |
| NFR-SEC5 | Standard security headers set on every response | HSTS, nosniff, frame-deny, referrer, permissions | ✅ |
| NFR-SEC6 | CORS restricted to an explicit allowlist from configuration | No wildcard in production | ✅ `CORS_ALLOWED_ORIGINS` from env |
| NFR-SEC7 | No secrets in source control | 0 secrets committed | ✅ `.env` gitignored; `.env.example` holds placeholders |
| NFR-SEC8 | Rate limits on authentication, submission, upload, and AI | Per-scope throttles | ✅ `DEFAULT_THROTTLE_RATES` |

### 2.2 Privacy

| ID | Requirement | Target | Status |
|----|-------------|--------|--------|
| NFR-PRIV1 | Public responses never include reporter identity | 0 PII leaks | ✅ public serializers omit reporter fields |
| NFR-PRIV2 | Public coordinates are jittered | ≥ 150 m (`PUBLIC_COORD_JITTER_METERS`) | ✅ |
| NFR-PRIV3 | Public tracking uses unguessable tokens, not references alone | UUIDv4 | ✅ `PublicByTokenView` |
| NFR-PRIV4 | Consent is recorded per policy version | Traceable | ✅ `ConsentRecord` |
| NFR-PRIV5 | Account deletion anonymizes PII while preserving audit integrity | FK-safe | ✅ `User.soft_delete()` |
| NFR-PRIV6 | No PII sent to external AI providers | 0 by default | ✅ mock provider is the default |

### 2.3 Performance and scalability

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-P1 | Interactive API responses | p95 < 500 ms at demo scale |
| NFR-P2 | Dashboard queries do not degrade with history | served from `DailyIncidentAggregate` where pre-aggregated |
| NFR-P3 | List endpoints are paginated | `page_size` ≤ 100 |
| NFR-P4 | Frequent query paths are indexed | indexes on status, severity, category, department, ward, created_at, sla_deadline, (lat,lng); GIN on `search_vector` |
| NFR-P5 | Large uploads do not traverse the application server | presigned direct upload to object storage |
| NFR-P6 | Expected load | < 10,000 incidents/month (SDP scale) |

### 2.4 Reliability and operability

| ID | Requirement | Status |
|----|-------------|--------|
| NFR-R1 | Liveness probe with no external dependencies | ✅ `GET /api/health/` |
| NFR-R2 | Readiness probe checking DB, cache, and storage, returning 503 when degraded | ✅ `GET /api/readiness/` |
| NFR-R3 | Structured logs including a correlation request ID | ✅ `X-Request-ID` |
| NFR-R4 | Every service can start with zero external credentials | ✅ mock/no-op adapters |
| NFR-R5 | Graceful degradation when an optional dependency is absent | ✅ local media, console email, mock AI |
| NFR-R6 | Backup and restore procedure documented | ✅ [DEVOPS.md](DEVOPS.md#7-backup-and-disaster-recovery) |

### 2.5 Maintainability and quality

| ID | Requirement | Target | Status |
|----|-------------|--------|--------|
| NFR-M1 | Backend coverage | ≥ 80% | ⚠️ gate defined; CI not wired |
| NFR-M2 | Frontend coverage | ≥ 70% statements on `src/` | ⚠️ gate defined; CI not wired |
| NFR-M3 | Backend lint/format | Ruff clean, line length 100 | ✅ `make lint` |
| NFR-M4 | Frontend strict TypeScript, no `any` | `tsc` clean, ESLint max-warnings 0 | ✅ `npm run lint`, `npm run typecheck` |
| NFR-M5 | Business logic isolated from transport | Service layer for every state change | ✅ `apps/*/services.py` |
| NFR-M6 | Reversible schema changes | Django migrations | ✅ |

### 2.6 Usability and accessibility

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-U1 | Responsive from 360 px upward | mobile-first Tailwind |
| NFR-U2 | Keyboard navigable with screen-reader support | Radix primitives, focus management |
| NFR-U3 | Loading, empty, and error states on every data view | component states |
| NFR-U4 | Professional civic visual design | consistent Tailwind design tokens |
| NFR-U5 | Supported browsers | last 2 versions of Chrome, Edge, Firefox, Safari |
| NFR-U6 | Language | English at launch; en/hi/mr prepared |

### 2.7 Compatibility and portability

| ID | Requirement |
|----|-------------|
| NFR-C1 | Runs on Linux containers and Windows dev environments |
| NFR-C2 | No hard dependency on PostGIS (lat/lng + geohash abstraction instead) |
| NFR-C3 | S3-compatible storage: MinIO locally, Amazon S3 in production |
| NFR-C4 | Python 3.12+ and Node 20+ |

---

## 3. User stories

Grouped by role. Acceptance criteria are condensed; the authoritative behaviour is in
the referenced tests and services.

### Citizen

| ID | Story | Acceptance criteria |
|----|-------|---------------------|
| US-C1 | As a citizen I want to report an incident in a few steps so that reporting is not a chore | Wizard completes; incident receives a reference number; reporter sees it in "My incidents" |
| US-C2 | As a citizen I want to attach a photo so the authority can assess without visiting | Media attached, validated, EXIF-stripped; thumbnail generated |
| US-C3 | As a citizen I want to report anonymously when the issue is sensitive | `is_anonymous` set; no reporter identity in any public representation |
| US-C4 | As a citizen I want to track my report without an account | Public tracking by reference or token; identity and exact coordinates redacted |
| US-C5 | As a citizen I want to know how long it should take | SLA deadline exposed on the incident; overdue state visible |
| US-C6 | As a citizen I want to be told when something changes | Notification written on every relevant transition |
| US-C7 | As a citizen I want to object if the fix is not real | Reopen allowed for own resolved/closed incidents |
| US-C8 | As a citizen I want to rate the outcome | 1–5 rating stored in `IncidentFeedback` |
| US-C9 | As a citizen I want my data deleted on request | Deletion request raised; admin processes it; PII anonymized |

### Volunteer

| ID | Story | Acceptance criteria |
|----|-------|---------------------|
| US-V1 | As a volunteer I want to see verified community incidents | Read access to `verified` / `in_progress` / `resolved` incidents |
| US-V2 | As a volunteer I want to add public observations | Public comment on incidents I can view |
| US-V3 | As a volunteer I should not see citizen PII or internal notes | Internal notes and PII excluded by permission and serializer |

### Department staff

| ID | Story | Acceptance criteria |
|----|-------|---------------------|
| US-D1 | As staff I want a prioritised queue for my department | Scoped list ordered by severity/urgency/SLA; filters and saved filters |
| US-D2 | As staff I want to verify or reject what reaches me | `submitted → verified/rejected` permitted; illegal cases rejected |
| US-D3 | As staff I want work assigned fairly | Workload-aware auto-assignment, or manual assignment with history |
| US-D4 | As staff I want to record internal context | Internal note visible to authority only |
| US-D5 | As staff I want to resolve with evidence | Resolution requires summary + evidence media |
| US-D6 | As staff I want to escalate when I am blocked | Escalation with level and reason; escalation sweep raises stale ones |
| US-D7 | As staff I want to merge duplicates | Duplicate merged into a parent; child closed as duplicate |
| US-D8 | As staff I want my SLA state visible | Overdue and breach flags on the queue and dashboard |

### Emergency responder

| ID | Story | Acceptance criteria |
|----|-------|---------------------|
| US-R1 | As a responder I want emergencies surfaced immediately | Emergency queue; `is_emergency` incidents and high/critical severity are visible |
| US-R2 | As a responder I want to move an incident to in-progress and resolve | Transitions permitted for responder on assigned/emergency incidents |
| US-R3 | As a responder I want to escalate | Escalation permitted |
| US-R4 | As a responder I must not reassign work to others | Assignment is restricted to admins and department staff |

### City administrator

| ID | Story | Acceptance criteria |
|----|-------|---------------------|
| US-A1 | As an admin I want to configure categories and SLA policy | Categories and `SLAConfiguration` administrable |
| US-A2 | As an admin I want to manage people and roles | Role assignment, deactivation, deletion-request processing |
| US-A3 | As an admin I want full visibility | Unscoped read access to incidents |
| US-A4 | As an admin I want to prove what happened | `GET /audit-logs/` with filters |
| US-A5 | As an admin I want to reach citizens | Announcement publishing |
| US-A6 | As an admin I want decision-support I can override | AI suggestions with recorded human decision |
| US-A7 | As an admin I need to act on behalf of a walk-in citizen | Staff/admin-created incidents attributed to a staff identity, never anonymous |

---

## 4. Use cases

### UC-1 Report an incident (primary flow)

| Field | Detail |
|-------|--------|
| **Actor** | Citizen |
| **Preconditions** | Feature enabled; reporting rights; location known |
| **Trigger** | Citizen opens "Report an incident" |
| **Main flow** | 1. Select category (optional AI/LRU suggestion). 2. Describe the incident and severity. 3. Pin the location and address. 4. Attach media (optional, required for some categories via `requires_media`). 5. Duplicate check is offered. 6. Submit. 7. System allocates a reference number, assigns a department, computes the SLA deadline, writes status history, audit log, and a notification; returns the reference. |
| **Alternate** | **Anonymous**: reporter is null and `is_anonymous` is set; no identity captured in public output. **Draft**: saved without submission; may be submitted later. |
| **Exception** | Rate limit exceeded (429); upload rejected for type/size/scan failure; validation error envelope returned. |
| **Postcondition** | Incident is `submitted` with a reference, owning department, and deadline. |

### UC-2 Verify or reject an incident

| Field | Detail |
|-------|--------|
| **Actor** | Department staff, city admin |
| **Preconditions** | Incident is `submitted` or `under_review` |
| **Main flow** | Staff reviews details and media; either verifies (→ `verified`) or rejects with a reason (→ `rejected`). |
| **Alternate** | Marked duplicate (→ `duplicate`), requiring an admin/superuser. |
| **Postcondition** | Status history and audit rows written; reporter notified. |

### UC-3 Assign work

| Field | Detail |
|-------|--------|
| **Actor** | Department staff, city admin |
| **Preconditions** | Incident is `verified` (or `submitted` for emergency fast-track) |
| **Main flow** | Choose assignee, or let workload-aware auto-assignment pick the least-loaded eligible member; incident → `assigned`; assignment row created; assignee notified. |
| **Postcondition** | `assigned_staff` / `assigned_responder` set; `assigned_at` stamped; history preserved on reassignment. |

### UC-4 Resolve and confirm

| Field | Detail |
|-------|--------|
| **Actor** | Department staff / responder; then citizen |
| **Preconditions** | Incident is `in_progress` (or `escalated`) |
| **Main flow** | Staff resolves with a summary and evidence media (→ `resolved`). Citizen is notified, reviews, and either confirms or disputes. Confirm → `closed` with rating. Dispute → `reopened`. |
| **Postcondition** | Resolution record, feedback record, and closed/open state consistent. |

### UC-5 Escalate

| Field | Detail |
|-------|--------|
| **Actor** | Staff, responder, admin |
| **Preconditions** | Incident is open and not already closed |
| **Main flow** | Escalate with level (level_1..level_3) and reason (→ `escalated`); escalation group notified. |
| **Alternate** | Deadline passes without action → `escalation_sweep` raises escalation automatically. |

### UC-6 Merge duplicates

| Field | Detail |
|-------|--------|
| **Actor** | City admin, superuser |
| **Preconditions** | Two incidents describe the same event; parent is not rejected |
| **Main flow** | Merge child into parent → child status `duplicate`, `duplicate_of` set; parent retains work; both audit-logged. |

### UC-7 Review analytics

| Field | Detail |
|-------|--------|
| **Actor** | Staff (department-scoped), responder (limited), admin (all) |
| **Main flow** | Open dashboard; filter by date range; read KPIs, trends, and breakdowns; export CSV. |
| **Exception** | Citizen requests return 403 — analytics are not citizen-facing. |

### UC-8 Administer the platform

| Field | Detail |
|-------|--------|
| **Actor** | City administrator, superuser |
| **Main flow** | Manage users/roles, departments, categories, SLA rules, announcements; review audit logs; process deletion requests. |

### UC-9 Degrade gracefully

| Field | Detail |
|-------|--------|
| **Actor** | System |
| **Trigger** | A configured dependency (email, SMS, AI, S3) is absent or fails |
| **Main flow** | Fall back to the mock/no-op/local adapter; log at warn; core workflow continues unaffected. |
| **Guarantee** | No user-facing workflow requires a cloud credential. |

---

## 5. Traceability summary

| Requirement group | Primary implementation | Primary test |
|-------------------|------------------------|--------------|
| FR-A* | `apps/accounts` | `backend/tests/test_auth.py` |
| FR-I*, FR-W* | `apps/incidents` | `backend/tests/test_incidents.py` |
| RBAC (NFR-SEC1) | `apps/accounts/permissions.py`, `TRANSITIONS` | `backend/tests/test_rbac.py` |
| Audit (FR-AD5) | `apps/audit` | `backend/tests/test_blocker_regressions.py` |
| NFR-M* | toolchain | `make lint`, `make test`, `make test-frontend` |
| E2E (success criteria) | full stack | `frontend/e2e` via `make test-e2e` |

> Running the backend suite requires PostgreSQL reachable at `DB_HOST:DB_PORT`
> (`safecity_test`). See [INSTALLATION-GUIDE.md](INSTALLATION-GUIDE.md#5-running-tests).
