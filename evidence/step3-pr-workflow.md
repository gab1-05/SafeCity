# Step 3: PR Workflow Evidence

Captured: 2026-10-16
Purpose: DBIT Notice 3 CI/CD proof — real pull requests with all workflows green
before merge (no fabricated results; failures and their fixes are recorded).

## PR #1 — feature → develop (pipeline fixes + a11y fixes + docs)

- URL: https://github.com/gab1-05/SafeCity/pull/19
- Base `develop` ← head `fix/ci-green-and-docs`
- Head SHAs (3 pushes, each re-ran checks):
  - `39013a2` — initial (docker-ci trivy pin, a11y marker names, axe dep, docs)
  - `52b047e` — e2e CORS origin, trivy-action v0.36.0, playwright baseURL default
  - `13b56a9` — notification-bell a11y fix
- Final result on `13b56a9`: backend-ci ✅, frontend-ci ✅, docker-ci ✅,
  e2e ✅, k8s-validate ✅ (PR event; push-event duplicates also green)
- Merged: `675ce81` (merge commit on `develop`)

### Failures seen and fixed (honest log)

1. **Run on `39013a2` — docker-ci failed at "Set up job":**
   `Unable to resolve action aquasecurity/setup-trivy@v0.2.1`.
   Root cause: trivy-action v0.28.0 hardcodes `uses: aquasecurity/setup-trivy@v0.2.1`,
   and that upstream tag no longer exists (their repo now only carries v0.2.6+).
   Verified via the GitHub API (repo contents at refs v0.28.0/v0.36.0 + tag lists).
   Fix: pin `aquasecurity/trivy-action@v0.36.0`, whose action.yaml references a
   still-valid setup-trivy ref (v0.2.6 commit SHA). The earlier v0.2.0 pin had a
   different, real defect (bundled trivy 0.21 cannot emit SARIF).

2. **Run on `39013a2` — e2e failed (3 login-dependent tests):**
   citizen login, admin login and the dashboard a11y test all timed out waiting for
   the auth token in localStorage.
   Root cause: the workflow runs the backend with `config.settings.test`, whose
   `CORS_ALLOWED_ORIGINS` default only covers `:5173`/`:8080` — every XHR from the
   SPA at `http://localhost:5174` was blocked. (Local runs passed because the compose
   stack injects a wider CORS list via environment.)
   Fix: set `CORS_ALLOWED_ORIGINS: http://localhost:5174,http://127.0.0.1:5174` in
   `.github/workflows/e2e.yml` job env.

3. **Run on `52b047e` — e2e 4/5 (dashboard a11y `button-name`, 1 node):**
   The notification bell in `AppLayout` was a `<button>` (Bell icon, no text)
   nested inside a `<Link>` carrying the aria-label. The label names the link, not
   the inner button. It passed locally because the aged dev DB had unread
   notifications (the badge number gave the button implicit text); the fresh CI
   seed has `unreadCount = 0`, exposing the unnamed button.
   Reproduced locally (marked citizen1's notifications read → same 1-node failure),
   then fixed by replacing the nested pair with a single `<Link>` styled via
   `buttonVariants` carrying the aria-label. Re-ran the suite under the same
   condition: 5/5 green.

## PR #2 — develop → main (promotion)

- URL: https://github.com/gab1-05/SafeCity/pull/20
- Base `main` ← head `develop` (`675ce81`)
- Result on the PR: backend-ci ✅, frontend-ci ✅, docker-ci ✅, e2e ✅,
  k8s-validate ✅ (PR event + develop-push duplicates)
- Merged: `3994959` (merge commit on `main`)

## Post-merge verification on `main` (push event, head `3994959`)

| Workflow | Event | Conclusion | Notes |
|----------|-------|------------|-------|
| backend-ci | push | ✅ success | 219 tests, 82% ≥ 80% gate |
| frontend-ci | push | ✅ success | lint, tsc, vitest, build |
| docker-ci | push | ✅ success | **Full path for the first time**: build + push to GHCR + Trivy scan + SARIF artifact upload (validates the v0.36.0 pin end-to-end) |
| e2e | push | ✅ success | smoke + a11y against seeded stack |
| k8s-validate | push | ✅ success | helm + terraform matrix |
| deploy | — | not triggered | tag/`workflow_dispatch` only — correct |

Note: docker-ci `push`-only steps (GHCR push, Trivy scan, SARIF upload) cannot run on
PRs by design (image exists only in the builder); the `main` push run above is their
first — and green — execution.

## Gate status

**PASS** — two real PRs, every required workflow green on the merged SHAs, full
`main`-push path (including image push + security scan) verified green.
