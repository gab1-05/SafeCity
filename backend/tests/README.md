# Backend test suite

219 tests, **82% line coverage** over `apps` + `config` (gate: ≥ 80%, enforced in
`backend-ci.yml` via `--cov-fail-under=80`).

## Running

The suite needs **PostgreSQL** (no SQLite fallback — JSONB, `tsvector` and partial unique
constraints are relied upon) and **Redis** (Channels layer). Either point
`DB_HOST`/`DB_PORT` at a running instance or start the dev stack:

```bash
make docker-up          # or: docker compose up -d db redis
cd backend
python -m pytest -q --cov=apps --cov=config --cov-report=term-missing
```

CI provides `postgres:16` + `redis:7` service containers (see
`.github/workflows/backend-ci.yml`).

## Layout

| Files | What they cover |
|-------|-----------------|
| `conftest.py` | Shared fixtures: API client, per-role users, auth helpers |
| `test_auth.py`, `test_auth_extended.py` | JWT login/refresh/rotation, lockout, sessions, password reset/change, profile |
| `test_2fa_flows.py`, `test_two_factor.py` | TOTP enrollment + login challenge, recovery codes, disable/regenerate, TOTP primitive regressions |
| `test_oauth_google.py` | Google OAuth endpoint + token verification (google-auth path and PyJWT fallback) |
| `test_rbac.py`, `test_role_requests.py`, `test_authz_guards.py` | Role model, role-request flow, permission guards |
| `test_incidents.py`, `test_workflow.py`, `test_public_map.py`, `test_exports.py` | Incident CRUD, transition matrix, public map, exports |
| `test_notifications.py`, `test_admin_overview.py`, `test_audit_retention.py` | Notifications, admin overview, audit retention |
| `test_management_commands.py` | `seed_demo_data` (full/minimal/idempotent/repair), `seed_announcements`, `sync_roles` |
| `test_config_modules.py` | dev/prod settings contracts, WSGI/ASGI/routing importability |
| `test_blocker_regressions.py` | Regressions for previously blocking bugs |

## Bugs the suite found (all fixed)

1. `apps/accounts/two_factor.py` — TOTP codes with a leading zero (e.g. `012345`) were
   rejected (~25% of time windows). Fixed + regression test.
2. `apps/accounts/urls_auth.py` — the session-revoke route used `<uuid:pk>` while
   `OutstandingToken.id` is an integer, so revocation always 404'd. Fixed to `<int:pk>`.
3. `apps/incidents/management/commands/seed_announcements.py` — the seeder mutated its
   module-level constant and crashed on a second in-process run. Made idempotent.

## Conventions

- Mark DB-touching tests with `@pytest.mark.django_db`.
- External providers (email, SMS, AI, malware scan) are mocked through their adapters; the
  suite is hermetic and needs no credentials.
- Keep the gate green: new code under `apps/`/`config/` should ship with tests.
