# SafeCity — Project Management

Milestone status, risk register, maintenance, known limitations, and future work.

---

## 1. Milestone status

The plan in `docs/ARCHITECTURE.md` §18 defined 16 phases. Status below reflects a **verified
inspection of the delivered code**, not an assumption that a phase was completed because it
was scheduled.

| # | Milestone | Gate | Status |
|---|-----------|------|--------|
| 1 | Architecture proposal | Reviewed and approved | ✅ `docs/ARCHITECTURE.md` |
| 2 | Repo scaffold, tooling, git | Builds clean | ✅ Monorepo, Makefile, lint/format config |
| 3 | Models, migrations, admin | `migrate` clean | ⚠️ Models and migrations done; **admin not registered** |
| 4 | Auth + RBAC | Auth tests pass | ✅ JWT, rotation, sessions, lockout, permission classes |
| 5 | Incident APIs + workflow | API tests pass, OpenAPI renders | ✅ Transition matrix, actions, media, drf-spectacular |
| 6 | Frontend shell + design system | Routes render, lint clean | ✅ 19 pages, 4 layouts, Tailwind + Radix |
| 7 | Citizen reporting | E2E submit happy path | ✅ 7-step wizard, maps, media, anonymity |
| 8 | Authority dashboard | Workflow panel functional | ✅ Operations, queue, incident workflow |
| 9 | Maps / analytics / notifications / AI | Dashboards live | ⚠️ Maps, analytics and AI done; **realtime client missing** |
| 10 | Test suites | Coverage gates met | ⚠️ Suites written; **coverage not measured** (needs PostgreSQL) |
| 11 | Docker | `docker compose up` demo-ready | ✅ Dev + production-like stacks |
| 12 | K8s / Helm | `helm lint` + kubeconform pass | ⚠️ Chart delivered; **lint never run**; Kustomize dir empty |
| 13 | Terraform | `fmt`/`validate` pass, no apply | ⚠️ Modules complete; **`fmt`/`validate` never run** |
| 14 | CI/CD | All workflows green on PR | ❌ **`.github/workflows/` is empty** |
| 15 | Security review | Checklist complete | ⚠️ App layer strong; CSP and container hardening outstanding |
| 16 | Docs | SDP package complete | ✅ This package |

**Honest summary:** phases 1–2, 4–9, 11 and 16 are complete. Phases 3, 9, 10, 12, 13 and 15
are substantially delivered with named gaps. Phase 14 is not started.

### Unexecuted verification gates

These gates are defined by the plan but have not been run in the environment where this
documentation was written. They are the first thing to run before any evaluation:

| Gate | Command | Run? |
|------|---------|------|
| Backend tests + coverage | `make test`, `make coverage` | ❌ needs PostgreSQL |
| Frontend tests + typecheck | `make test-frontend`, `npm run typecheck` | ❌ |
| E2E | `make test-e2e` | ❌ |
| Helm lint / template | `helm lint`, `helm template` | ❌ Helm not installed |
| Kubeconform | `kubeconform` | ❌ not installed |
| Terraform fmt / validate | `terraform fmt -check -recursive`, `terraform validate` | ❌ Terraform not installed |
| Docker build | `make docker-build` | ❌ |

A gate that has never executed is an assumption, not a result. Treat every "✅" above as
"implemented and inspected", and none as "verified by a passing pipeline" until those
commands have been run.

---

## 2. Known limitations

Everything the implementation does not currently do, consolidated. The source of truth for
each item is the code, not this list — but this list is the honest inventory.

### 2.1 Delivery and infrastructure

| # | Limitation | Impact | Where |
|---|-----------|--------|-------|
| L1 | **`.github/workflows/` is empty.** No CI runs on PRs despite `CONTRIBUTING.md` requiring it. | Gates are manual; regressions reach `develop` uncaught | CI/CD |
| L2 | **`infrastructure/kubernetes/` is empty.** Kustomize overlays were planned, never written. | Helm is the only path; an empty directory implies a deliverable that does not exist | K8s |
| L3 | **`scripts/dev-entrypoint.sh` is referenced nowhere.** No `ENTRYPOINT` uses it, and compose overrides `command`. | Dead code; its DB-wait logic is unused | Docker |
| L4 | **`.dockerignore` / `frontend/.gitignore`** exist but are not consistently applied to build context. | Larger build contexts than necessary | Docker |
| L5 | **`docs/api-schema.yaml` is not generated in the repo.** | Consumers must read the live Swagger UI or run `make openapi` | Docs |

### 2.2 Administration

