# SafeCity — Demo Script

A rehearsable, timed walkthrough for an SDP evaluation. Total: **~15 minutes**
(12 minutes of demo, 3 minutes of buffer).

> **Open with this sentence, and mean it:** "SafeCity is an incident coordination tool for
> this SDP. It is not an official emergency service and not an integrated government
> system. In a real emergency you call your local emergency number."
>
> Saying this unprompted is stronger than being asked and having to concede it.

---

## Before the audience arrives

```bash
cp .env.example .env
make docker-up            # wait for healthy
make migrate
make seed
```

Verify all three, and **do not skip this**:

```bash
curl -s http://localhost:8080/api/health/       # {"status":"ok",...}
curl -s http://localhost:8080/api/readiness/    # database/cache/storage all ok
curl -s http://localhost:8080/api/meta/config/  # categories present
```

Open and **log in to** these tabs in advance so nothing is typed live:

| Tab | URL | Login |
|-----|-----|-------|
| 1 | http://localhost:5173 | not logged in |
| 2 | http://localhost:5173 | `citizen1@safecity.local` / `Citizen@12345!` |
| 3 | http://localhost:5173/operations | `staff.roads@safecity.local` / `Staff@12345!` |
| 4 | http://localhost:5173/analytics | `admin@safecity.local` / `Admin@12345!` |
| 5 | http://localhost:8080/api/schema/swagger/ | — |
| 6 | http://localhost:8080/api/readiness/ | — |

Have this file open in a seventh tab for reference.

Seeded data: **8 departments · 16 categories · 9 wards in 3 zones · 13 incidents** spread
across every stage of the lifecycle · 5 staff · 1 responder · 1 volunteer · 5 citizens ·
3 announcements.

---

## The narrative arc

> "A citizen reports a problem. Four different roles act on it. Nothing can be done
> silently, nothing can be skipped, and the citizen can dispute the outcome."

That is the whole product. Everything below is evidence for it.

---

## Minute 0–1 · The problem

**Tab 1.** Land on the home page. Do not click anything yet.

> "Civic complaints today arrive by phone, WhatsApp, and walk-in. Nobody can say what is
> outstanding, who is working on it, or whether 'forwarded' means anything. The failure is
> not the form — it is the missing workflow and the missing accountability."

Point at `/track` in the nav.

> "A citizen can track a report without an account. Here's what that page does *not* show:
> who reported it, or exactly where they live."

---

## Minute 1–4 · Citizen reports an incident

**Tab 1 (logged out).** Go to `/track` first, and search the seeded reference.

> "Reference numbers are sequential and human-readable: `SC-MUM-2026-000042`. Public
> tracking works from the reference alone."

**Tab 2 (citizen).** Click **Report an incident** (`/report`). Walk the 7 steps briskly:

1. **Category & title** — pick *Road damage*, title "Large pothole near bus stop".
2. **Description** — "Roughly two feet across, deep enough to throw a two-wheeler."
3. **Location** — click the map to drop a pin. *Pause here.*
   > "The pin is exact. What the public sees is jittered by at least 150 metres. Authorities
   > get the truth; the public gets the neighbourhood."
4. **Severity** — *High*.
5. **Media** — attach any image. Mention: "Type, MIME and magic bytes are validated
   server-side, EXIF is stripped, and a thumbnail is generated asynchronously. A browser
   check is not the boundary."
6. **Options** — point at anonymous reporting. *Do not toggle it yet.*
   > "Note the trade-off: anonymity means no notifications, because the system no longer
   > knows who to notify."
7. **Review** → Submit.

**Read the reference number aloud** and write it on the whiteboard.

> "That number was allocated under a row lock, so two simultaneous submissions cannot
> collide on it."

**Optional 30 seconds — the workflow guarantee.** With the incident open, try an illegal
action, e.g. resolve it directly. Show the rejection:

```json
{ "detail": "Transition submitted → resolved is not allowed for you.", "code": "invalid_transition", "errors": {} }
```

> "Status transitions are a matrix, not a free-text field. The client can branch on `code`
> without parsing prose."

---

## Minute 4–7 · Staff work the queue

**Tab 3 (staff).** `/operations` — point at the KPI strip (open, awaiting verification,
high priority, overdue, emergency, SLA compliance).

> "This is scoped to the Roads department. A Water department user sees a different number,
> and that scoping is enforced on the server. The frontend hiding a menu is not a security
> control."

Go to `/queue`.

- Sort by SLA deadline; note overdue flags.
  > "Priority is severity and deadline, not arrival order. A water leak does not wait behind
  > a road marking because the road marking arrived first."
- Open the seeded "Large pothole on main road".
- **Verify** → **Assign** (mention workload-aware auto-assignment picking the least-loaded
  staff member).
- **Start work** → **Resolve**, entering a summary *and* evidence. Emphasize:
  > "Resolution requires evidence. A resolution that cannot be inspected is
  > indistinguishable from a ticket someone closed to clear their queue."
