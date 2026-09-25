# SafeCity — API Reference

The backend is a Django REST Framework application. This document is the **narrative**
reference: conventions, endpoint inventory, and worked examples.

The **machine-readable** contract is generated from the code and must never be
hand-edited:

```bash
make openapi                     # writes docs/api-schema.yaml
```

| Format | URL (development) |
|--------|-------------------|
| Swagger UI | `/api/schema/swagger/` |
| Redoc | `/api/schema/redoc/` |
| Raw OpenAPI 3 | `/api/schema/` |

Base path is **`/api/v1/`**. Health and schema endpoints sit one level above it.

---

## 1. Conventions

### Versioning

The API version is in the URL path (`/api/v1/`). Breaking changes ship as `/api/v2/`
rather than mutating v1 in place.

### Authentication

JWT bearer tokens, header-based:

```
Authorization: Bearer <access_token>
```

| Setting | Value | Config key |
|---------|-------|-----------|
| Access token lifetime | 15 minutes | `ACCESS_TOKEN_MINUTES` |
| Refresh token lifetime | 7 days | `REFRESH_TOKEN_DAYS` |
| Rotation | on | `ROTATE_REFRESH_TOKENS` |
| Blacklist after rotation | yes | `BLACKLIST_AFTER_ROTATION` |
| Algorithm | HS256 | `SIMPLE_JWT.ALGORITHM` |

Refresh tokens rotate on every use. Presenting a rotated (blacklisted) refresh token
fails, which is how token replay is detected — a stolen refresh token becomes useless
as soon as the legitimate client refreshes.

Django admin remains session + CSRF authenticated; it is a separate surface from the
API.

### Pagination

Page-number pagination, `PAGE_SIZE = 20`, `max_page_size = 100`.

```json
{
  "count": 137,
  "next": "http://localhost:8080/api/v1/incidents/?page=3",
  "previous": "http://localhost:8080/api/v1/incidents/?page=1",
  "results": []
}
```

### Filtering, search, ordering

Enabled globally via `DjangoFilterBackend`, `SearchFilter`, and `OrderingFilter`:

- `?field=value` — exact-match filters where a viewset declares them
- `?search=term` — full-text search (PostgreSQL `tsvector` on incidents)
- `?ordering=-created_at` — ordering
- `?page=N&page_size=N` — pagination

### Error envelope

Every error response — validation, permission, not-found, and unexpected server errors —
uses one shape, produced by `apps/core/exceptions.py`:

```json
{
  "detail": "Human-readable summary.",
  "code": "machine_readable_code",
  "errors": { "field_name": ["Message."] }
}
```

Unexpected exceptions are logged with a stack trace server-side and returned as a
generic 500 without internals, so implementation details never leak to clients.

### Status codes

