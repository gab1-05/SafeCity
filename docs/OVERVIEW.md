# SafeCity — Project Overview

## 1. Problem statement

Indian cities receive civic complaints through fragmented channels: helpline calls,
WhatsApp forwards, social media posts, walk-in visits, and departmental email inboxes.
This fragmentation produces well-documented, expensive failure modes:

| Problem | Consequence |
|---------|-------------|
| **No single intake channel** | A pothole reported by phone is invisible to the app team; the same pothole is reported five times and worked on twice. |
| **No shared status vocabulary** | "We forwarded it" is indistinguishable from "it is fixed". Citizens cannot tell whether a report is being worked on. |
| **No accountability trail** | Once a complaint leaves the citizen's hands, there is no record of *who* acted, *when*, or *why* it was closed. |
| **No SLA discipline** | Without deadlines, low-visibility problems (streetlights, garbage) are starved in favour of whatever was escalated loudest. |
| **No prioritisation signal** | A fallen live wire and a faded road marking enter the same queue, in arrival order. |
| **No feedback loop** | Citizens stop reporting because reporting appears to accomplish nothing, which reduces the city's own signal. |

The *technical* problem is therefore not "make a complaint form". A civic incident
platform is a **workflow and accountability system**: it must route reports to the
correct department, enforce a state machine so status is unambiguous, compute and
enforce deadlines, keep an immutable audit trail, and give citizens a way to see and
dispute outcomes — all while protecting reporter privacy, because reports frequently
contain location and identity data about the person reporting.

## 2. Objectives

| # | Objective | How SafeCity meets it | Where it lives |
|---|-----------|----------------------|----------------|
| O1 | Single intake for civic incidents | One reporting wizard covering category, location, evidence, and severity; anonymous reporting supported | `apps/incidents` |
| O2 | Correct routing | Every category declares an owning department; incidents inherit it and can be assigned to staff | `IncidentCategory.default_department` |
| O3 | Unambiguous lifecycle | A declarative transition matrix; illegal transitions are rejected with a machine-readable error, not silently ignored | `apps/incidents/services.py` `TRANSITIONS` |
| O4 | Deadline discipline | SLA rules per (category, severity) compute a stored deadline; a Celery sweep flags breaches | `core.SLAConfiguration`, `incidents/tasks.py` |
| O5 | Accountability | Every state change writes an append-only `AuditLog` in the same transaction | `apps/audit` |
| O6 | Citizen visibility | Unguessable-token public tracking links plus reference lookup, with PII stripped | `views_public.py` |
| O7 | Prioritisation | Severity + urgency + emergency flag drive queue ordering and escalation | `apps/incidents` |
| O8 | Privacy by construction | Public serializers redact identity and jitter coordinates | `SERIALIZERS`, `PUBLIC_COORD_JITTER_METERS` |
| O9 | Operational insight | Role-scoped analytics and CSV export over incidents, SLA and workload | `apps/analytics` |
| O10 | Zero-credential demo | Email, SMS, AI, and object storage all degrade to mocks | adapter interfaces |

## 3. Scope

### In scope

- Citizen registration, authentication, and profile/privacy management.
- Incident submission with media, location, and optional anonymity.
- Departmental workflow: verify → assign → work → resolve → confirm/close, plus
  reject, duplicate/merge, escalate, reopen.
- SLA computation, breach detection, and escalation sweeps.
- Notifications (in-app, WebSocket, email/SMS adapters) with per-user preferences.
- Role-scoped dashboards, maps, queue management, and analytics.
- Audit logging and administrator tooling.
- Deployment packaging: Docker Compose, Helm chart, Terraform modules, and CI workflows.

### Out of scope (and honestly labelled as such)