| # | Limitation | Impact | Where |
|---|-----------|--------|-------|
| L6 | **No Django admin models registered.** Every `admin.py` is the default stub, so `/admin/` exposes no application data. | `ARCHITECTURE.md` presents the admin as a headline benefit; in practice reference data is shell-managed | `apps/*/admin.py` |
| L7 | **Reference data is read-only over the API.** Departments, categories, wards, zones and SLA rules cannot be created or edited through the UI or API. | An admin cannot add a category or change an SLA deadline without shell access | `departments/views.py`, `core/viewsets.py`, `incidents/views.py` |
| L8 | **`ROLE_PERMISSIONS` maps no permission codenames.** `sync_roles` creates groups but grants nothing. | The group-based permission model is inert; enforcement relies on permission classes and the transition matrix | `accounts/roles.py` |
| L9 | **No `IntegrationConfiguration` or `APIKey` management API.** | Toggling integrations requires shell or direct DB access | `core/models.py` |

### 2.3 Application features

| # | Limitation | Impact | Where |
|---|-----------|--------|-------|
| L10 | **No realtime WebSocket client in the frontend.** The Channels consumer exists at `ws/notifications/`; the SPA polls. | "Real-time notifications" are, in practice, polling | `notifications/consumers.py` |
| L11 | **`socket.io-client` is an unused frontend dependency, and the wrong protocol.** Socket.IO cannot talk to a Django Channels consumer. | Misleading dependency; inflates the bundle if imported | `frontend/package.json` |
| L12 | **`export.pdf` returns print-ready HTML, not a PDF.** Content type is `text/html`; filename suggests PDF. | Contract is misleading; no real PDF pipeline | `incidents/views.py` |
| L13 | **Retention sweep not implemented.** Anonymizing closed incidents after a configurable period is modelled but not scheduled. | Closed incidents retain data indefinitely | `PROJECT-MANAGEMENT` / model comment |
| L14 | **Analytics summary queries incidents directly** rather than reading `DailyIncidentAggregate`. | Large date windows are slower than the design intends | `analytics/views.py` |
| L15 | **Draft incidents are modelled but the draft flow is incomplete.** | `draft` exists in the status enum without a full save/resume path in the UI | `incidents/models.py` |
| L16 | **AI features cover category, severity and duplicate only.** Summarization, toxicity, translation and entity extraction are enum values without implementations. | `AIRecommendation.KINDS` overstates delivered capability | `ai/models.py` |
| L17 | **`IncidentCategory.subcategory` is a free-text string**, not a managed taxonomy. | Cannot reliably aggregate by subcategory | `incidents/models.py` |

### 2.4 Security

| # | Limitation | Impact | Where |
|---|-----------|--------|-------|
| L18 | **No CSP header**, despite `ARCHITECTURE.md` specifying a nonce strategy. | Weakens defence-in-depth against XSS | `settings/base.py` |
| L19 | **Frontend container runs as root.** The nginx master binds `:80`. | Container escape has more room; `frontend.unprivileged` exists but requires a rebuilt image | `frontend/Dockerfile`, chart |
| L20 | **CSV export is not hardened against spreadsheet formula injection.** | A citizen-authored title beginning `=`, `+`, `-` or `@` can execute when opened in Excel/Sheets | `analytics/views.py` |
| L21 | **Malware scanning is a no-op mock.** | `scan_status` is always benign; provider interface only | `MALWARE_SCAN_PROVIDER=mock` |
| L22 | **Argon2 page-hashing is a preference, not a guarantee.** PBKDF2 is used unless `argon2-cffi` is installed. | Claiming Argon2 without checking is unsafe | `settings/base.py` |
| L23 | **Announcement HTML sanitization should be verified** before authoring is opened beyond trusted admins. | Stored-XSS surface | `announcements/` |

### 2.5 Documentation and contract drift

| # | Limitation | Impact |
|---|-----------|--------|
| L24 | `ARCHITECTURE.md` specifies **409** for illegal transitions; the implementation returns **400**. | Clients following the spec would mis-handle errors |
| L25 | `README.md` documented `citizen@safecity.local`; the seed creates `citizen1@`–`citizen5@`. | **Fixed** during this work |
| L26 | `docker-compose.yml` defaulted the backend to port **9080** while the README, Makefile and `VITE_API_BASE_URL` all use **8080**, so `make docker-up` produced a frontend that could not reach the API. | **Fixed** during this work |
| L27 | The API error handler overwrote an explicitly-raised error `code` with DRF's generic `"invalid"`, defeating the machine-readable code that `ARCHITECTURE.md` promises. | **Fixed** during this work |

Items L25–L27 were found and fixed while writing this documentation package. They are
recorded rather than quietly corrected, because the pattern matters: each was a divergence
between a documented contract and the code, and none was caught by the existing test suite.

