# SafeCity — Viva Questions and Answers

Model answers, grounded in the delivered code. Where the honest answer is "that is not
built yet", it says so — with the reasoning for the decision that *was* made. Conceding a
known gap and explaining the trade-off reads far better than being caught overstating.

---

## A. Problem and scope

**A1. What problem does SafeCity solve?**

Civic complaints arrive through fragmented channels — phone, WhatsApp, walk-ins,
departmental inboxes — and nobody can say what is outstanding, who is working on it, or
whether "forwarded" meant anything. The failure is not the intake form; it is the missing
workflow and the missing accountability. SafeCity enforces a state machine, computes and
tracks deadlines, keeps an immutable audit trail, and lets the citizen see and dispute the
outcome — while protecting reporter privacy.

**A2. Is this an emergency service?**

No, and it deliberately does not present itself as one. The README, the UI, and this
documentation all say so. Emergencies are surfaced and escalated to a human; nothing is
auto-dispatched, and there is no integration with any official system.

**A3. Who are the users?**

Six roles: citizens, volunteers, department staff, emergency responders, city
administrators, and superusers. Each has a distinct permission surface, enforced
server-side — see [ROLES-AND-ACCESS.md](ROLES-AND-ACCESS.md).

**A4. What is explicitly out of scope?**

Official emergency dispatch, real government system integration, native mobile apps,
payments/fines, and automatically applying AWS infrastructure. Each is excluded with a
stated reason rather than left ambiguous.

---

## B. Architecture

**B1. Why a Django monolith rather than microservices?**

At this scale — under 10,000 incidents a month — microservices add network failure modes,
distributed transactions, and operational overhead without adding capability. A modular
monolith with clear app boundaries (`accounts`, `incidents`, `notifications`, `analytics`,
`audit`, `ai`) is easier to test, deploy and explain. If a specific app later needed
independent scaling, its boundary is already drawn.

**B2. Why PostgreSQL specifically?**

Three features are load-bearing: `tsvector` full-text search for incident search, JSONB for
audit change diffs and integration settings, and partial unique constraints (one default
saved location per user, one active SLA rule per category/severity). This is also why the
test suite has **no SQLite fallback** — testing against a different engine would miss
precisely the features the design depends on.

**B3. Why is there a service layer?**

Every state-changing operation routes through `apps/*/services.py`. Viewsets stay thin.
This means workflow rules cannot be bypassed by a management command, a Celery task, or the
Django admin, because those paths call the same services. Authorization enforced in a view
is only enforced for callers who happen to use that view.

**B4. How do you handle the PostGIS dependency?**

By not having one. Location is `DecimalField` lat/lng with a composite B-tree index, and
nearby search uses haversine in `apps/incidents/views.py`. This avoids a hard PostGIS build
dependency while keeping clustering and heatmaps working, and the abstraction allows a
later swap to PostGIS without changing the API.

**B5. Why UUID primary keys?**

Non-guessable identifiers on a public surface. With sequential integer keys, `/incidents/42/`
tells an attacker how many incidents exist and invites enumeration. Note that this is only
half the protection — the other half is that unauthorized access returns **404**, not 403,
so existence is not confirmed either.

**B6. Why is the frontend a SPA?**

Fast iteration with Vite, typed contracts against the generated OpenAPI schema, and one
deployment artifact. The cost — no SSR, and a token in `localStorage` — is a deliberate,
documented trade-off.

---

## C. The workflow

**C1. Walk me through the incident lifecycle.**

