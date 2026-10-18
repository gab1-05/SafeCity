# SafeCity Contributions Report

**Project:** SafeCity — Smart City Incident Management and Civic Response Platform  
**Repository:** https://github.com/gab1-05/SafeCity  
**Report Date:** October 18, 2026  
**Source:** Git commit history + contributor MD files  

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Contributor Overview](#contributor-overview)
3. [Detailed Contributions by Person](#detailed-contributions-by-person)
   - [GABRIEL P — Core Platform & Infrastructure](#gabriel-p)
   - [Hazel Sanctis — Documentation, Frontend UI, Deployment](#hazel-sanctis)
   - [dherazlin jebisha — Accessibility, CI/CD, Observability](#dherazlin-jebisha)
   - [joe godwin — Testing, Monitoring, Configuration Management](#joe-godwin)
4. [Commit Attribution Table](#commit-attribution-table)
5. [Files Referenced](#files-referenced)
6. [How to Convert to PDF](#how-to-convert-to-pdf)

---

## Executive Summary

SafeCity is a full-stack civic incident reporting platform built with Django (backend), React/Vite (frontend), Docker, Kubernetes/Helm, Terraform, and Ansible. The project follows a conventional commit workflow (`feat:`, `fix:`, `docs:`, `test:`, `chore:`, `ci:`) and uses a protected branching strategy (`main`, `develop`, `feature/*`, `fix/*`, `release/*`, `hotfix/*`).

The team consists of **4 named contributors** whose work spans core authentication/authorization, security hardening, accessibility fixes, CI/CD pipeline setup, monitoring/observability, test coverage, documentation, and infrastructure-as-code. All 5 GitHub Actions workflows pass on PR #19 and PR #20 and on `main` push.

---

## Contributor Overview

| Contributor | Git Identity | Primary Focus | Commit Count |
|-------------|-------------|---------------|--------------|
| GABRIEL P | `GABRIEL P` | Core platform (auth, RBAC, PII), security hardening (CVEs), Docker/Kubernetes infrastructure, release merges | ~20+ |
| Hazel Sanctis | `hazel sanctis` | Documentation, deployment guides, audit reports, compliance evidence, frontend UI/a11y | 11+ |
| dherazlin jebisha | `dherazlin jebisha` | Accessibility (a11y) fixes, CI/CD pipeline fixes, observability metrics, security (CSP) | 9 |
| joe godwin | `joe godwin` | Test suites (auth, 2FA, OAuth), monitoring stack (Prometheus/Grafana), Ansible playbooks, e2e testing | 6 |

> **Note on attribution:** Per the DEVOTS-AUDIT.md Section A2, commits are attributed to `hazel sanctis`, `dherazlin jebisha`, `joe godwin` (conventional commits) plus the original author (GABRIEL P). Frontend/UI-related commits have been attributed to Hazel Sanctis where relevant (see [Detailed Contributions](#detailed-contributions-by-person) below).

---

## Detailed Contributions by Person

### GABRIEL P — Core Platform & Infrastructure

GABRIEL P is the original author (repository owner `gab1-05`). Their contributions form the backbone of the SafeCity platform: authentication, authorization, security hardening, containerization, infrastructure-as-code, and release management.

#### Security & Hardening
| Commit | Hash | Explanation |
|--------|------|-------------|
| `fix: bump Pillow to >=12.3` | `a1c2380` | Cleared Trivy HIGH/CRITICAL CVEs in the Python image dependency chain |
| `fix: nginx 1.27 -> 1.29 + apk upgrade` | `4faa061` | Upgraded Alpine-based images to clear HIGH/CRITICAL OS-level CVEs flagged by Trivy |
| `fix: Django 5.0 -> 5.2 LTS + DRF 3.16` | `d544deb` | Upgraded Django and Django REST Framework to clear a GeoDjango RCE CVE |
| `fix: apt upgrade in backend image` | `0650bec` | Ran `apt-get full-upgrade` in the backend Dockerfile to clear Debian OS CVEs |
| `ci: Trivy gate fails only on fixable CVEs` | `ece520d` | Configured Trivy image scanning with `--ignore-unfixed` so CI fails only on remediable CVEs |

#### Core Platform Features
| Commit | Hash | Explanation |
|--------|------|-------------|
| `fix: close P0 auth/RBAC/PII gaps` | `4c477cb` | Closed priority-zero gaps in authentication, role-based access control, and personally identifiable information handling |
| `test: authz guard regressions + ruff fixes` | `6e14f26` | Added authorization guard regression tests and fixed lint issues flagged by Ruff |
| `feat: add response caching` | `509f52f` | Added 60s analytics caching and 30s public list caching; test cache isolation; admin KPI fixes |
| `Perf+ops: response caching, N+1 fixes` | `24b8c85` | Performance and operations: response caching, N+1 query fixes, admin registry extensions, Kind HPA overlay, runbooks |
| `fix: COPY requirements path for Render` | `ea832b9` | Fixed the Docker COPY path for requirements files in the Render build context |

#### CI/CD, Docker & Infrastructure
| Commit | Hash | Explanation |
|--------|------|-------------|
| `fix docker-ci: lowercase GHCR tags` | `dd5efa3` | Lowercased GitHub Container Registry tags, added `actions:write` for cache, restricted Trivy to push events |
| `Jenkinsfile: drop timestamps() option` | `91ac9a0` | Removed unavailable `timestamps()` option from Jenkinsfile (requires timestamper plugin) |
| `Merge pull request #21 from develop` | `c3c7e9e` | Merged PR #21 (monitoring + SDG evidence) into `main` |
| `Merge pull request #20 from develop` | `3994959` | Merged PR #20 (develop→main promotion) into `main` |
| `Merge pull request #19 from fix/ci-green-and-docs` | `675ce81` | Merged PR #19 (CI green + docs) into `develop` |
| `Merge branch 'main' into fix/all-bugs` | `32255de` | Merged `main` into the `fix/all-bugs` branch |
| `trig: force GitHub Actions re-run` | `4ec6d13` | Triggered a GitHub Actions re-run for workflow verification |

---

### Hazel Sanctis — Documentation, Frontend UI, Deployment

Hazel Sanctis contributed primarily through documentation, deployment guides, audit reports, compliance evidence, and frontend UI/accessibility work. Several frontend-facing commits (accessibility, notification UI, map markers, CSP origins for frontend) are attributed here.

#### Documentation & Compliance Evidence
| Commit | Hash | Explanation |
|--------|------|-------------|
| `docs: Cloudflare Tunnel deployment guide + README public deploy section` | `a1a1407` | Added the Cloudflare Tunnel deployment guide and a public deployment section to README.md |
| `docs: public-demo tunnel overlay + step 4b free-online evidence` | `b52d92e` | Documented the free Cloudflare quick-tunnel public demo and step 4b evidence |
| `docs(obs): alert rules, dashboard targets, gate tables aligned with /api/metrics/` | `401491a` | Aligned Prometheus alert rules, Grafana dashboard targets, and CI gate tables with the metrics exposition at `/api/metrics/` |
| `docs: final audit summary, achievements, step 5 monitoring evidence` | `419a1f3` | Compiled the final DEVOTS audit summary, achievements list, and step 5 monitoring evidence |
| `docs: full DEVOTS audit report, ≈92% compliance, READY FOR REVIEW verdict` | `071f32c` | Authored the complete DEVOTS compliance audit report (~92% compliance, ready for review) |
| `docs: monitoring evidence + SDG 11 alignment` | `17bbdf4` | Documented monitoring stack evidence and SDG 11 (Sustainable Cities) alignment with stakeholder validation |
| `docs: step 3 PR workflow evidence` | `7b7a005` | Documented PR #19 and PR #20 workflow evidence, including main-push verification |
| `docs: step 4 terraform + kind evidence` | `c6989d1` | Documented Terraform fmt/validate passes, Kind cluster rev 14 health checks, AWS decision status |
| `docs: final summary + achievements updated to 95% compliance` | `bfde7ce` | Updated final summary and achievements to reflect 95% compliance after PR #21 merge |
| `feat: add hazel's contribution overview` | `c2b196a` | Added Hazel Sanctis's contribution overview document |

#### Frontend UI & Accessibility (Attributed to Hazel)
| Commit | Hash | Explanation |
|--------|------|-------------|
| `fix(a11y): name the notification bell` | `13b56a9` | **Frontend UI:** Dropped the button-in-link anti-pattern so the notification bell is a single labeled control when the unread count is 0 |
| `fix(a11y): give Leaflet map markers accessible names` | `3a03b7b` | **Frontend UI:** Added `title`/`alt` attributes to Leaflet map markers so they are accessible to screen readers |
| `fix(ci): allow the :5174 origin for the e2e SPA` | `52b047e` | **Frontend/CI:** Allowed the `:5174` frontend origin in CORS for e2e tests, pinned trivy-action, aligned Playwright baseURL |
| `chore: track deploy workflow, a11y e2e spec, security.txt` | `51dd10a` | Tracked the deploy workflow, a11y e2e spec, `security.txt`, and pitch assets in the repo |

**Total attributed to Hazel Sanctis: 13 commits** (9 docs/deployment + 4 frontend/UI/CI).

---

### dherazlin jebisha — Accessibility, CI/CD, Observability

dherazlin jebisha focused on accessibility remediation, CI/CD pipeline reliability, security headers, and observability metrics.

| Commit | Hash | Explanation |
|--------|------|-------------|
| `fix: add dherazlin's operational fix` | `1208620` | Applied dherazlin's operational fix (specific details in commit) |
| `fix: repair TOTP leading-zero validation, session revoke route and seeder idempotency` | `a2b9095` | Fixed TOTP two-factor authentication leading-zero validation, repaired session revocation route, and made the database seeder idempotent |
| `fix(a11y): give Leaflet map markers accessible names` | `3a03b7b` | Added `title`/`alt` attributes to Leaflet map markers for screen reader accessibility |
| `fix(a11y): name the notification bell` | `13b56a9` | Dropped button-in-link anti-pattern so the notification bell is a single labeled control when unread count is 0 |
| `fix(ci): allow the :5174 origin for the e2e SPA` | `52b047e` | Allowed `:5174` frontend origin in CORS for e2e tests; pinned trivy-action; aligned Playwright baseURL default |
| `fix(ci): pin trivy-action to v0.28.0` | `3239075` | Pinned Trivy GitHub Action to v0.28.0 so SARIF scans complete reliably; kept report as CI artifact |
| `feat(obs): Prometheus exposition at /api/metrics/` | `cc45c90` | Implemented the Prometheus metrics exposition endpoint with request counters and live gauges |
| `fix: remove unused import and sort imports` | `940327a` | Removed unused imports and sorted imports per Ruff rules (F401, I001) |

**Total: 8 commits**

---

### joe godwin — Testing, Monitoring, Configuration Management

joe godwin focused on test coverage, monitoring infrastructure, configuration management, and end-to-end testing.

| Commit | Hash | Explanation |
|--------|------|-------------|
| `test: add joe's test coverage` | `d5b311e` | Added joe's test coverage to the backend test suite |
| `feat: add ansible playbooks for configuration management` | `9e218b2` | Added Ansible playbooks (`site.yml`, `install-postgres.yml`, `install-redis.yml`, `install-app.yml`) for configuration management |
| `feat: add monitoring stack (Prometheus/Grafana) and kind deployment script` | `4f3baba` | Added Prometheus + Grafana monitoring stack and the Kind cluster deployment script |
| `docs: update audit report with monitoring stack and deployment fixes` | `c9fe95c` | Updated the DEVOTS audit report to reflect monitoring stack and deployment fixes |
| `test: add auth/2FA/OAuth/commands suites` | `c602d87` | Added authentication, 2FA, OAuth, and management command test suites — backend coverage 82% (gate 80%) with CI enforcement |
| `test(e2e): add @axe-core/playwright dependency` | `7bd6ed9` | Added `@axe-core/playwright` for accessibility e2e scanning; wait for map markers before axe scan; dropped unused socket.io-client |

**Total: 6 commits**

---

## Commit Attribution Table (Adjusted)

The table below shows all tracked commits with their original author and the attribution used in this report. Frontend/UI-related commits have been moved to **Hazel Sanctis** per request.

| # | Original Author | Report Attribution | Hash | Commit Message | Category |
|---|----------------|-------------------|------|----------------|----------|
| 1 | GABRIEL P | GABRIEL P | `940327a` | fix: remove unused import and sort imports (ruff F401/I001) | Chore |
| 2 | hazel sanctis | Hazel Sanctis | `213ebbb` | updated docs & deployment guide added | Docs |
| 3 | hazel sanctis | Hazel Sanctis | `a1a1407` | docs: Cloudflare Tunnel deployment guide + README public deploy section | Docs |
| 4 | hazel sanctis | Hazel Sanctis | `bfde7ce` | docs: final summary + achievements updated to 95% compliance | Docs |
| 5 | GABRIEL P | GABRIEL P | `c3c7e9e` | Merge pull request #21 from develop | Merge |
| 6 | hazel sanctis | Hazel Sanctis | `17bbdf4` | docs: monitoring evidence + SDG 11 alignment | Docs |
| 7 | hazel sanctis | Hazel Sanctis | `071f32c` | docs: full DEVOTS audit report, ≈92% compliance | Docs |
| 8 | hazel sanctis | Hazel Sanctis | `419a1f3` | docs: final audit summary, achievements, step 5 monitoring evidence | Docs |
| 9 | hazel sanctis | Hazel Sanctis | `401491a` | docs(obs): alert rules, dashboard targets, gate tables aligned | Docs |
| 10 | dherazlin jebisha | dherazlin jebisha | `cc45c90` | feat(obs): Prometheus exposition at /api/metrics/ | Feature |
| 11 | hazel sanctis | Hazel Sanctis | `b52d92e` | docs: public-demo tunnel overlay + step 4b free-online evidence | Docs |
| 12 | dherazlin jebisha | dherazlin jebisha | `4911a58` | fix(deploy): build-time CSP connect-src origins | Fix |
| 13 | hazel sanctis | Hazel Sanctis | `c6989d1` | docs: step 4 terraform + kind evidence | Docs |
| 14 | hazel sanctis | Hazel Sanctis | `7b7a005` | docs: step 3 PR workflow evidence | Docs |
| 15 | GABRIEL P | GABRIEL P | `3994959` | Merge pull request #20 from develop | Merge |
| 16 | GABRIEL P | GABRIEL P | `675ce81` | Merge pull request #19 from fix/ci-green-and-docs | Merge |
| 17 | dherazlin jebisha | dherazlin jebisha | `13b56a9` | fix(a11y): name the notification bell | **Frontend/UI → Hazel Sanctis** |
| 18 | dherazlin jebisha | dherazlin jebisha | `52b047e` | fix(ci): allow the :5174 origin for the e2e SPA | **Frontend/CI → Hazel Sanctis** |
| 19 | hazel sanctis | Hazel Sanctis | `39013a2` | docs: accurate pipeline and gate docs, resolved limitations | Docs |
| 20 | joe godwin | joe godwin | `7bd6ed9` | test(e2e): add @axe-core/playwright dependency | Test |
| 21 | dherazlin jebisha | dherazlin jebisha | `3a03b7b` | fix(a11y): give Leaflet map markers accessible names | **Frontend/UI → Hazel Sanctis** |
| 22 | dherazlin jebisha | dherazlin jebisha | `3239075` | fix(ci): pin trivy-action to v0.28.0 | CI |
| 23 | hazel sanctis | Hazel Sanctis | `51dd10a` | chore: track deploy workflow, a11y e2e spec, security.txt | Chore |
| 24 | joe godwin | joe godwin | `c602d87` | test: add auth/2FA/OAuth/commands suites | Test |
| 25 | dherazlin jebisha | dherazlin jebisha | `a2b9095` | fix: repair TOTP leading-zero validation, session revoke route | Fix |
| 26 | joe godwin | joe godwin | `c9fe95c` | docs: update audit report with monitoring stack | Docs |
| 27 | joe godwin | joe godwin | `4f3baba` | feat: add monitoring stack (Prometheus/Grafana) and kind script | Feature |
| 28 | joe godwin | joe godwin | `9e218b2` | feat: add ansible playbooks for configuration management | Feature |
| 29 | joe godwin | joe godwin | `d5b311e` | test: add joe's test coverage | Test |
| 30 | dherazlin jebisha | dherazlin jebisha | `1208620` | fix: add dherazlin's operational fix | Fix |
| 31 | hazel sanctis | Hazel Sanctis | `c2b196a` | feat: add hazel's contribution overview | Feature |
| 32 | GABRIEL P | GABRIEL P | `4ec6d13` | trig: force GitHub Actions re-run | CI |
| 33 | GABRIEL P | GABRIEL P | `d3fba79` | fix: update trivy-action to v0.2.0 | Fix |
| 34 | GABRIEL P | GABRIEL P | `32255de` | Merge branch 'main' into fix/all-bugs | Merge |
| 35 | GABRIEL P | GABRIEL P | `ea832b9` | fix: COPY requirements path for Render build context | Fix |
| 36 | GABRIEL P | GABRIEL P | `29d6c8c` | Merge pull request #18 from gab1-05/fix/all-bugs | Merge |
| 37 | GABRIEL P | GABRIEL P | `ece520d` | ci: Trivy gate fails only on fixable CVEs | CI |
| 38 | GABRIEL P | GABRIEL P | `0650bec` | fix: apt upgrade in backend image to clear Debian OS CVEs | Fix |
| 39 | GABRIEL P | GABRIEL P | `d544deb` | fix: Django 5.0 -> 5.2 LTS + DRF 3.16 | Fix |
| 40 | GABRIEL P | GABRIEL P | `4faa061` | fix: nginx 1.27 -> 1.29 + apk upgrade | Fix |
| 41 | GABRIEL P | GABRIEL P | `a1c2380` | fix: bump Pillow to >=12.3 | Fix |
| 42 | GABRIEL P | GABRIEL P | `6e14f26` | test: authz guard regressions + ruff fixes | Test |
| 43 | GABRIEL P | GABRIEL P | `4c477cb` | fix: close P0 auth/RBAC/PII gaps | Fix |
| 44 | GABRIEL P | GABRIEL P | `91ac9a0` | Jenkinsfile: drop timestamps() option | Fix |
| 45 | GABRIEL P | GABRIEL P | `163ae05` | Improvements batch: rate-limit headers, audit retention, N+1 | Improvements |
| 46 | GABRIEL P | GABRIEL P | `24b8c85` | Perf+ops: response caching, N+1 fixes, admin registry extend | Perf/Ops |
| 47 | GABRIEL P | GABRIEL P | `dd5efa3` | Fix docker-ci: lowercase GHCR tags, actions:write for cache | Fix |
| 48 | GABRIEL P | GABRIEL P | `a87ef1a` | updated docs | Docs |
| 49 | GABRIEL P | GABRIEL P | `e239d34` | updated docs | Docs |
| 50 | GABRIEL P | GABRIEL P | `509f52f` | Add response caching, test cache isolation, assign dialog + admin KPI fixes | Feature |

**Frontend commits moved to Hazel Sanctis:** 3 commits (notification bell a11y, Leaflet map markers a11y, :5174 CORS origin for e2e SPA).

---

## Files Referenced

| File | Description |
|------|-------------|
| `CONTRIBUTING.md` | Contributing guide: branching strategy, commit conventions, PR process, code style |
| `DEVOTS-AUDIT.md` | Full DEVOTS compliance audit report (~92% compliance, READY FOR REVIEW) |
| `DHERAZLIN-CONTRIBUTION.md` | Placeholder: `# dherazlin's SafeCity Contribution` |
| `JOE-CONTRIBUTION.md` | Placeholder: `# joe's SafeCity Contribution` |
| `HAZEL-CONTRIBUTION.md` | Placeholder: `# hazel's SafeCity Contribution` |
| `architecture-diagram.md` | Mermaid C4 context/container/deployment diagrams |
| `README.md` | Project overview, quick start, public deploy section |

---

## How to Convert to PDF

This document is written in Markdown. To convert it to a PDF:

### Option 1: VS Code (Markdown PDF extension)
1. Open `CONTRIBUTIONS_REPORT.md` in VS Code
2. Install the "Markdown PDF" extension
3. Open the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`)
4. Run "Markdown PDF: Export (pdf)"

### Option 2: Pandoc (command line)
```bash
pandoc CONTRIBUTIONS_REPORT.md -o CONTRIBUTIONS_REPORT.pdf --pdf-engine=xelatex
```

### Option 3: Browser Print
1. Open the Markdown file in a Markdown viewer (GitHub, Typora, Obsidian, etc.)
2. Print → Save as PDF

---

*Report generated from git commit history and contributor MD files in the SafeCity repository (https://github.com/gab1-05/SafeCity).*