| Excluded | Rationale |
|----------|-----------|
| Official emergency dispatch | SafeCity is explicitly *not* an emergency service; emergencies are surfaced and escalated to a human, never auto-dispatched. |
| Government system integration | No municipal API is consumed or claimed. All external systems are adapters behind an interface. |
| Native mobile applications | The SPA is responsive to 360 px; native apps are future work. |
| Payments, billing, or fines | Not part of civic incident coordination. |
| Automatically applying AWS infrastructure | Terraform is delivered as code and reviewed, never applied without explicit approval. |

## 4. Stakeholders

| Stakeholder | Interest | Primary interface |
|-------------|----------|-------------------|
| **Citizens / residents** | Report problems, track progress, confirm fixes | Public site + citizen dashboard |
| **Volunteers** | Support verified incidents, observe community activity | Community views |
| **Department staff** | Work an assigned queue within SLA | Authority dashboard + queue |
| **Emergency responders** | Handle high-severity and emergency incidents fast | Emergency queue + escalations |
| **Department heads / supervisors** | Workload balance, escalation handling | Analytics + escalation views |
| **City administrators** | Configure categories, SLAs, users, and departments | Admin tools + audit log |
| **Superusers** | Full platform control, break-glass access | Django admin |
| **The Bombay Salesian Society (evaluators)** | Assess architecture, process, and delivery quality | This documentation package |
| **Privacy / governance reviewers** | Verify PII handling and consent | Security & privacy doc, audit trail |

Stakeholder interests map onto concrete permissions in
[ROLES-AND-ACCESS.md](ROLES-AND-ACCESS.md).

## 5. How SafeCity is different

| Design choice | Practical effect |
|---------------|------------------|
| **Workflow is enforced, not advisory** | Status cannot drift; a transition either passes the matrix or returns an error. There is no "set status to whatever" endpoint. |
| **Auditability is not optional** | Audit rows are written inside the business transaction. No role — including superuser — can skip the trail. |
| **AI can never act alone** | An AI suggestion is stored with provider, confidence, and the human's accept/edit/reject decision. No transition is caused by AI. |
| **Degrades to zero credentials** | `docker compose up` yields a fully working system with no cloud accounts; optional integrations are additive. |
| **Privacy is a serializer concern** | Redaction happens at the boundary, so an internal model gaining a PII field cannot leak it by accident. |
| **Failure is explicit** | Illegal transitions return 409 with a code; readiness returns 503 listing which dependency failed. |

## 6. Success criteria

| Criterion | Target | Verification |
|-----------|--------|--------------|
| End-to-end incident loop | Citizen report → verification → assignment → resolution → citizen confirmation | Playwright E2E suite (`make test-e2e`) |
| Workflow integrity | 100% of transitions pass the matrix; forbidden transitions rejected | `backend/tests/test_incidents.py` |
| RBAC correctness | Permission matrix enforced server-side per role | `backend/tests/test_rbac.py` |
| Audit completeness | Every state change produces an audit row | `backend/tests/test_blocker_regressions.py` |
| Backend coverage | ≥ 80% statements | `make coverage` |
| Frontend coverage | ≥ 70% statements on `src/` | `make test-frontend` |
| Zero-credential startup | Full stack runs from a bare clone | `make docker-up && make migrate && make seed` |
| Privacy | No reporter PII in any public response | Public serializer snapshot tests |

> Coverage and E2E gates are defined but **CI is not yet wired up** — see
> [Known limitations](PROJECT-MANAGEMENT.md#2-known-limitations) for the current, verified
> state of each of these criteria.

## 7. Document map

- **What to build** → [REQUIREMENTS.md](REQUIREMENTS.md)
- **How it is built** → [ARCHITECTURE.md](ARCHITECTURE.md), [DATA-MODEL.md](DATA-MODEL.md), [API-REFERENCE.md](API-REFERENCE.md)
- **Who may do what** → [ROLES-AND-ACCESS.md](ROLES-AND-ACCESS.md)
- **Under what guarantees** → [SECURITY-AND-PRIVACY.md](SECURITY-AND-PRIVACY.md)
- **How to run it** → [INSTALLATION-GUIDE.md](INSTALLATION-GUIDE.md)
