# Step 2: Test Suites + Coverage Evidence

Captured: 2026-10-16
Purpose: DBIT Notice 3 automated-testing proof (C5, C6) against the gates in `docs/DEVOPS.md`.

## Backend — pytest (Django)

Command (same as CI):

```
cd backend
python -m pytest -q --cov=apps --cov=config --cov-report=term-missing --junitxml=pytest-junit.xml
```

Result:

```
collected 219 items
219 passed, 0 failed, 0 errors in ~9s
TOTAL  3719 stmts  665 miss  82%   (gate: >= 80%)
```

- JUnit XML: `backend/pytest-junit.xml` (219 tests, 0 failures, 0 errors)
- Gate status: **PASS** — 82% >= 80% (documented gate, enforced in `backend-ci.yml` via `--cov-fail-under=80`)

### Test suites added in this pass (51 new tests)

| File | Covers |
|------|--------|
| `tests/test_auth_extended.py` | password-reset confirm, change password, session list/revoke, logout edges, profile PATCH, lockout 423 |
| `tests/test_2fa_flows.py` | TOTP enrollment, login challenge exchange, recovery codes, disable, regenerate + TOTP primitive regressions |
| `tests/test_oauth_google.py` | Google OAuth endpoint (13 branches) + token verification (google-auth path + PyJWT fallback) |
| `tests/test_management_commands.py` | `seed_demo_data` (minimal + full + idempotency + role repair), `seed_announcements`, `sync_roles` |
| `tests/test_config_modules.py` | dev/prod settings contracts, WSGI/ASGI/routing importability |

### Bugs found and fixed while raising coverage

1. **TOTP leading-zero rejection** (`apps/accounts/two_factor.py`): valid codes like `012345`
   were rejected (`int < 100000`), causing intermittent 2FA failures (~25% of windows).
   Fixed + regression test.
2. **Session revoke URL type mismatch** (`apps/accounts/urls_auth.py`): route used
   `<uuid:pk>` while `OutstandingToken.id` is an integer — revocation always 404'd.
   Fixed to `<int:pk>` + tests.
3. **Seeder mutated its module constant** (`seed_announcements.py`): second in-process
   run crashed (`pop("days_ago")`). Fixed + idempotency test.

## Frontend — Vitest

Command:

```
cd frontend
npm run test -- --run --coverage
```

Result:

```
Test Files  3 passed (3)
     Tests  15 passed (15)
```

- Coverage tooling added: `@vitest/coverage-v8` dev dependency (committed).
- Coverage measured: ~7% statements on `src/` — the 70% target in `DEVOPS.md` is not yet
  met; the unit suite deliberately covers critical flows (auth API, store, badges, utils,
  login page) while full journeys are covered by the Playwright e2e suite instead.
  Recorded honestly as PARTIAL in the audit; follow-up plan in `docs/DEVOPS.md`.

## End-to-end — Playwright

Command (seeded compose stack + a fresh build of the current source):

```
cd frontend
npm run build
# E2E_BASE_URL=http://127.0.0.1:5174 E2E_NO_SERVER=1
npx playwright test
```

Result (local, 2026-10-16):

```
5 passed (5)
  smoke: landing/public map render, citizen login + report wizard, admin incident queue
  a11y:  public pages + citizen dashboard clean under axe (wcag2a/wcag2aa)
```

### Accessibility bug found and fixed during this pass

The a11y spec flagged **100 Leaflet markers on `/map` carrying `role="button"` with no
accessible name** (`aria-command-name`) — screen-reader users could not identify incident
pins. Fixed by giving every marker a `title` + `alt` (accessible name) in `PublicMapPage`,
`NearbyIncidentsPage` and the `CreateIncidentPage` location pin (re-verified: 100/100
markers named). The spec now waits for map markers before scanning, making the audit
deterministic instead of load-timing dependent.

Dependency fix: `@axe-core/playwright` added to `frontend/package.json` — the committed
`a11y.spec.ts` imported it but the package was missing, which failed the `e2e` workflow at
collection time.
