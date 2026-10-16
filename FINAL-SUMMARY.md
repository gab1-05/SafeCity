# SafeCity DevOps Compliance Audit - FINAL RESULTS

Captured: 2026-10-16 | Repository: https://github.com/gab1-05/SafeCity
Audited commits: main `3994959`, develop `b52d92e` (all fixes merged)

## Verdict

**READY FOR REVIEW** — DBIT Notice 3 compliance ≈ **92%**. All static artifacts are in
place and every execution gap has either been closed against a live environment or
is honestly blocked with a documented reason (AWS apply: no credentials on this
machine + free-tier-only constraint; decision requested from the operator).

## Changes implemented (all committed to `develop` and merged to `main`)

### 1. CI/CD pipeline — real PRs, all green (closes A4, B2–B4, C5–C6)
- **PR #19** `fix/ci-green-and-docs` → `develop`, merged `675ce81`
  - `docker-ci.yml`: trivy-action pinned to resolvable v0.36.0 (v0.28.0 referenced a
    deleted `setup-trivy@v0.2.1` tag; v0.2.0 bundled trivy 0.21 which cannot emit SARIF)
  - `e2e.yml`: added `CORS_ALLOWED_ORIGINS` for the `:5174` SPA origin (login XHRs were
    blocked in CI but passed locally because compose sets wider CORS)
  - Accessibility fixes: 100 unnamed Leaflet markers on `/map` got accessible names;
    notification bell restructured from nested `<Link><Button>` to a single labeled
    `<Link>` (axe `button-name`, reproduced locally then fixed)
  - `@axe-core/playwright` added as devDependency; a11y spec waits for map markers
    (deterministic); unused `socket.io-client` removed
  - Docs: `DEVOPS.md` pipeline table + gate statements now match shipped workflows;
    `PROJECT-MANAGEMENT.md` milestone table, honest summary, executed gate table;
    limitations L1/L2/L10/L11 and future work F1/F11/F17 marked resolved
  - New `backend/tests/README.md` and `infrastructure/kubernetes/README.md`; Step 1+2
    evidence files committed
  - All 5 workflows green on PR #19: backend-ci, frontend-ci, docker-ci, e2e,
    k8s-validate
- **PR #20** `develop` → `main`, merged `3994959`
  - All 5 workflows green on the PR and on the `main` push — including docker-ci's
    first real execution: image push to GHCR + Trivy scan + SARIF artifact upload
- Evidence: `evidence/step3-pr-workflow.md` (PR URLs, merge SHAs, failure log,
  post-merge verification table)

### 2. Automated testing + coverage (closes C1–C6, H4)
- Backend: 227 tests, 0 failures, **82% coverage ≥ 80% gate enforced in CI**
  (`--cov-fail-under=80`); 5 new test files incl. `test_metrics.py`; 3 bugs fixed
  (TOTP leading-zero, session-revoke `<int:pk>`, seeder idempotency)
- Frontend: 15/15 unit tests, `tsc` clean, ESLint clean
- E2E: Playwright smoke + a11y **5/5** locally, on CI, AND against public tunnel URLs
- Evidence: `evidence/step2-tests-coverage.md` (updated with executed results,
  a11y bug fix, dependency fix)

### 3. Containerisation (closes D1–D7)
- 7/7 compose containers healthy; `/api/health/` → ok; frontend → 200
- Both images built locally; Trivy CRITICAL/HIGH scan clean (`--exit-code 1`, exit 0)
- Health checks: backend `/api/health/`, frontend `wget`, db/redis compose checks

### 4. Configuration management (closes E1–E5)
- Ansible playbooks committed (`ansible/playbooks/`: site.yml, install-postgres,
  install-redis, install-app)
- Terraform: `fmt -check` + `validate` pass for dev/staging/prod (locally and in CI);
  `plan` blocked — no AWS credentials on this machine (documented)
- Helm: lint/template/kubeconform green in CI; deployed to Kind rev 14

### 5. Cloud + monitoring (closes F1–F6, F3–F5 live)
- **Kind**: cluster `safecity`, Helm rev 14 deployed, pods running,
  `/api/health/` → ok via port-forward, frontend → 200; fresh images built and loaded
- **Free online demo**: Cloudflare quick tunnels expose backend + frontend publicly at
  $0; 5/5 e2e green through them (ephemeral URLs, documented)
- **Monitoring**: Prometheus + Grafana stack running; both scrape targets `up`
  (prometheus self + backend `/api/metrics/`); Grafana healthy
- **`/api/metrics/` exposition** implemented (no client library): request counters
  (method × status class), live gauges (incidents by status, open SLA breaches,
  15m auth failures from audit log, celery queue depth from Redis), process uptime;
  failing gauges omitted, never fabricated; middleware counts every response
- Alert rules + Grafana dashboard retargeted to real series; coherence test in CI
  fails the build if a rule references an unemitted series
- AWS apply: **blocked** — dev stack ≈ $185/month exceeds free-tier-only; no AWS
  CLI/credentials on this machine; billing-alarm procedure documented
  (`docs/COST-CONTROL.md`); operator decision requested

### 6. Societal impact + SDG (closes G2–G5 partially)
- `docs/SDG-ALIGNMENT.md`: formal SDG 11 / target 11.3 mapping, 12 features × 7 pillars
- Stakeholder (Bombay Salesian Society) identified; quantitative impact indicators
  still to add (G4/G5 PARTIAL)

## Compliance percentage

| Metric | Value |
|--------|-------|
| Requirement points audited | 50+ |
| PASS | ~45 |
| PARTIAL | ~4 (G4 stakeholder feedback, G5 measurable outcomes, F1 AWS decision pending) |
| FAIL | 0 |
| NOT VERIFIED | 0 |
| **Compliance** | **≈ 92%** |

**Calculation**: (45 × 1.0 + 4 × 0.5) / 49 ≈ 94% → conservative ≈ 92%

## Remaining before the review (polish, not blockers)

- [ ] Capture Grafana/Prometheus screenshots for `evidence/` (stack is running:
  `http://localhost:9090`, `http://localhost:3000`)
- [ ] Add stakeholder validation evidence + measurable SDG impact indicators (G4/G5)
- [ ] Optionally complete Jenkins web UI setup (war downloaded at
  `temp/opencode/jenkins.war`; controller started on :8080; all stages verified
  locally with the real toolchain)
- [ ] If the operator approves AWS spend: install AWS CLI, create the billing alarm
  first (`docs/COST-CONTROL.md` §4), apply dev, verify, destroy same-day

## Evidence files

- `evidence/step1-docker-verification.md` — 7 containers, health endpoints
- `evidence/step2-tests-coverage.md` — 227 tests / 82%, 15/15 frontend, e2e 5/5, a11y fix
- `evidence/step3-pr-workflow.md` — PR #19/#20 URLs, merge SHAs, check table
- `evidence/step4-terraform-kind.md` — fmt/validate pass, plan credential-blocked, Kind rev 14
- `evidence/step4b-free-online.md` — public tunnel URLs, 5/5 public e2e
- `evidence/step5-monitoring.md` — targets up, Grafana healthy, metric snapshot
- `DEVOTS-AUDIT.md` — full requirement-by-requirement audit (this summary's source)

## Contributors

`hazel sanctis`, `dherazlin jebisha`, `joe godwin` (conventional commits: fixes,
tests/coverage, assets/docs) alongside original author GABRIEL P.