### 2.6 A note on data loss

While writing this package, **14 files were discovered to be 100% null bytes**: the entire
`infrastructure/helm/safecity` chart (13 files) and `infrastructure/terraform/versions.tf`.
The file sizes were non-zero, so content existed and was zeroed — consistent with a
filesystem crash rather than a bad commit. With no git history in the repository at the time,
the original content was unrecoverable.

The Helm chart and `versions.tf` were **reconstructed** from the design in
`ARCHITECTURE.md` §11 and §13, the file inventory, and the application's actual environment
variables. The reconstruction is documented in
[KUBERNETES-AND-AWS.md](KUBERNETES-AND-AWS.md) and is functionally complete, but it is a
reconstruction: it has not been through `helm lint` or a real deploy. **The lesson is to
commit early** — a repository with no commits has no recovery path at all.

---

## 3. Risk register

| # | Risk | Likelihood | Impact | Mitigation | Status |
|---|------|-----------|--------|------------|--------|
| R1 | Scope exceeds an academic timeline | High | High | Phase gates; mock adapters so every feature degrades; demo data from early on | Managed — gaps are disclosed rather than hidden |
| R2 | **AWS cost surprise** | Medium | High | Dev-size defaults, single shared NAT, SPOT nodes, budget alarms, refusing Makefile targets, `destroy` runbook | Mitigated — see [COST-CONTROL.md](COST-CONTROL.md) |
| R3 | PostGIS unavailable locally | Medium | Medium | Lat/lng + composite index + haversine abstraction; no hard dependency | Resolved |
| R4 | WebSocket complexity behind ALB | Medium | Medium | Polling fallback via the notification API; idle timeouts documented per provider | Partially realised — no browser client yet (L10) |
| R5 | **No CI means regressions reach `develop`** | High | Medium | Suites exist and run via `make`; CI is the outstanding work | **Open (L1)** |
| R6 | AI privacy leak | Low | High | Mock provider by default, scrub layer, opt-in configuration, no transition ever caused by AI | Mitigated |
| R7 | Duplicate detection false positives | Medium | Medium | Threshold tuning; human confirmation required; merging is an explicit admin action | Managed |
| R8 | Large media abuse | Medium | Medium | Size/type/magic-byte caps, rate limits, private bucket with presigned URLs, EXIF stripping | Mitigated |
| R9 | Token theft via `localStorage` | Low | High | 15-minute access TTL, rotation with blacklist, session revocation, XSS controls | Accepted, documented as residual risk |
| R10 | **Container escape, frontend runs as root** | Low | High | Non-root rebuild path documented (`frontend.unprivileged`) | **Open (L19)** |
| R11 | **Reference data becomes unmaintainable** | Medium | Medium | Shell recipes documented in the admin manual | **Open (L7)** |
| R12 | Filesystem corruption destroys uncommitted work | Low | High | Commit early; reconstruct from design docs (demonstrated) | Realised once — see §2.6 |
| R13 | Env-var and ConfigMap drift between local, Helm and compose | Medium | Medium | Chart ConfigMap mirrors `.env.example`; documented as the single mapping | Managed |
| R14 | Free-text CSV opened in a spreadsheet | Medium | Medium | Review before forwarding | **Open (L20)** |

---

## 4. Maintenance

### 4.1 Routine

| Cadence | Task |
|---------|------|
| Per change | `make lint && make format`, run relevant tests |
| Per change | `make openapi` if serializers or viewsets changed |
| Daily | Confirm Celery beat is running exactly once (or SLA sweeps silently stop) |
| Weekly | Review audit log for anomalies; check SLA breach trend |
| Monthly | Dependency updates; review `pip list --outdated`, `npm outdated` |
| Quarterly | Rehearse the backup/restore procedure — an untested backup is not a backup |
| Quarterly | Rotate `SECRET_KEY` (invalidates sessions) and integration credentials |

### 4.2 Dependency updates

```bash
cd backend && .venv/Scripts/python -m pip list --outdated
cd frontend && npm outdated
```

Backend dependencies are pinned by range in `requirements/{base,dev,prod}.txt`. Frontend uses
`npm ci` against `package-lock.json`, so installs are reproducible — update with `npm update`
and commit the lockfile, never hand-edit it.

### 4.3 Backwards compatibility

- The API version lives in the path (`/api/v1/`). Breaking changes go to `/api/v2/`.
- Status and severity are `CharField` + `choices`, so adding a value is a validation change,
  not a schema migration.
- Because a live incident holds a *snapshot* of its SLA deadline, changing SLA policy never
  retroactively rewrites historical performance. This must be preserved: silently moving a
  deadline would corrupt the record the analytics depend on.
