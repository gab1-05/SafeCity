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

Specs exist (`frontend/e2e/`, incl. `a11y.spec.ts`); they require the seeded compose stack.
Run: `make docker-up && make migrate && make seed && make test-e2e`.