`draft → submitted → under_review → verified → assigned → in_progress → resolved →
closed`, with `rejected`, `duplicate`, `awaiting_info`, `escalated` and `reopened` as
branches. The full matrix is in [ROLES-AND-ACCESS.md](ROLES-AND-ACCESS.md#4-the-workflow-transition-matrix).

**C2. How is an illegal transition prevented?**

`TRANSITIONS` in `apps/incidents/services.py` is a declarative `{from: {to: {roles}}}` map.
`change_status()` checks it before writing anything and raises `WorkflowError` if the
transition is not permitted. The check, the mutation, the history row, the audit row and the
notification fan-out all commit or roll back together.

**C3. What status code does an illegal transition return?**

**400**, with `code: "invalid_transition"`. Note this honestly: `docs/ARCHITECTURE.md`
specifies 409, and the delivered behaviour is 400 because `WorkflowError` subclasses DRF's
`ValidationError`. The tests assert 400. Clients should branch on `code`, not the status
code — which is why the error envelope carries a machine-readable code at all.

> Related: the code field was previously being *overwritten* with DRF's generic `"invalid"`,
> which silently defeated the whole point. That was found and fixed during this work; the
> exception handler now preserves an explicitly raised code. It is a good example of why
> "the tests pass" is not the same as "the contract holds" — no test asserted the code value.

**C4. Why can staff not mark an incident `verified` when it is `submitted`?**

They can — `submitted → under_review` is theirs, and `under_review → verified` is theirs.
`submitted → verified` directly is restricted to admins. The distinction is that claiming
and verifying are separate steps, so "who looked at this" is answerable from the timeline.

**C5. Why require evidence to resolve?**

A resolution that cannot be inspected is indistinguishable from a ticket someone closed to
clear their queue — and the citizen can reopen it precisely because they can see that. It
also creates the record needed to answer a later question about what was actually done.

**C6. Who can reopen, and why?**

The reporter (for their own resolved or closed incident), plus admins/superusers. If the fix
is not real, reopening carries the original context forward, which is more useful than a
fresh report.

---

## D. Security and privacy

**D1. How is authorization enforced?**

Three independent layers: a DRF permission class (what kind of user is this?), an
object-level check (may they touch *this row*?), and a service-layer workflow check (is this
transition legal from here?). Each answers a different question, so none can substitute for
another. The frontend route guards are UX only and are treated as bypassable.

**D2. Why 404 instead of 403 for objects you cannot see?**

A 403 confirms the object exists. That is exactly the enumeration signal an attacker probing
for a neighbour's report is looking for.

**D3. How are stolen tokens limited?**

Access tokens live 15 minutes; refresh tokens rotate with `BLACKLIST_AFTER_ROTATION`. A
replayed rotated token fails, so a stolen refresh token goes useless as soon as the
legitimate client refreshes. Users can list and revoke sessions individually.

**D4. What is the biggest residual security risk?**

Tokens in `localStorage`. `localStorage` is readable by any script that achieves XSS, which
is why the XSS controls carry the weight here: React's default escaping, no
`dangerouslySetInnerHTML`, and server-side sanitization of announcement bodies. A
refresh-token-only httpOnly cookie would remove this class of risk and is the natural next
step.

> Also worth naming unprompted: **CSP is not configured**, despite `ARCHITECTURE.md`
> specifying it. That is a documented deviation, not an oversight the reviewer found first.

**D5. How is the audit trail protected from tampering?**

It is append-only with no API route to create, update or delete rows, and the write happens
in the service layer beneath any permission check — so no role, including superuser, can
bypass it. `AuditLog.actor` uses `SET_NULL` so anonymizing a user does not destroy the trail.

**D6. Is that a legal guarantee of immutability?**

No, and it is worth being precise. The application layer provides no mutation path and a
database superuser could still alter rows directly. True immutability would need
write-once storage or a hash chain. The claim is "no application path can alter it", not
"it cannot be altered".

**D7. How is reporter privacy protected?**

Redaction lives in the serializers, not the views, so an internal model gaining a new PII
field cannot leak it by accident — a public serializer only emits fields it explicitly
declares. Public coordinates are jittered ≥150 m. Public tracking uses unguessable UUID
tokens rather than reference numbers alone.

**D8. Is the coordinate jitter cryptographically sound?**

No, and I would not claim it is. Jitter is applied per public request, so correlating
several reports about the same location could narrow the true position. A
differential-privacy budget is the correct evolution. The current control stops the easy
attack — reading an exact home address off a public page — not a determined one.

**D9. How does account deletion coexist with the audit trail?**

`soft_delete()` erases name, phone and email, sets an unusable password, and retains the
row. Personal data is destroyed; the accountability record's structural integrity is not.
Erasing the trail entirely would let anyone with a brief session destroy accountability for
past actions.

**D10. Why is deletion a manual admin step?**

Automatic irreversible deletion on request is trivially weaponized by an attacker who
briefly holds a session.

---

## E. Data and performance

**E1. How are reference numbers generated without collisions?**

`allocate_reference_number()` uses `get_or_create` (tolerating the two-worker race) then
`SELECT … FOR UPDATE` on the counter row, holding the lock until the surrounding transaction
commits. The counter increment and the `Incident` insert commit together. It is a table
rather than a Postgres sequence so it stays inspectable, resettable per year, and portable.

**E2. Which indexes matter most?**

`status`, `severity`, `sla_deadline`, and `(latitude, longitude)` for the queue and map
queries; a **GIN** index on `search_vector` for full-text search; and
`Notification(recipient, read_at)` for the unread-count hot path.

**E3. How do dashboards stay fast as history grows?**

`DailyIncidentAggregate` stores one row per `(date, ward, category, department)` — including
`avg_response_minutes` and satisfaction as a **sum and a count**, not an average, because
averaging averages is wrong. It is built nightly by `aggregate_daily` at 00:30.

> Honest caveat: the live `/analytics/summary/` endpoint currently queries incidents
> directly rather than reading those aggregates, so very large windows are slower than the
> design intends. The aggregate table exists and is populated; switching the endpoint to
> read it is the remaining work.

**E4. Why store severity and status as `CharField` with choices rather than a DB enum?**

Adding a status becomes a validation change, not a schema change — avoiding the awkward
`ALTER TYPE` migration path on PostgreSQL, which cannot run inside a transaction in older
versions and is a common source of deployment pain.

**E5. Why not store an average satisfaction?**

Because you cannot combine averages. Given per-ward averages you cannot compute the
city-wide average without the underlying counts. Storing `satisfaction_sum` and
`satisfaction_n` makes the rollup arithmetic correct.

---

## F. Testing and quality

**F1. What is the test strategy?**

Three layers: pytest + pytest-django for auth, RBAC, incident CRUD, workflow, media
validation and audit; Vitest + React Testing Library for components; Playwright for the
full citizen → authority → resolution → feedback loop against a seeded stack. Gates: 80%
backend, 70% frontend statements.

**F2. How is the RBAC matrix tested?**

`backend/tests/test_rbac.py` parametrizes over roles × endpoints, so adding a role or
endpoint surfaces missing coverage rather than silently going untested.

**F3. Why does the backend suite need PostgreSQL?**

It depends on `tsvector`, JSONB, GIN indexes and partial unique constraints. A SQLite
fallback would test the parts of the system that need testing least. The practical
consequence — and the thing to know when debugging — is that **if `pytest` appears to hang,
it is almost certainly waiting on an unreachable database**, not hanging on a deadlock.

**F4. What makes tests deterministic?**

`config/settings/test.py`: MD5 password hashing (speed only), throttles disabled with rates
still declared (scoped throttle classes resolve rates at instantiation), Celery eager,
LocMem cache, in-memory channel layer, LocMem email, and `--reuse-db`.

**F5. Are the quality gates actually enforced?**

Not yet, and I would rather say so. `CONTRIBUTING.md` requires backend tests, frontend
tests, typecheck, lint, Docker build, Trivy, and Terraform fmt/validate before merge — but
`.github/workflows/` is **empty**. The commands all work via `make`; the automation that
runs them on every PR is not written. That is the largest single delivery gap.

---

## G. DevOps and deployment

**G1. How do you deploy?**

Docker Compose for local and demo use, a Helm chart for Kubernetes, and Terraform for AWS.
The chart ships `values-dev/staging/prod` overlays with real differences in replica counts,
PDBs, secrets handling and node capacity.

**G2. Why are migrations a separate Helm hook rather than an entrypoint?**

Running migrations from a Deployment entrypoint means N replicas race the same migration and
a failed rollout becomes ambiguous — you cannot tell whether the old or new schema is live.
The chart runs them as a `pre-install,pre-upgrade` hook with `--noinput`, so a broken
migration aborts the release.

**G3. Why does only one Celery beat run?**

Two schedulers both fire every scheduled job, double-counting SLA breaches and raising
duplicate escalations. The Deployment uses the `Recreate` strategy so it is never
momentarily 2 during a rollout — not merely `replicas: 1`.

**G4. Why does liveness not check the database?**

Liveness hits `/api/health/`, which checks nothing. Readiness hits `/api/readiness/`, which
checks DB, cache and storage and returns 503 with a per-dependency map. Probing readiness for
liveness would restart healthy pods during a database blip and turn an outage into a
crash loop.

**G5. What does the Kubernetes chart deliberately not do?**

It does not create PostgreSQL or Redis. They are expected to be managed services. The
`safecity.dbHost` and `safecity.redisUrl` helpers use `required`, so a missing endpoint fails
at render time with a readable message instead of producing a Service name that does not
exist and a CrashLoopBackOff that takes an hour to diagnose.

**G6. Why is the frontend container running as root?**

The shipped `nginx:1.27-alpine` image's master process needs root to bind `:80`. The chart
reduces it to `NET_BIND_SERVICE` alone with a read-only root filesystem and documents the
rebuild recipe on `nginx-unprivileged` (uid 101, port 8080) — exposed as a `frontend.unprivileged`
flag that switches the port and security contexts automatically. It is a known gap, not an
oversight, and it is tracked as a security deviation.

**G7. Can NetworkPolicy be relied on?**

Only with a CNI that enforces it — Calico, Cilium, or AWS VPC CNI network policies. On a
cluster whose CNI ignores these objects, they apply cleanly and enforce nothing, which is a
silent no-op. Worth stating because it is a common false sense of security.

**G8. What does the AWS deployment cost?**

Roughly $185/month for dev, $370 staging, $460 production — and critically, **~$114/month
for dev even completely idle** (EKS control plane ~$73 plus one NAT gateway ~$41). That is
why [COST-CONTROL.md](COST-CONTROL.md) leads with it, the Makefile's apply/destroy targets
refuse to run, and the honest advice is that a `terraform plan` demonstrates the same
engineering competence as an apply at zero cost.

---

## H. Honest limitations

**H1. What is not finished?**

State it plainly:

1. **CI workflows** — `.github/workflows/` is empty, so the documented gates run manually.
2. **Django admin** — no application models are registered; every `admin.py` is the default
   stub. Reference data is therefore managed by the seed command or the shell.
3. **Kustomize overlays** — `infrastructure/kubernetes/` is empty. Helm is the delivered path.
4. **Realtime notifications** — a Channels consumer exists at `ws/notifications/`, but no
   browser client is wired, so the SPA polls. `socket.io-client` is an unused dependency and
   is the wrong protocol for a Channels backend.
5. **CSV export hardening** — citizen-authored text can land in a spreadsheet cell starting
   with `=`, `+`, `-` or `@`. Formula injection is not neutralized.
6. **Malware scanning** — the provider interface exists; the implementation is a no-op mock.
7. **Retention sweep** — anonymizing closed incidents after a configurable period is
   modelled but not implemented.
8. **`export.pdf`** returns print-ready HTML, not a PDF, despite the path name.
9. **Role permissions** — `ROLE_PERMISSIONS` maps no codenames; enforcement comes from
   permission classes and the transition matrix instead.
10. **Frontend container runs as root.**

**H2. Why not just hide the gaps?**

Because a reviewer who finds an undisclosed gap stops trusting everything else. Disclosing
them also demonstrates that the limits were understood rather than stumbled into.

**H3. What would you do with another month?**

In priority order: (1) CI workflows, since they protect everything else; (2) register the
Django admin models or build admin CRUD for reference data — the current shell-only workflow
is the weakest part of the product; (3) harden CSV export and add CSP; (4) wire the WebSocket
client and drop the unused `socket.io-client` dependency; (5) point analytics at the
pre-aggregated table; (6) implement the retention sweep and a real malware scanner.

---

## I. Design judgement

**I1. What was the hardest trade-off?**

Resolution by the citizen. Requiring the reporter to confirm means work is not "done" until
a non-expert agrees, which can leave items open longer than a department would like. The
alternative — letting the department declare closure unilaterally — is the exact failure
mode the platform exists to fix. So the citizen confirms, and reopening is a first-class
transition rather than a support request.

**I2. Which decision would you defend hardest?**

That AI can never cause a workflow transition. Every suggestion is stored with its provider,
confidence, and the human's accept/edit/reject decision. This costs convenience — nothing is
auto-classified — and buys something worth more: when a decision is questioned months later,
there is a record of what was proposed, how confident the system was, and who chose
otherwise. An auditable system cannot have steps with no accountable author.

**I3. What would you change if you started again?**

Nothing architectural. The one thing I would change is sequencing: put CI in place before the
first feature. The gates are documented and the commands work, but having written them last
means every earlier change went uncovered by automation. Test infrastructure is cheap when
it is early and expensive when it is retrofitted.

**I4. What is the most defensible thing about this project?**

That it degrades to zero credentials. Missing S3 falls back to local disk, missing SMTP to
the console, missing AI to a mock. `docker compose up` produces a complete working system
with no cloud accounts. That constraint forced every optional dependency behind an interface,
which is why the external systems are genuinely pluggable rather than nominally so.