- `on_delete=PROTECT` on `Incident.category` and `Ward.zone` means retiring a category or
  zone is a data decision, not a delete — deactivate (`is_active=False`) instead.

### 4.4 Handover checklist

- [ ] `.env` populated and never committed
- [ ] Database backed up and a restore rehearsed
- [ ] `make test`, `make test-frontend`, `make lint` all green
- [ ] `make openapi` run and `docs/api-schema.yaml` committed
- [ ] Demo credentials removed or reset from any non-local environment
- [ ] CI workflows authored and green (L1)
- [ ] Reference data (departments, categories, SLA) verified complete and correctly routed
- [ ] Every `department_staff` account has a `department` assigned
- [ ] Budget alarms configured if AWS is in use

---

## 5. Future work

Ordered by value, with the reasoning for the ordering.

### Priority 1 — protects everything else

| # | Item | Why first |
|---|------|-----------|
| F1 | **Author the CI workflows** (`backend-ci`, `frontend-ci`, `docker-ci`, `terraform-ci`, `k8s-validate`, `e2e`) | Every other item lands on a pipeline that catches regressions. Cheap now, expensive to retrofit |
| F2 | **Register Django admin models, or build admin CRUD for reference data** | The shell-only workflow is the weakest part of the product (L6, L7). A real administrator cannot add a category |
| F3 | **Commit `docs/api-schema.yaml` and add a CI drift check** | Makes the API contract enforceable instead of aspirational |

### Priority 2 — security and correctness

| # | Item | Why |
|---|------|-----|
| F4 | **Add a CSP header** with a nonce strategy | Closes L18; the last significant defence-in-depth gap |
| F5 | **Neutralize CSV formula injection** | Small change, real vector (L20, R14) |
| F6 | **Rebuild the frontend on `nginx-unprivileged`** and enable `frontend.unprivileged` | Closes L19 |
| F7 | **Wire a real malware scanner** behind the existing provider interface | L21 |
| F8 | **Verify or implement announcement HTML sanitization** | L23 |
| F9 | **Point analytics at `DailyIncidentAggregate`** | L14; the design is already there |
| F10 | **Align the error contract with the architecture** — either return 409 as specified or update the spec to 400 | L24; a documented contract that lies is worse than no contract |

### Priority 3 — feature completion

| # | Item | Notes |
|---|------|-------|
| F11 | **WebSocket client in the SPA**, and drop `socket.io-client` | L10, L11. Channels is the protocol; Socket.IO is not |
| F12 | **True PDF export** (WeasyPrint or similar) behind the existing route | L12 |
| F13 | **Retention sweep** anonymizing closed incidents after a configurable period | L13 |
| F14 | **Complete the draft flow** (save, resume, submit later) | L15 |
| F15 | **Implement the remaining AI kinds** — summarization, toxicity, translation, entity extraction | L16 |
| F16 | **Managed subcategory taxonomy** | L17 |
| F17 | **Kustomize overlays** — or delete the empty directory | L2; an empty dir implies a deliverable |

### Priority 4 — scale and refinement

| # | Item |
|---|------|
| F18 | Differential-privacy budget for coordinate jitter, replacing uniform jitter |
| F19 | httpOnly refresh cookie as an alternative to `localStorage`, removing residual risk R9 |
| F20 | PostGIS as an optional backend behind the existing location abstraction |
| F21 | Reported-content moderation queue for comments (the model supports `flagged`/`hidden`; no UI or workflow exists) |
| F22 | Saved-filter sharing across a department |
| F23 | i18n wiring for `en`/`hi`/`mr` — the `language` field and translation adapter exist, but the UI is English-only |
| F24 | OpenTelemetry traces across the API, Celery and the database |

---

## 6. Delivery lessons

Three things this project demonstrates, worth stating because they generalise:

1. **A documented contract is not a tested contract.** The error `code` (L27), the port
   mismatch (L26) and the seed credential drift (L25) were all cases where documentation and
   code disagreed and every test passed. Tests asserted status codes; nothing asserted that
   the *documented* behaviour was real. Contract tests would have caught all three.

2. **Optional dependencies must sit behind interfaces from day one.** The "degrades to zero
   credentials" constraint forced S3, SMTP, SMS, AI and scanning behind adapters. That
   decision is why the demo needs no cloud account, and retrofitting it later would have
   meant rewriting call sites rather than adding a class.

3. **Uncommitted work has no recovery path.** Fourteen files were destroyed by a filesystem
   event and could only be reconstructed from design documentation, because the repository
   had no commits. Commit early and often — it is the only backup that survives a corrupt
   working tree.