- Add an **internal note**.
  > "Authority-only. The citizen never sees this — and note it is audited, so it is a
  > professional record, not a private chat."

---

## Minute 7–9 · Citizen confirms or disputes

**Tab 2 (citizen).** Open `/notifications`.

> "She was notified when it was verified, assigned, and resolved."

Open the incident → **Confirm** with a 5-star rating.

> "If the fix were not real, she could reopen it instead. Reopening is a first-class
> transition, not a support request. That is why the citizen can be told the truth about
> status — the status is not final until she agrees."

**Show the timeline** — point at the entries and the actor on each.

---

## Minute 9–11 · Authority view

**Tab 4 (admin).** `/analytics`.

- Change the date range.
- Point at SLA compliance, average response and resolution times.
- Export CSV.
  > "Same numbers as JSON, and note this endpoint returns 403 for a citizen — analytics are
  > not citizen-facing."

Go to `/admin/audit`.

> "Every state change writes an audit row in the *same transaction* as the change. So a
> committed change can never lack its audit entry. There is no API route to edit or delete
> these, and no role bypasses it — including superuser, because the write happens beneath
> the permission check."

Filter by the incident you just changed. Show actor, diff, and `request_id`.

> "That request id matches the `X-Request-ID` response header and the JSON log line. A
> complaint about one action traces end-to-end."

---

## Minute 11–13 · Architecture and engineering

**Tab 5 — Swagger.** Expand a couple of endpoints.

> "The schema is generated from the serializers. It cannot drift from the implementation,
> because it *is* the implementation."

**Tab 6 — Readiness.**

```json
{ "status": "ok", "checks": { "database": "ok", "cache": "ok", "storage": "local" } }
```

> "Liveness checks no dependency; readiness checks all three. Restarting a pod because the
> database blinked would turn a blip into a crash loop."

**Close with the three decisions you would defend hardest:**

1. **Degrades to zero credentials.** "AWS, SMTP, AI and object storage are all optional.
   Missing each one falls back to a local or mock adapter. `docker compose up` is a complete
   system, not a sketch of one."
2. **AI can never act alone.** "A suggestion is stored with its provider, confidence, and
   the human's accept/edit/reject decision. No transition is ever caused by AI. That is what
   makes it auditable."
3. **Honest gaps.** "The Helm chart is delivered; `helm lint` is the CI gate and hasn't been
   wired up yet. The Django admin has no models registered, so reference data is managed by
   seed and shell. Realtime notifications have a Channels backend but no browser client yet.
   I'd rather you hear those from me than find them."

---

## Minute 13–15 · Reserve

Buffer for the tools being slow, a question running long, or a genuinely different demo.

---

## If something breaks

| Failure | Recover in 20 seconds |
|---------|----------------------|
| Stack not up | `make docker-up` and talk about architecture while it starts |
| Login fails | Re-run `make seed` — it is idempotent |
| Reference not found | Search `/incidents` as the citizen, or use a seeded incident instead |
| A page is slow | Open the Swagger tab and narrate the API while it settles |
| Upload rejected | Expected: explain validation is server-side, then submit without media |
| Readiness shows `degraded` | Name the failing dependency from the `checks` map — it is demonstrating itself |
| Total failure | Walk `docs/ARCHITECTURE.md` and the API schema. The design is the substance; the UI is the proof |

Never debug live for more than ~30 seconds. Say "let me come back to that", note it, and
move on. An evaluator remembers a presenter who stayed composed, not one who found a typo.

---

## Anticipated questions during the demo

Full answers are in [VIVA-QA.md](VIVA-QA.md). Short forms:

- **"Is this connected to the BMC?"** No, and it does not claim to be. Every external system is an adapter.
- **"What if someone reports a fake emergency?"** Rate limits, verification before work is assigned, duplicate detection, and an immutable audit trail naming the actor.
- **"Why not microservices?"** At this scale a modular monolith is easier to operate, test and explain — and microservices would have added failure modes without adding capability.
- **"How do you know it works?"** pytest over auth/RBAC/workflow/audit, Vitest for components, Playwright end-to-end. Gates are 80% backend, 70% frontend.
  > Then: "and I'll be straight — the CI workflows that enforce those gates aren't written yet, so they run via `make test`, not on every PR."
- **"What is not finished?"** Helm chart exists but `helm lint` is unrun in CI; Django admin has no models registered; the K8s Kustomize overlays are empty; reference data is shell-managed; realtime notifications have no browser client; CSV export isn't hardened against spreadsheet formula injection.

---

## Post-demo

```bash
make docker-down          # keep data
make docker-down -v       # delete volumes — DESTROYS ALL DATA
```

If you deployed AWS for the demo, tear it down **the same day** and follow
[COST-CONTROL.md](COST-CONTROL.md). An idle EKS cluster plus a NAT gateway costs roughly
$114/month whether or not anyone looks at it again.