| Code | Meaning in SafeCity |
|------|---------------------|
| 200 / 201 | Success |
| 204 | Deleted (no body) |
| 400 | Validation failure, **including an illegal workflow transition** (`WorkflowError` subclasses DRF's `ValidationError`) |
| 401 | Missing/invalid/expired credentials |
| 403 | Authenticated but not permitted (includes role-scope and analytics-for-citizen) |
| 404 | Not found, **or** not visible to this caller (existence is not disclosed) |
| 429 | Rate limit exceeded |
| 503 | Readiness probe reports a degraded dependency |

Returning 404 rather than 403 for objects a caller may not see is deliberate: a 403 on an
object the caller cannot view would confirm that the object exists.

### Rate limits

| Scope | Limit | Config key |
|-------|-------|-----------|
| `anon` | `RATE_LIMIT_ANON_PER_MIN`/min (default 30) | env |
| `user` | 120/min | fixed |
| `auth` | 10/min | fixed |
| `incident_create` | `RATE_LIMIT_INCIDENTS_PER_HOUR`/hour (default 5) | env |
| `media_upload` | 30/hour | fixed |
| `ai` | 20/hour | fixed |

Throttling is disabled under `config.settings.test`, with rates still declared so scoped
throttle classes can resolve them.

### Request correlation

Responses carry an `X-Request-ID`. The same value is written to `AuditLog.request_id`
and attached to structured log lines, so a report about a specific action can be traced
to its audit row and its logs.

---

## 2. Endpoint inventory

### 2.1 Operational

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/health/` | none | Liveness. No external dependencies checked. Always 200 when the process is up. |
| GET | `/api/readiness/` | none | Readiness. Checks database, cache/Redis, and storage. **503** with a `checks` map when degraded. |
| GET | `/api/meta/config/` | none | Public runtime config: map tile URL, feature flags, upload limits, active categories. |
| GET | `/api/schema/` | none | OpenAPI 3 document |
| GET | `/api/schema/swagger/` | none | Swagger UI |
| GET | `/api/schema/redoc/` | none | Redoc |

`/api/readiness/` is the probe orchestrators should use to decide routing. It returns the
failing dependency rather than a bare failure:

```json
{ "status": "degraded", "checks": { "database": "error", "cache": "ok", "storage": "local" } }
```

### 2.2 Authentication — `/api/v1/auth/`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/auth/register/` | none | Register a citizen account |
| POST | `/auth/token/` | none | Obtain access + refresh tokens (throttled, `auth` scope) |
| POST | `/auth/token/refresh/` | none | Rotate refresh → new access + refresh |
| POST | `/auth/token/verify/` | none | Verify a token is valid |
| POST | `/auth/logout/` | bearer | Blacklist the presented refresh token |
| GET / PATCH | `/auth/me/` | bearer | Read / update own profile |
| POST | `/auth/password/reset/` | none | Request a reset link |
| POST | `/auth/password/reset/confirm/` | none | Complete the reset |
| POST | `/auth/password/change/` | bearer | Change password (invalidates other sessions) |
| GET | `/auth/sessions/` | bearer | List active refresh-token sessions |
| DELETE | `/auth/sessions/{id}/` | bearer | Revoke one session |

### 2.3 Users — `/api/v1/users/`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/users/` | city_admin, superuser | List users |
| GET | `/users/{id}/` | city_admin, superuser | Retrieve a user |
| POST | `/users/{id}/role/` | city_admin, superuser | Change a user's role |
| POST | `/users/{id}/deactivate/` | city_admin, superuser | Deactivate an account |
| GET | `/users/deletion-requests/` | city_admin, superuser | List deletion requests |
| POST | `/users/deletion-requests/{id}/process/` | city_admin, superuser | Approve/complete a deletion request |

### 2.4 Profile — `/api/v1/`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET / PATCH | `/profile/notification-preferences/` | bearer | Channel and per-event switches |
| GET | `/profile/consents/` | bearer | Consent records |
| POST | `/profile/deletion-request/` | bearer | Request account deletion |
| GET / POST | `/saved-locations/` | bearer | List / create a saved location |
| GET / PATCH / DELETE | `/saved-locations/{id}/` | bearer | Manage a saved location |

### 2.5 Reference data

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/departments/` | bearer | List departments |
| GET | `/departments/{id}/` | bearer | Retrieve a department |
| GET | `/categories/` | bearer | List incident categories |
| GET | `/categories/{id}/` | bearer | Retrieve a category |
| GET | `/wards/` | bearer | List wards |
| GET | `/wards/{id}/` | bearer | Retrieve a ward |
| GET | `/zones/` | bearer | List zones |
| GET | `/zones/{id}/` | bearer | Retrieve a zone |

### 2.6 Incidents — `/api/v1/incidents/`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/incidents/` | bearer | Role-scoped, filterable, searchable, paginated list |
| POST | `/incidents/` | citizen, staff, admin | Create an incident (throttle `incident_create`) |
| GET | `/incidents/{id}/` | bearer (object-checked) | Retrieve one incident |
| PATCH | `/incidents/{id}/` | object-checked | Update permitted fields |
| DELETE | `/incidents/{id}/` | object-checked | Soft delete |
| POST | `/incidents/{id}/status/` | per transition matrix | Perform a status transition |
| POST | `/incidents/{id}/assign/` | staff, admin | Assign or reassign |
| POST | `/incidents/{id}/escalate/` | authority | Escalate with level + reason |
| POST | `/incidents/{id}/merge/` | admin, superuser | Merge as duplicate into a parent |
| POST | `/incidents/{id}/reopen/` | reporter, staff, admin | Reopen a resolved/closed incident |
| POST | `/incidents/{id}/confirm/` | reporter, admin | Confirm resolution (optional rating) |
| GET | `/incidents/{id}/timeline/` | object-checked | Status timeline (public + internal where permitted) |
| GET / POST | `/incidents/{id}/comments/` | object-checked | Read / add comments and internal notes |
| GET | `/incidents/{id}/similar/` | object-checked | Nearby/similar incidents |
| GET | `/incidents/{id}/export.pdf/` | object-checked | Printable HTML report (see note) |
| POST | `/incidents/duplicates/check/` | bearer | Duplicate check during the wizard |
| GET | `/incidents/track/{reference}/` | none | Public lookup by reference number |
| GET | `/incidents/public/{token}/` | none | Public view by unguessable token |

> **Note on `export.pdf`.** The path is named `export.pdf`, but the current
> implementation returns a **print-ready HTML document** with
> `Content-Disposition: inline`, intended for the browser's print-to-PDF. A true PDF
> pipeline (WeasyPrint / xhtml2pdf) can be attached later without changing the route.
> The filename suggests a PDF; the content type is `text/html`. This is recorded in
> [Known limitations](PROJECT-MANAGEMENT.md#2-known-limitations).

#### Media — `/api/v1/incidents/media/`

These routes are registered **before** the incidents router on purpose: the incidents
`DefaultRouter` registers `incidents/<pk>/` with a `[^/.]+` pk pattern that would
otherwise match `incidents/media/` and 404 every upload.

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET / POST | `/incidents/media/` | object-checked | List / upload incident media |
| GET / DELETE | `/incidents/media/{id}/` | object-checked | Retrieve / delete media |

### 2.7 Notifications — `/api/v1/notifications/`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/notifications/` | bearer | List own notifications |
| POST | `/notifications/{id}/read/` | bearer | Mark one read |
| POST | `/notifications/read-all/` | bearer | Mark all read |

Realtime delivery uses a Django Channels WebSocket at `ws/notifications/`, not an HTTP
endpoint. See [§5 WebSocket](#5-websocket-notifications).

### 2.8 Announcements — `/api/v1/announcements/`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/announcements/` | none (published) | List published announcements |
| GET | `/announcements/{id}/` | none (published) | Retrieve one |
| POST | `/announcements/` | city_admin, superuser | Create |
| PATCH / DELETE | `/announcements/{id}/` | city_admin, superuser | Update / delete |

### 2.9 Analytics — `/api/v1/analytics/`

Citizens receive **403**; staff are department-scoped; responders are limited; admins and
superusers are unscoped.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/analytics/summary/` | Headline KPIs |
| GET | `/analytics/trends/` | Incidents per day |
| GET | `/analytics/by-category/` | Breakdown by category |
| GET | `/analytics/by-ward/` | Breakdown by ward |
| GET | `/analytics/by-department/` | Breakdown by department |
| GET | `/analytics/by-status/` | Breakdown by status |
| GET | `/analytics/by-severity/` | Breakdown by severity |
| GET | `/analytics/export.csv/` | CSV export of the summary |

`summary/` and `trends/` accept `?days=N` (1–365, default 30).

### 2.10 Audit — `/api/v1/audit-logs/`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/audit-logs/` | city_admin, superuser | Filterable, read-only audit trail |

Read-only by design: there is no create, update, or delete route. Rows are written only
by the audit service, inside the transaction that changed state.

### 2.11 AI — `/api/v1/ai/`

All AI endpoints are advisory. Responses include a `disclaimer` field and, for
suggestions, a recommendation id so the human decision can be recorded.

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/ai/incidents/{incident_id}/suggest/` | authority | Category + severity suggestions (throttle `ai`) |
| POST | `/ai/recommendations/{recommendation_id}/decide/` | authority | Record `accepted` / `edited` / `rejected` |
| POST | `/ai/duplicates/` | bearer | Duplicate similarity assistance |

---

## 3. Worked examples

### 3.1 Register and authenticate

```bash
# Register
curl -s -X POST http://localhost:8080/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"email":"new.citizen@example.com","password":"Str0ng-Pass!23","first_name":"New","last_name":"Citizen"}'

# Log in
curl -s -X POST http://localhost:8080/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"citizen1@safecity.local","password":"Citizen@12345!"}'
```

Response:

```json
{ "access": "<15-minute token>", "refresh": "<7-day token>" }
```

Store `access` and send it as `Authorization: Bearer <access>`.

### 3.2 Report an incident

```bash
curl -s -X POST http://localhost:8080/api/v1/incidents/ \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{
        "title": "Deep pothole near bus stop",
        "description": "Roughly 2 feet across and deep enough to damage a two-wheeler wheel. Near the Andheri station bus stop.",
        "category": "<category-uuid>",
        "severity": "high",
        "latitude": "19.119700",
        "longitude": "72.846400",
        "address_public": "Near Andheri station bus stop",
        "is_anonymous": false
      }'
```

The server allocates the reference number, routes to the owning department, and computes
the SLA deadline. The returned `reference_number` looks like `SC-MUM-2026-000042`.

### 3.3 Perform a workflow transition

```bash
# Verify (department staff / admin)
curl -s -X POST http://localhost:8080/api/v1/incidents/$ID/status/ \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{"to_status": "verified", "note": "Confirmed on site."}'
```

An illegal transition is rejected with **400** and a machine-readable code rather than
being silently applied:

```json
{ "detail": "Transition submitted → resolved is not allowed for you.", "code": "invalid_transition", "errors": {} }
```

Clients should branch on `code`, not on the message text. Codes raised by the workflow
layer include `invalid_transition`, `anonymous_disabled`, `forbidden_department`, and
`invalid_assignee`. Authentication failures use `not_authenticated`.

### 3.4 Assign and resolve

```bash
# Assign (workload-aware auto-selection if assignee is omitted)
curl -s -X POST http://localhost:8080/api/v1/incidents/$ID/assign/ \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{"assignee": "<staff-uuid>", "note": "Roads crew 2"}'

# Resolve with evidence
curl -s -X POST http://localhost:8080/api/v1/incidents/$ID/status/ \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{"to_status": "resolved", "note": "Pothole filled and levelled.",
       "resolution_summary": "Filled with hot-mix asphalt on 2026-09-18, levelled and compacted."}'
```

### 3.5 Citizen confirms

```bash
curl -s -X POST http://localhost:8080/api/v1/incidents/$ID/confirm/ \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{"rating": 5, "comment": "Fixed within two days. Thank you."}'
```

### 3.6 Public tracking (no account required)

```bash
# By reference number
curl -s http://localhost:8080/api/v1/incidents/track/SC-MUM-2026-000042/

# By unguessable token
curl -s http://localhost:8080/api/v1/incidents/public/3f9c1e2a-..../
```

Both return a redacted projection: no reporter identity, no private address, no internal
notes, and coordinates jittered by at least `PUBLIC_COORD_JITTER_METERS` (default 150 m).

### 3.7 AI suggestion with a recorded human decision

```bash
curl -s -X POST http://localhost:8080/api/v1/ai/incidents/$ID/suggest/ \
  -H "Authorization: Bearer $ACCESS"

# ... read the recommendations, then record what you did with one ...
curl -s -X POST http://localhost:8080/api/v1/ai/recommendations/$REC_ID/decide/ \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{"decision": "edited"}'
```

The decision is audit-logged with the kind and confidence, which is what makes the
suggestion explainable in review.

### 3.8 Health checks

```bash
curl -s http://localhost:8080/api/health/     # {"status":"ok","service":"safecity-backend"}
curl -s http://localhost:8080/api/readiness/  # 200 or 503 with a per-dependency map
```

---

## 4. Role scoping cheat sheet

| Caller | `GET /incidents/` returns |
|--------|---------------------------|
| Citizen | Own reports |
| Volunteer | Verified / in-progress / resolved community incidents |
| Department staff | Their department's incidents |
| Emergency responder | Assigned, high/critical, or emergency incidents |
| City admin / superuser | Everything (excluding soft-deleted) |

Full detail is in [ROLES-AND-ACCESS.md](ROLES-AND-ACCESS.md).

---

## 5. WebSocket notifications

Realtime notifications are delivered over **Django Channels**, not an HTTP endpoint and
not Socket.IO:

| Property | Value |
|----------|-------|
| Route | `ws/notifications/` |
| Consumer | `apps/notifications/consumers.py` `NotificationConsumer` |
| Protocol | `AsyncJsonWebsocketConsumer` (`{"type": "notify", "payload": {...}}`) |
| Group per user | `user-<user_id>` |
| Origin validation | `AllowedHostsOriginValidator` |
| Production server | Daphne behind the load balancer |

There is currently **no WebSocket client in the frontend**, so the SPA relies on the
polling REST endpoints. `socket.io-client` is declared as a frontend dependency but is
unused, and Socket.IO is not compatible with this Channels consumer — see
[Known limitations](PROJECT-MANAGEMENT.md#2-known-limitations). The HTTP notification
endpoints above are the supported path today.

---

## 6. Regenerating the schema

```bash
make openapi    # equivalent to:
                # cd backend && python manage.py spectacular --file ../docs/api-schema.yaml
```

Run this whenever serializers or viewsets change. CI is intended to fail when the
committed schema drifts from the generated one.
