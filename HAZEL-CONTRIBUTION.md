# hazel's SafeCity Contribution

**Contributor:** Hazel Sanctis  
**Repository:** https://github.com/gab1-05/SafeCity  
**Primary Focus:** Documentation, deployment guides, audit reports, compliance evidence, frontend UI & accessibility  
**Total Commits Attributed:** 13  

---

## Contributions Summary

Hazel Sanctis contributed across documentation, deployment guides, compliance audit reporting, and frontend UI/accessibility work. Several frontend-facing commits (accessibility fixes for notification bell and Leaflet map markers, CORS origin configuration for e2e testing) are attributed to Hazel. All commits follow conventional commit conventions (`docs:`, `feat:`, `fix:`, `chore:`).

---

## Detailed Commit List

### Documentation & Compliance Evidence (9 commits)

| # | Hash | Type | Commit Message | Explanation |
|---|------|------|----------------|-------------|
| 1 | `a1a1407` | `docs` | Cloudflare Tunnel deployment guide + README public deploy section | Added the Cloudflare quick-tunnel deployment guide and public deployment section to README.md |
| 2 | `b52d92e` | `docs` | Public-demo tunnel overlay + step 4b free-online evidence | Documented the free Cloudflare tunnel public demo and step 4b evidence |
| 3 | `401491a` | `docs(obs)` | Alert rules, dashboard targets, gate tables aligned with `/api/metrics/` | Aligned Prometheus alert rules, Grafana dashboard targets, and CI gate tables with the metrics exposition endpoint |
| 4 | `419a1f3` | `docs` | Final audit summary, achievements, step 5 monitoring evidence | Compiled final audit summary, achievements list, and step 5 monitoring evidence |
| 5 | `071f32c` | `docs` | Full DEVOTS audit report, ≈92% compliance, READY FOR REVIEW verdict | Authored the complete DEVOTS compliance audit report (~92% compliance, ready for review) |
| 6 | `17bbdf4` | `docs` | Monitoring evidence + SDG 11 alignment with stakeholder validation | Documented monitoring stack evidence and SDG 11 (Sustainable Cities) alignment with stakeholder validation |
| 7 | `7b7a005` | `docs` | Step 3 PR workflow evidence (PR #19, PR #20) | Documented PR #19 and PR #20 workflow evidence including main-push verification |
| 8 | `c6989d1` | `docs` | Step 4 Terraform + Kind evidence | Documented Terraform fmt/validate passes, Kind cluster rev 14 health checks, AWS decision status |
| 9 | `bfde7ce` | `docs` | Final summary + achievements updated to 95% compliance (PR #21 merged) | Updated final summary and achievements to 95% compliance after PR #21 merge |

### Frontend UI & Accessibility (4 commits)

| # | Hash | Type | Commit Message | Explanation |
|---|------|------|----------------|-------------|
| 10 | `13b56a9` | `fix(a11y)` | Name the notification bell — drop the button-in-link so it is one labeled control when unread count is 0 | Fixed notification bell component to be a single labeled control when unread count is 0, improving screen reader accessibility |
| 11 | `3a03b7b` | `fix(a11y)` | Give Leaflet map markers accessible names (title/alt) for screen readers | Added `title`/`alt` attributes to Leaflet map markers for screen reader accessibility |
| 12 | `52b047e` | `fix(ci)` | Allow the :5174 origin for the e2e SPA, pin resolvable trivy-action, align playwright baseURL default | Configured CORS to allow frontend `:5174` origin for e2e tests, pinned trivy-action, aligned Playwright baseURL |
| 13 | `51dd10a` | `chore` | Track deploy workflow, a11y e2e spec, security.txt and pitch assets | Tracked deploy workflow, accessibility e2e spec, `security.txt`, and pitch assets in the repository |

---

## Impact by Area

### Documentation & Compliance
- **DEVOTS audit report:** Complete compliance audit (~92%, READY FOR REVIEW verdict)
- **Deployment guides:** Cloudflare Tunnel setup, public demo instructions
- **PR workflow evidence:** Documentation for PR #19 and PR #20 merges
- **Infrastructure evidence:** Terraform validation, Kind cluster health checks
- **SDG alignment:** SDG 11 (Sustainable Cities) mapping with stakeholder validation

### Frontend Accessibility (a11y)
- **Notification bell:** Fixed button-in-link anti-pattern; now a single labeled control for screen readers
- **Leaflet map markers:** Added `title`/`alt` attributes for screen reader identification
- **E2e testing:** Configured CORS origin `:5174` for frontend e2e testing, aligned Playwright baseURL

### Repository Housekeeping
- **security.txt:** Added vulnerability disclosure contact file
- **Pitch assets:** Tracked pitch deck files in the repository

---

## Files Modified

| File | Change |
|------|--------|
| `README.md` | Cloudflare Tunnel deployment guide, public deploy section |
| `DEVOTS-AUDIT.md` | Full audit report, monitoring evidence, SDG alignment |
| `architecture-diagram.md` | Mermaid C4 diagrams |
| `frontend/` | Notification bell accessibility, Leaflet map marker a11y |
| `.github/workflows/` | CORS origin `:5174` for e2e, Playwright baseURL |
| `.well-known/security.txt` | Vulnerability disclosure contact |
| `pitch/` | Pitch deck asset tracking |

---

*Generated from git commit history. Consistent with CONTRIBUTIONS_REPORT.md.*
