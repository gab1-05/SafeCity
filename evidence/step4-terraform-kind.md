# Step 4: Terraform + Kind Evidence

Captured: 2026-10-16
Purpose: DBIT Notice 3 infrastructure-as-code proof — Terraform verification and a
real Helm deployment on a local cluster. No result is fabricated; blocks are
marked PASS / PARTIAL / NOT DONE.

## Tool versions

| Tool | Version | Status |
|------|---------|--------|
| terraform | v1.16.2 (windows_amd64) | ✅ present |
| kind | v0.33.0 | ✅ present |
| kubectl | v1.36.1 (client) | ✅ present |
| helm | v4.3.0 | ✅ present |
| aws CLI | — | ❌ NOT installed; no AWS credentials on this machine |

## Terraform — fmt / init / validate: PASS

Same commands as the `k8s-validate` workflow, run locally per environment
(`infrastructure/terraform/environments/{dev,staging,prod}`):

| Check | dev | staging | prod |
|-------|-----|---------|------|
| `terraform fmt -check -recursive` | ✅ exit 0 | ✅ (same run) | ✅ (same run) |
| `terraform init -backend=false` | ✅ | ✅ | ✅ |
| `terraform validate` | ✅ "Success! The configuration is valid." | ✅ | ✅ |

## Terraform — plan: PARTIAL (credential-blocked, same as CI)

`terraform plan -input=false` fails on all three environments with AWS credential
errors (no `AWS_ACCESS_KEY_ID`, no SSO profile, no IMDS role on this laptop):

```
Error: failed to refresh cached credentials, no EC2 IMDS role found,
operation error ec2imds: GetMetadata, exceeded maximum number of attempts
```

**Honesty note on CI:** the `k8s-validate` terraform jobs are green, but the plan
step ends with `|| true`. The uploaded `terraform-plan-dev` artifact (47 lines)
shows what really happens without credentials: Terraform plans the two
credential-free `random_password` resources (`Plan: 2 to add`), then exits 1 on
the AWS provider. So a green `k8s-validate` run proves `fmt` + `validate`, **not**
a complete plan. No `apply` has ever run anywhere (see AWS below).

## Kind deployment: PASS

- Cluster `safecity` (node `safecity-control-plane`, v1.37.0-era kind), namespace
  `safecity-dev`; Bitnami PostgreSQL + Redis releases present (namespace `default`).
- Rebuilt both images from current source and loaded them into kind:
  `safecity-backend:1.0.0` (`sha256:aab3ae5e…`), `safecity-frontend:1.0.0`
  (`sha256:c8af1569…`).
- `helm upgrade --install safecity infrastructure/helm/safecity -f values-kind.yaml`
  → release revision **14**, deployed.
- Same-tag caveat (documented, then handled): the chart reuses tag `1.0.0`, so the
  upgrade alone did not restart pods. Ran `kubectl rollout restart` on both
  deployments; new pods (`backend-64d8bcc9d4`, `frontend-5b44896b59`) Running,
  old ReplicaSets terminated.
- Seeding is idempotent: `seed_demo_data` reported "Incidents already exist —
  skipping incident seeding. Demo data seeded."
- Verification via port-forward:
  - `GET http://127.0.0.1:18082/api/health/` → `{"status": "ok", "service": "safecity-backend"}`
  - `GET http://127.0.0.1:5175/` (frontend service) → HTTP 200
- Operational note: Docker Desktop had stopped since the morning session (daemon
  unreachable, kind API refused). Restarted it from the per-user install
  (`%LocalAppData%\Programs\DockerDesktop\Docker Desktop.exe`); compose stack
  (7 containers) and kind recovered.

## AWS apply + billing alarm: NOT DONE (blocked — decision required)

- Nothing has been applied to AWS, ever: no CLI, no credentials, no account
  access from this machine. This matches the repository's own guardrails
  (`terraform/README.md`: "Nothing in this directory has been applied";
  `docs/COST-CONTROL.md` teardown-first policy).
- **The dev stack is not free-tier.** Indicative cost `ap-south-1`: dev ≈
  **$185/month** (EKS control plane $73 + NAT $41 + nodes/RDS/Redis/ALB/…),
  staging ≈ $370, prod ≈ $460. Applying dev would violate the standing
  "AWS free tier only" spend constraint.
- The billing-alarm procedure exists (`docs/COST-CONTROL.md` §4, `aws budgets
  create-budget`) but needs an AWS account, credentials, and a notification email.
- Proceeding requires: (1) explicit spend approval, (2) AWS credentials on this
  machine, (3) a confirmed alarm email. Asked the operator; see session log.
  Until then the $0 path (plan-only + kind + compose) is the verified deployment
  story, which is also the repository's own recommendation for an academic
  submission (`COST-CONTROL.md` §3).

## Gate status

**PARTIAL** — Terraform fmt/validate and the full kind deploy (fresh images,
health-verified) are PASS with logs above. `terraform plan`/`apply` and the AWS
billing alarm are NOT DONE, blocked on credentials + spend approval (decision
requested, not assumed).
