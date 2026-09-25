# SafeCity — Administrator Manual

For **city administrators** (`city_admin`) and **superusers**.

> **Read this first:** SafeCity's administration surface is split. People, announcements,
> audit and analytics are manageable through the application. Reference data — departments,
> categories, wards, zones and SLA rules — is **read-only through the API** and is managed
> by the seed command or the Django shell. The Django admin site, despite what
> `docs/ARCHITECTURE.md` suggests, currently has **no application models registered**.
>
> This document tells you which is which, so you are not left hunting for a screen that
> does not exist. See [§2](#2-what-you-can-and-cannot-manage-from-the-ui).

---

## 1. Administrator roles

| | City Administrator | Superuser |
|---|---|---|
| See and act on all incidents | ✅ | ✅ |
| Manage users and roles | ✅ | ✅ |
| Process deletion requests | ✅ | ✅ |
| Manage announcements | ✅ | ✅ |
| Read audit logs | ✅ | ✅ |
| View all analytics | ✅ | ✅ |
| Django admin access (`is_staff`) | — | ✅ |
| Django shell / management commands | — | ✅ |

Both are treated as "authority" by the permission layer, so both bypass department scoping.
The practical difference is that only a superuser can reach the Django admin and the shell,
which is where reference-data changes happen today.

---

## 2. What you can and cannot manage from the UI

| Resource | Manageable in the application? | How |
|----------|-------------------------------|-----|
| **Users** — list, view | ✅ | `/admin/users`, `GET /api/v1/users/` |
| **User roles** | ✅ | `POST /api/v1/users/{id}/role/` |
| **Deactivate a user** | ✅ | `POST /api/v1/users/{id}/deactivate/` |
| **Deletion requests** | ✅ | `/admin/users`, `GET /users/deletion-requests/`, `POST /users/deletion-requests/{id}/process/` |
| **Announcements** — create/edit/publish/delete | ✅ | `POST/PATCH/DELETE /api/v1/announcements/`, `POST /announcements/{id}/publish/` |
| **Audit logs** — read | ✅ | `/admin/audit`, `GET /api/v1/audit-logs/` |
| **Analytics** | ✅ | `/analytics`, `GET /api/v1/analytics/*` |
| **Department workload** | ✅ | `GET /api/v1/departments/{id}/workload/` |
| **Departments** | ❌ read-only via API | Django shell / seed ([§5](#5-managing-reference-data)) |
| **Incident categories** | ❌ read-only via API | Django shell / seed |
| **Wards and zones** | ❌ read-only via API | Django shell / seed |
| **SLA rules** | ❌ read-only via API | Django shell / seed |
| **Integration configuration** | ❌ no API | Django shell / Django admin |
| **API keys** | ❌ no API | Django shell / Django admin |

Reference data is read-only over the API (`ListModelMixin` + `RetrieveModelMixin` for
departments/wards/zones, `ReadOnlyModelViewSet` for categories). The reporting form needs
to read it, so it is public; nothing needs to write it at runtime.

**This is a real gap**, not a design statement: an administrator cannot add a category or
change an SLA deadline without shell access. It is logged in
[Known limitations](PROJECT-MANAGEMENT.md#2-known-limitations).

---

## 3. Managing users

### Assigning or changing a role

Roles are a single value per user (`citizen`, `volunteer`, `department_staff`,
`emergency_responder`, `city_admin`, `superuser`). Only `city_admin` and `superuser` may
change them, and self-registration can never produce anything but `citizen`.

```bash
curl -X POST http://localhost:8080/api/v1/users/$USER_ID/role/ \
  -H "Authorization: Bearer $ADMIN_ACCESS" \
  -H "Content-Type: application/json" \
  -d '{"role": "department_staff", "department": "'"$WATER_DEPT_ID"'"}'
```

Assign a `department` for `department_staff`, or the user will be scoped to nothing and see
an empty queue. This is the single most common setup mistake.

### Deactivating a user

```bash
curl -X POST http://localhost:8080/api/v1/users/$USER_ID/deactivate/ \
  -H "Authorization: Bearer $ADMIN_ACCESS"
```

Deactivation sets `is_active = false` and revokes access. It is **not** deletion: the
account's history stays intact, which is why it is the right action for a staff member who
has left rather than erasing their record.

### Processing a deletion request

A citizen raises a request; you complete it. This is human-in-the-loop on purpose — an
attacker holding a brief session should not be able to irreversibly delete an account.

1. `GET /api/v1/users/deletion-requests/` — find `pending` requests.
2. Verify the requester before acting if the data is sensitive.
3. `POST /api/v1/users/deletion-requests/{id}/process/` with a status of `processing`,
   `completed`, or `rejected`.

`completed` runs `User.soft_delete()`, which anonymizes name, phone and email to
`deleted-<uuid>@safecity.invalid`, sets an unusable password, and keeps the row so audit and
incident foreign keys survive. Accountability for past actions is preserved; personal data
is not.

---

## 4. Announcements

Announcements are the one publishing surface, and they are full CRUD.

```bash
# Create (draft)
curl -X POST http://localhost:8080/api/v1/announcements/ \
  -H "Authorization: Bearer $ADMIN_ACCESS" -H "Content-Type: application/json" \
  -d '{"title":"Water supply interruption — Ward 4","body":"...","audience":"public","is_pinned":true}'

# Publish
curl -X POST http://localhost:8080/api/v1/announcements/$ID/publish/ \
  -H "Authorization: Bearer $ADMIN_ACCESS"
```

| Field | Effect |
|-------|--------|
| `audience` | `public` (everyone), `citizens`, or `staff` |
| `is_pinned` | Pins to the top of the list |
| `is_published` | Only published announcements are visible publicly |

Drafts are invisible to the public. Every create, update, delete and publish is audit-logged
with your actor identity.

> **Announcement bodies are rendered as content on public pages.** Treat announcement HTML
> as an injection surface and avoid pasting untrusted markup. Server-side sanitization is
> intended but should be verified before authoring is opened beyond trusted admins — see
> [Security deviations](SECURITY-AND-PRIVACY.md#7-deviations-from-the-architecture-proposal) D-4.

---

## 5. Managing reference data

Changes here are made with the Django shell or by editing the seed command. Run from
`backend/` with the virtualenv active.

### Departments

```bash
python manage.py shell -c "
from apps.accounts.models import Department
d, created = Department.objects.get_or_create(
    code='parks',
    defaults={'name': 'Parks & Gardens', 'is_emergency_department': False,
              'contact_email': 'parks@safecity.local'},
)
print('created' if created else 'already existed', d)
"
```

`code` is a slug used in URLs and labels; changing it breaks references in docs and
commands. Changing a department's *name* is safe.

### Incident categories

The category decides which department receives a report, via `default_department`. This
routing rule is the most consequential thing you will configure.

```bash
python manage.py shell -c "
from apps.incidents.models import IncidentCategory
from apps.accounts.models import Department
dept = Department.objects.get(code='parks')
c, created = IncidentCategory.objects.get_or_create(
    slug='fallen-tree',
    defaults={
        'name': 'Fallen Tree',
        'default_department': dept,
        'is_emergency_category': True,
        'requires_media': True,
        'display_order': 50,
        'icon': 'tree',
    },
)
print('created' if created else 'already existed', c)
"
```

| Field | Guidance |
|-------|----------|
| `default_department` | The department that receives these reports. Leaving it null means the report arrives unowned |
| `is_emergency_category` | Marks reports as emergencies and routes them to the fast lane. Use sparingly |
| `requires_media` | Forces a photo. Good for damage claims; a barrier for issues people pass on foot |
| `display_order` | Lower sorts first in the reporting form. Put frequent categories at the top |
| `is_active` | Retire a category instead of deleting it — deletion is `PROTECT`ed while incidents reference it |

### SLA rules

Deadlines are per `(category, severity)`. A rule with `category = NULL` is the fallback for
every category without its own rule.

```bash
python manage.py shell -c "
from apps.core.models import SLAConfiguration
from apps.incidents.models import IncidentCategory
cat = IncidentCategory.objects.get(slug='fallen-tree')
SLAConfiguration.objects.update_or_create(
    category=cat, severity='critical', is_active=True,
    defaults={'response_hours': 1, 'resolution_hours': 6},
)
print('ok')
"
```

**Deadlines are snapshotted onto each incident at creation.** Changing a rule does not
retroactively alter existing deadlines — deliberately, because silently moving a deadline
would rewrite the performance record. New incidents pick up the new policy.

### Wards and zones

Seed data ships illustrative Mumbai-style zones and wards. They are explicitly
non-authoritative.

```bash
python manage.py shell -c "
from apps.core.models import Zone, Ward
z, _ = Zone.objects.get_or_create(code='z4', defaults={'name': 'Zone 4'})
Ward.objects.get_or_create(code='z4-w1', defaults={'name': 'Zone 4 Ward 1', 'zone': z,
    'latitude': 19.08, 'longitude': 72.88})
print('ok')
"
```

### Roles and groups

After changing role definitions, sync the Django groups:

```bash
python manage.py sync_roles
```

> **Caveat.** `apps/accounts/roles.py` currently maps **no permission codenames** to roles —
> the `ROLE_PERMISSIONS` dictionary is empty. `sync_roles` creates the groups and reports
> membership, but grants no permissions. Authorization comes from the explicit permission
> classes and the transition matrix instead. See
> [ROLES-AND-ACCESS.md](ROLES-AND-ACCESS.md#7-current-gaps).

---

## 6. Audit logs

`/admin/audit` and `GET /api/v1/audit-logs/` expose the append-only trail. Each row records
actor, action, object, a JSON change diff, `request_id`, IP and user agent.

| Field | Use |
|-------|-----|
| `action` | e.g. `incident.status_change`, `ai.decision`, `announcement.published` |
| `actor` | Who acted (null after the account is anonymized) |
| `object_type` / `object_id` | What was affected |
| `changes` | Before/after values |
| `request_id` | Matches the `X-Request-ID` response header and the JSON log line |
| `ip_address` / `user_agent` | Request provenance |

### Investigating "who changed this?"

1. Find the incident or object in the relevant view.
2. Filter audit logs by `object_type` and `object_id`.
3. Read the `changes` diff to see exactly what moved.
4. Take the `request_id` and search the backend logs for the full request context.

There is no API route to create, modify or delete audit rows, and no role bypasses
auditing — including superuser, because the write happens in the service layer beneath any
permission check.

---

## 7. Analytics

`/analytics` and `GET /api/v1/analytics/*` are role-scoped:

| Role | Sees |
|------|------|
| Citizen | **403** — analytics are not citizen-facing |
| Department staff | Their department only |
| Emergency responder | Assigned incidents plus all high/critical |
| City admin / superuser | Everything |

| Endpoint | Gives |
|----------|-------|
| `/analytics/summary/` | Totals, open, awaiting verification, high priority, overdue, emergency, resolution rate, SLA compliance %, average response and resolution minutes, average satisfaction |
| `/analytics/trends/?days=30` | Incidents per day |
| `/analytics/by-category/`, `by-ward/`, `by-department/`, `by-status/`, `by-severity/` | Breakdowns |
| `/analytics/export.csv/` | CSV of the summary |

`days` accepts 1–365 (default 30).

The summary is computed live over the window. `DailyIncidentAggregate` rows are also built
nightly by `apps.analytics.tasks.aggregate_daily` at 00:30 — those are the intended
O(1) source for historical dashboards, but the current summary endpoint queries incidents
directly, so very large windows are slower than they need to be.

> **When exporting CSV, be careful opening it in a spreadsheet.** Cell values come from
> citizen-authored text. A title beginning with `=`, `+`, `-` or `@` can be interpreted as a
> formula by Excel. Review before forwarding, and see
> [Residual risk R3](SECURITY-AND-PRIVACY.md#6-residual-risks).

---

## 8. Reviewing AI recommendations

AI output is advisory and always requires a recorded human decision. No incident changes
state because of an AI suggestion.

```bash
# Ask for suggestions (authority only)
curl -X POST http://localhost:8080/api/v1/ai/incidents/$ID/suggest/ \
  -H "Authorization: Bearer $ADMIN_ACCESS"

# Record what you did with one
curl -X POST http://localhost:8080/api/v1/ai/recommendations/$REC_ID/decide/ \
  -H "Authorization: Bearer $ADMIN_ACCESS" -H "Content-Type: application/json" \
  -d '{"decision": "accepted"}'   # or "edited" / "rejected"
```

Each `AIRecommendation` stores provider, output, confidence and the decision, so it stays
answerable *why* a classification was chosen. The default provider is `mock`, which makes no
external call. Enabling a real provider is a configuration change with privacy consequences —
read [§4 of the security doc](SECURITY-AND-PRIVACY.md#4-input-upload-and-output-controls)
first.

---

## 9. Emergency mode

Controlled by `EMERGENCY_MODE_ENABLED` (default on) and surfaced to the SPA through
`GET /api/meta/config/`.

When enabled:

- the frontend shows a red emergency banner,
- emergency incidents appear at the top of the response queue,
- `is_emergency` incidents bypass normal verification for visibility (a human still
  verifies; nothing is auto-dispatched),
- responders see all high and critical incidents.

Disable it in configuration if the deployment should not present emergency affordances —
for example a purely demonstrative instance.

---

## 10. Routine operational tasks

| Task | Command |
|------|---------|
| Apply migrations | `make migrate` |
| Create a superuser | `make superuser` |
| Sync role groups | `python manage.py sync_roles` |
| Re-seed demo data (idempotent) | `make seed` |
| Regenerate the API schema | `make openapi` |
| Tail backend logs | `make docker-logs` |

### Before a demo or evaluation

1. `make migrate` — schema current.
2. `make seed` — demo data present.
3. `curl /api/readiness/` — all checks `ok`.
4. Open the citizen, staff and admin views at least once.

### Health checks

```bash
curl -s http://localhost:8080/api/health/      # liveness, no dependencies
curl -s http://localhost:8080/api/readiness/   # 503 with a per-dependency map if degraded
```

---

## 11. Administrator checklist

- [ ] Every `department_staff` account has a `department` assigned
- [ ] Every active category has a `default_department`, or reports arrive unowned
- [ ] SLA rules exist for each severity — at minimum a null-category fallback per severity
- [ ] At least one emergency department is flagged `is_emergency_department`
- [ ] Announcements are reviewed before publishing; drafts stay unpublished
- [ ] Deletion requests are processed deliberately, never in bulk
- [ ] `is_staff` is granted only to superusers
- [ ] Demo credentials do **not** exist in any deployed environment
- [ ] Audit log reviewed after any incident of note
