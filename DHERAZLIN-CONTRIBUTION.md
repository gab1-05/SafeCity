# dherazlin's SafeCity Contribution

**Contributor:** dherazlin jebisha  
**Repository:** https://github.com/gab1-05/SafeCity  
**Primary Focus:** Accessibility (a11y), CI/CD pipeline reliability, security headers, observability metrics  
**Total Commits Attributed:** 8  

---

## Contributions Summary

dherazlin jebisha contributed across four key areas: accessibility remediation, CI/CD pipeline fixes, security header configuration, and observability metrics implementation. All commits follow conventional commit conventions (`fix:`, `feat:`, `ci:`).

---

## Detailed Commit List

| # | Hash | Type | Commit Message | Explanation |
|---|------|------|----------------|-------------|
| 1 | `cc45c90` | `feat(obs)` | Prometheus exposition at `/api/metrics/` (request counters + live gauges) | Implemented the Prometheus metrics exposition endpoint with request counters and live gauges for observability |
| 2 | `3a03b7b` | `fix(a11y)` | Give Leaflet map markers accessible names (title/alt) for screen readers | Added `title`/`alt` attributes to Leaflet map markers so they are accessible to screen readers |
| 3 | `13b56a9` | `fix(a11y)` | Name the notification bell — drop the button-in-link so it is one labeled control when unread count is 0 | Fixed the notification bell component so it is a single labeled control when the unread count is 0, improving screen reader accessibility |
| 4 | `52b047e` | `fix(ci)` | Allow the :5174 origin for the e2e SPA, pin resolvable trivy-action, align playwright baseURL default | Configured CORS to allow the frontend `:5174` origin for e2e tests, pinned trivy-action version, and aligned Playwright baseURL defaults |
| 5 | `3239075` | `fix(ci)` | Pin trivy-action to v0.28.0 so SARIF scans complete; keep report as artifact | Pinned Trivy GitHub Action to v0.28.0 to ensure SARIF scans complete reliably, with the report kept as a CI artifact |
| 6 | `a2b9095` | `fix` | Repair TOTP leading-zero validation, session revoke route and seeder idempotency | Fixed TOTP two-factor authentication leading-zero validation, repaired the session revocation route, and made the database seeder idempotent |
| 7 | `1208620` | `fix` | Add dherazlin's operational fix | Applied dherazlin's operational fix to the codebase |
| 8 | `940327a` | `fix` | Remove unused import and sort imports (ruff F401/I001) | Removed unused imports and sorted imports per Ruff linting rules (F401, I001) |

---

## Impact by Area

### Accessibility (a11y)
- **Leaflet map markers:** Added accessible names (`title`/`alt`) so screen readers can identify map markers
- **Notification bell:** Fixed button-in-link anti-pattern; the bell is now a single labeled control, improving keyboard and screen reader navigation

### CI/CD Pipeline
- **Trivy security scanning:** Pinned to v0.28.0 for reliable SARIF report generation
- **Frontend CORS:** Allowed `:5174` origin for e2e SPA testing
- **Playwright baseURL:** Aligned defaults for consistent end-to-end testing

### Security
- **CSP connect-src:** Configured build-time CSP connect-src origins for non-localhost deployments (see also `4911a58`)
- **TOTP 2FA:** Fixed leading-zero validation bug in time-based one-time password verification
- **Session management:** Repaired session revoke route
- **Database seeder:** Made seeder idempotent to prevent duplicate seed data

---

## Files Modified

| File | Change |
|------|--------|
| `frontend/` | Leaflet map marker accessibility attributes, notification bell component |
| `.github/workflows/` | Trivy action pinning, CORS origin configuration, Playwright baseURL |
| `backend/apps/accounts/` | TOTP validation, session revoke route |
| `backend/` | Database seeder idempotency, unused import removal |

---

*Generated from git commit history. Consistent with CONTRIBUTIONS_REPORT.md.*
