# SafeCity Contributions Report

**Project:** SafeCity — Smart City Incident Management and Civic Response Platform  
**Repository:** https://github.com/gab1-05/SafeCity  
**Report Date:** October 19, 2026  
**Source:** Git commit history + contributor MD files  

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Contributor Overview](#contributor-overview)
3. [Detailed Contributions by Person](#detailed-contributions-by-person)
   - [GABRIEL P — Core Platform & Infrastructure](#gabriel-p)
   - [Hazel Sanctis — Documentation, Frontend UI, Deployment](#hazel-sanctis)
   - [Dherazlin Jebisha — Accessibility, CI/CD, Observability](#dherazlin-jebisha)
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

| Contributor | Git Identity | GitHub | Primary Focus | Commit Count |
|-------------|-------------|--------|---------------|--------------|
| GABRIEL P | `GABRIEL P <gab1.gab05.05@gmail.com>` | [@gab1-05](https://github.com/gab1-05) | Core platform (auth, RBAC, PII), security hardening (CVEs), Docker/Kubernetes infrastructure, release merges | 33 |
| Hazel Sanctis | `hazel sanctis <sanctishazel@gmail.com>` | [@vanessa310107](https://github.com/vanessa310107) | Documentation, deployment guides, audit reports, compliance evidence, frontend UI/a11y | 24 (21 authored + 3 moved) |
| Dherazlin Jebisha | `Dherazlin Jebisha <dherazlinjb06@gmail.com>` | [@Dherazlin](https://github.com/Dherazlin) | Accessibility (a11y) fixes, CI/CD pipeline fixes, observability metrics, security (CSP) | 9 |
| joe godwin | `joe godwin <godwinjoe87@gmail.com>` | [@joegodwin04](https://github.com/joegodwin04) | Test suites (auth, 2FA, OAuth), monitoring stack (Prometheus/Grafana), Ansible playbooks, e2e testing | 6 |

> **Note on attribution:** Per the DEVOTS-AUDIT.md Section A2, commits are attributed to `hazel sanctis`, `Dherazlin Jebisha`, `joe godwin` (conventional commits) plus the original author (GABRIEL P). Frontend/UI-related commits have been attributed to Hazel Sanctis where relevant (see [Detailed Contributions](#detailed-contributions-by-person) below). Dependabot dependency-bump commits are attributed to the repository owner.

---

## Detailed Contributions by Person

### GABRIEL P — Core Platform & Infrastructure

GABRIEL P is the original author (repository owner `gab1-05`). Their contributions form the backbone of the SafeCity platform: authentication, authorization, security hardening, containerization, infrastructure-as-code, and release management.

#### Security & Hardening
| Commit | Hash | Explanation |
|--------|------|-------------|
| `fix: bump Pillow to >=12.3` | `e31711a` | Cleared Trivy HIGH/CRITICAL CVEs in the Python image dependency chain |
| `fix: nginx 1.27 -> 1.29 + apk upgrade` | `b955f6d` | Upgraded Alpine-based images to clear HIGH/CRITICAL OS-level CVEs flagged by Trivy |
| `fix: Django 5.0 -> 5.2 LTS + DRF 3.16` | `ef06c6e` | Upgraded Django and Django REST Framework to clear a GeoDjango RCE CVE |
| `fix: apt upgrade in backend image` | `b362abb` | Ran `apt-get full-upgrade` in the backend Dockerfile to clear Debian OS CVEs |
| `ci: Trivy gate fails only on fixable CVEs` | `1897096` | Configured Trivy image scanning with `--ignore-unfixed` so CI fails only on remediable CVEs |

#### Core Platform Features
| Commit | Hash | Explanation |
|--------|------|-------------|
| `fix: close P0 auth/RBAC/PII gaps` | `d5707c9` | Closed priority-zero gaps in authentication, role-based access control, and personally identifiable information handling |
| `test: authz guard regressions + ruff fixes` | `d28d40d` | Added authorization guard regression tests and fixed lint issues flagged by Ruff |
| `feat: add response caching` | `509f52f` | Added 60s analytics caching and 30s public list caching; test cache isolation; admin KPI fixes |
| `Perf+ops: response caching, N+1 fixes` | `4a16c35` | Performance and operations: response caching, N+1 query fixes, admin registry extensions, Kind HPA overlay, runbooks |
| `fix: COPY requirements path for Render` | `ae1c691` | Fixed the Docker COPY path for requirements files in the Render build context |

#### CI/CD, Docker & Infrastructure
| Commit | Hash | Explanation |
|--------|------|-------------|
| `fix docker-ci: lowercase GHCR tags` | `fa6e4c3` | Lowercased GitHub Container Registry tags, added `actions:write` for cache, restricted Trivy to push events |
| `Jenkinsfile: drop timestamps() option` | `29b7dd9` | Removed unavailable `timestamps()` option from Jenkinsfile (requires timestamper plugin) |
| `Merge pull request #21 from develop` | `1e8ef38` | Merged PR #21 (monitoring + SDG evidence) into `main` |
| `Merge pull request #20 from develop` | `99e9d77` | Merged PR #20 (develop→main promotion) into `main` |
| `Merge pull request #19 from fix/ci-green-and-docs` | `f70da24` | Merged PR #19 (CI green + docs) into `develop` |
| `Merge branch 'main' into fix/all-bugs` | `bedcba7` | Merged `main` into the `fix/all-bugs` branch |
| `trig: force GitHub Actions re-run` | `91abba0` | Triggered a GitHub Actions re-run for workflow verification |

---

### Hazel Sanctis — Documentation, Frontend UI, Deployment

Hazel Sanctis ([@vanessa310107](https://github.com/vanessa310107), `sanctishazel@gmail.com`) contributed primarily through documentation, deployment guides, audit reports, compliance evidence, Render cloud deployment fixes, and frontend UI/accessibility work. Several frontend-facing commits (accessibility, notification UI, map markers, CSP origins for frontend) are attributed here.

#### Documentation & Compliance Evidence
| Commit | Hash | Explanation |
|--------|------|-------------|
| `docs: Cloudflare Tunnel deployment guide + README public deploy section` | `66fa631` | Added the Cloudflare Tunnel deployment guide and a public deployment section to README.md |
| `docs: public-demo tunnel overlay + step 4b free-online evidence` | `305aa3d` | Documented the free Cloudflare quick-tunnel public demo and step 4b evidence |
| `docs(obs): alert rules, dashboard targets, gate tables aligned with /api/metrics/` | `56a230d` | Aligned Prometheus alert rules, Grafana dashboard targets, and CI gate tables with the metrics exposition at `/api/metrics/` |
| `docs: final audit summary, achievements, step 5 monitoring evidence` | `7137891` | Compiled the final DEVOTS audit summary, achievements list, and step 5 monitoring evidence |
| `docs: full DEVOTS audit report, ≈92% compliance, READY FOR REVIEW verdict` | `8dcea0e` | Authored the complete DEVOTS compliance audit report (~92% compliance, ready for review) |
| `docs: monitoring evidence + SDG 11 alignment` | `0989b30` | Documented monitoring stack evidence and SDG 11 (Sustainable Cities) alignment with stakeholder validation |
| `docs: step 3 PR workflow evidence` | `234839b` | Documented PR #19 and PR #20 workflow evidence, including main-push verification |
| `docs: step 4 terraform + kind evidence` | `1b6df5a` | Documented Terraform fmt/validate passes, Kind cluster rev 14 health checks, AWS decision status |
| `docs: final summary + achievements updated to 95% compliance` | `66ab02c` | Updated final summary and achievements to reflect 95% compliance after PR #21 merge |
| `feat: add hazel's contribution overview` | `73850a0` | Added Hazel Sanctis's contribution overview document |
| `docs: accurate pipeline and gate docs, resolved limitations` | `18ce1e2` | Corrected pipeline/gate documentation and recorded step 1-2 evidence |
| `updated docs & deployment guide added` | `b9ea47f` | Refreshed the docs set and added the deployment guide |
| `docs: add CONTRIBUTIONS_REPORT.md with full contributor breakdown` | `920b733` | Added the full per-contributor breakdown report |
| `docs: sync all contributor MD files with consistent contribution data` | `d6365df` | Aligned all contributor MD files to one consistent dataset |
| `feat: add generated PDF contributions report and generator script` | `bbc16b2` | Added the PDF export of the contributions report and its generator |

#### Cloud Deployment — Render
| Commit | Hash | Explanation |
|--------|------|-------------|
| `fix: run migrations before starting Daphne on Render` | `4cfaf50` | Applied `migrate --noinput` in the container CMD before serving (Render has no paid Pre-Deploy hook) |
| `fix: cross-origin API/WS URLs in frontend, seed demo data on boot` | `ddae7ab` | Made API/WS base URLs build-time configurable and seeded demo data on boot |
| `fix: derive CSP connect-src from VITE_API_BASE_URL` | `3e70f27` | `vite.config.ts` derives the CSP `connect-src` extra origins from the configured API/WS URLs |
| `fix: degrade cache/channels/celery to in-process defaults when Redis is absent` | `cd11b7e` | LocMem cache + in-memory channel layer + eager Celery fallback when `REDIS_URL` is unset |
| `updated docs added` | `d5d7af2` | Documentation refresh |

#### Frontend UI & Accessibility (Attributed to Hazel)
| Commit | Hash | Explanation |
|--------|------|-------------|
| `fix(a11y): name the notification bell` | `e95f8ab` | **Frontend UI:** Dropped the button-in-link anti-pattern so the notification bell is a single labeled control when the unread count is 0 |
| `fix(a11y): give Leaflet map markers accessible names` | `8c4b54d` | **Frontend UI:** Added `title`/`alt` attributes to Leaflet map markers so they are accessible to screen readers |
| `fix(ci): allow the :5174 origin for the e2e SPA` | `2b1bf10` | **Frontend/CI:** Allowed the `:5174` frontend origin in CORS for e2e tests, pinned trivy-action, aligned Playwright baseURL |
| `chore: track deploy workflow, a11y e2e spec, security.txt` | `ab1c7fd` | Tracked the deploy workflow, a11y e2e spec, `security.txt`, and pitch assets in the repo |

**Total attributed to Hazel Sanctis: 24 commits** (10 docs/deployment + 6 platform docs/reports + 5 Render deployment fixes + 3 frontend/UI/CI moved here).

---

### Dherazlin Jebisha — Accessibility, CI/CD, Observability

Dherazlin Jebisha focused on accessibility remediation, CI/CD pipeline reliability, security headers, and observability metrics.

| Commit | Hash | Explanation |
|--------|------|-------------|
| `fix: add dherazlin's operational fix` | `76db20d` | Applied dherazlin's operational fix (specific details in commit) |
| `fix: repair TOTP leading-zero validation, session revoke route and seeder idempotency` | `98221cf` | Fixed TOTP two-factor authentication leading-zero validation, repaired session revocation route, and made the database seeder idempotent |
| `fix(a11y): give Leaflet map markers accessible names` | `8c4b54d` | Added `title`/`alt` attributes to Leaflet map markers for screen reader accessibility |
| `fix(a11y): name the notification bell` | `e95f8ab` | Dropped button-in-link anti-pattern so the notification bell is a single labeled control when unread count is 0 |
| `fix(ci): allow the :5174 origin for the e2e SPA` | `2b1bf10` | Allowed `:5174` frontend origin in CORS for e2e tests; pinned trivy-action; aligned Playwright baseURL default |
| `fix(ci): pin trivy-action to v0.28.0` | `1db7967` | Pinned Trivy GitHub Action to v0.28.0 so SARIF scans complete reliably; kept report as CI artifact |
| `feat(obs): Prometheus exposition at /api/metrics/` | `3fdba27` | Implemented the Prometheus metrics exposition endpoint with request counters and live gauges |
| `fix: remove unused import and sort imports` | `68eaeec` | Removed unused imports and sorted imports per Ruff rules (F401, I001) |
| `fix(deploy): build-time CSP connect-src origins for non-localhost deployments` | `001373f` | Configured build-time CSP `connect-src` origins so the deployed SPA can reach its API |

**Total: 9 commits**

---

### joe godwin — Testing, Monitoring, Configuration Management

joe godwin focused on test coverage, monitoring infrastructure, configuration management, and end-to-end testing.

| Commit | Hash | Explanation |
|--------|------|-------------|
| `test: add joe's test coverage` | `b3d574b` | Added joe's test coverage to the backend test suite |
| `feat: add ansible playbooks for configuration management` | `49bb9b5` | Added Ansible playbooks (`site.yml`, `install-postgres.yml`, `install-redis.yml`, `install-app.yml`) for configuration management |
| `feat: add monitoring stack (Prometheus/Grafana) and kind deployment script` | `2d2a0c3` | Added Prometheus + Grafana monitoring stack and the Kind cluster deployment script |
| `docs: update audit report with monitoring stack and deployment fixes` | `4429f3b` | Updated the DEVOTS audit report to reflect monitoring stack and deployment fixes |
| `test: add auth/2FA/OAuth/commands suites` | `0cbb6a3` | Added authentication, 2FA, OAuth, and management command test suites — backend coverage 82% (gate 80%) with CI enforcement |
| `test(e2e): add @axe-core/playwright dependency` | `4203aec` | Added `@axe-core/playwright` for accessibility e2e scanning; wait for map markers before axe scan; dropped unused socket.io-client |

**Total: 6 commits**

---

## Commit Attribution Table (Adjusted)

The table below shows all tracked commits with their original author and the attribution used in this report. Frontend/UI-related commits have been moved to **Hazel Sanctis** per request.

| # | Original Author | Report Attribution | Hash | Commit Message | Category |
|---|----------------|-------------------|------|----------------|----------|
| 1 | GABRIEL P | GABRIEL P | `68eaeec` | fix: remove unused import and sort imports (ruff F401/I001) | Chore |
| 2 | hazel sanctis | Hazel Sanctis | `b9ea47f` | updated docs & deployment guide added | Docs |
| 3 | hazel sanctis | Hazel Sanctis | `66fa631` | docs: Cloudflare Tunnel deployment guide + README public deploy section | Docs |
| 4 | hazel sanctis | Hazel Sanctis | `66ab02c` | docs: final summary + achievements updated to 95% compliance | Docs |
| 5 | GABRIEL P | GABRIEL P | `1e8ef38` | Merge pull request #21 from develop | Merge |
| 6 | hazel sanctis | Hazel Sanctis | `0989b30` | docs: monitoring evidence + SDG 11 alignment | Docs |
| 7 | hazel sanctis | Hazel Sanctis | `8dcea0e` | docs: full DEVOTS audit report, ≈92% compliance | Docs |
| 8 | hazel sanctis | Hazel Sanctis | `7137891` | docs: final audit summary, achievements, step 5 monitoring evidence | Docs |
| 9 | hazel sanctis | Hazel Sanctis | `56a230d` | docs(obs): alert rules, dashboard targets, gate tables aligned | Docs |
| 10 | Dherazlin Jebisha | Dherazlin Jebisha | `3fdba27` | feat(obs): Prometheus exposition at /api/metrics/ | Feature |
| 11 | hazel sanctis | Hazel Sanctis | `305aa3d` | docs: public-demo tunnel overlay + step 4b free-online evidence | Docs |
| 12 | Dherazlin Jebisha | Dherazlin Jebisha | `001373f` | fix(deploy): build-time CSP connect-src origins | Fix |
| 13 | hazel sanctis | Hazel Sanctis | `1b6df5a` | docs: step 4 terraform + kind evidence | Docs |
| 14 | hazel sanctis | Hazel Sanctis | `234839b` | docs: step 3 PR workflow evidence | Docs |
| 15 | GABRIEL P | GABRIEL P | `99e9d77` | Merge pull request #20 from develop | Merge |
| 16 | GABRIEL P | GABRIEL P | `f70da24` | Merge pull request #19 from fix/ci-green-and-docs | Merge |
| 17 | Dherazlin Jebisha | Dherazlin Jebisha | `e95f8ab` | fix(a11y): name the notification bell | **Frontend/UI → Hazel Sanctis** |
| 18 | Dherazlin Jebisha | Dherazlin Jebisha | `2b1bf10` | fix(ci): allow the :5174 origin for the e2e SPA | **Frontend/CI → Hazel Sanctis** |
| 19 | hazel sanctis | Hazel Sanctis | `18ce1e2` | docs: accurate pipeline and gate docs, resolved limitations | Docs |
| 20 | joe godwin | joe godwin | `4203aec` | test(e2e): add @axe-core/playwright dependency | Test |
| 21 | Dherazlin Jebisha | Dherazlin Jebisha | `8c4b54d` | fix(a11y): give Leaflet map markers accessible names | **Frontend/UI → Hazel Sanctis** |
| 22 | Dherazlin Jebisha | Dherazlin Jebisha | `1db7967` | fix(ci): pin trivy-action to v0.28.0 | CI |
| 23 | hazel sanctis | Hazel Sanctis | `ab1c7fd` | chore: track deploy workflow, a11y e2e spec, security.txt | Chore |
| 24 | joe godwin | joe godwin | `0cbb6a3` | test: add auth/2FA/OAuth/commands suites | Test |
| 25 | Dherazlin Jebisha | Dherazlin Jebisha | `98221cf` | fix: repair TOTP leading-zero validation, session revoke route | Fix |
| 26 | joe godwin | joe godwin | `4429f3b` | docs: update audit report with monitoring stack | Docs |
| 27 | joe godwin | joe godwin | `2d2a0c3` | feat: add monitoring stack (Prometheus/Grafana) and kind script | Feature |
| 28 | joe godwin | joe godwin | `49bb9b5` | feat: add ansible playbooks for configuration management | Feature |
| 29 | joe godwin | joe godwin | `b3d574b` | test: add joe's test coverage | Test |
| 30 | Dherazlin Jebisha | Dherazlin Jebisha | `76db20d` | fix: add dherazlin's operational fix | Fix |
| 31 | hazel sanctis | Hazel Sanctis | `73850a0` | feat: add hazel's contribution overview | Feature |
| 32 | GABRIEL P | GABRIEL P | `91abba0` | trig: force GitHub Actions re-run | CI |
| 33 | GABRIEL P | GABRIEL P | `45f6cfd` | fix: update trivy-action to v0.2.0 | Fix |
| 34 | GABRIEL P | GABRIEL P | `bedcba7` | Merge branch 'main' into fix/all-bugs | Merge |
| 35 | GABRIEL P | GABRIEL P | `ae1c691` | fix: COPY requirements path for Render build context | Fix |
| 36 | GABRIEL P | GABRIEL P | `299fe91` | Merge pull request #18 from gab1-05/fix/all-bugs | Merge |
| 37 | GABRIEL P | GABRIEL P | `1897096` | ci: Trivy gate fails only on fixable CVEs | CI |
| 38 | GABRIEL P | GABRIEL P | `b362abb` | fix: apt upgrade in backend image to clear Debian OS CVEs | Fix |
| 39 | GABRIEL P | GABRIEL P | `ef06c6e` | fix: Django 5.0 -> 5.2 LTS + DRF 3.16 | Fix |
| 40 | GABRIEL P | GABRIEL P | `b955f6d` | fix: nginx 1.27 -> 1.29 + apk upgrade | Fix |
| 41 | GABRIEL P | GABRIEL P | `e31711a` | fix: bump Pillow to >=12.3 | Fix |
| 42 | GABRIEL P | GABRIEL P | `d28d40d` | test: authz guard regressions + ruff fixes | Test |
| 43 | GABRIEL P | GABRIEL P | `d5707c9` | fix: close P0 auth/RBAC/PII gaps | Fix |
| 44 | GABRIEL P | GABRIEL P | `29b7dd9` | Jenkinsfile: drop timestamps() option | Fix |
| 45 | GABRIEL P | GABRIEL P | `b6991fe` | Improvements batch: rate-limit headers, audit retention, N+1 | Improvements |
| 46 | GABRIEL P | GABRIEL P | `4a16c35` | Perf+ops: response caching, N+1 fixes, admin registry extend | Perf/Ops |
| 47 | GABRIEL P | GABRIEL P | `fa6e4c3` | Fix docker-ci: lowercase GHCR tags, actions:write for cache | Fix |
| 48 | GABRIEL P | GABRIEL P | `77d8f6b` | updated docs | Docs |
| 49 | GABRIEL P | GABRIEL P | `bd86915` | updated docs | Docs |
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
