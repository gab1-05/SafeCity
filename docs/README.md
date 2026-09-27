# SafeCity — Documentation Package

**Project:** SafeCity — Smart City Incident Management and Civic Response Platform
**Client / Institution:** The Bombay Salesian Society
**Document type:** Software Development Project (SDP) documentation package

> ⚠️ SafeCity is an **incident coordination tool**. It is *not* an official emergency
> service and *not* an officially integrated government system. In a real emergency,
> call your local emergency number.

---

## Reading order

Start here if you are evaluating the project:

| # | Document | What it answers |
|---|----------|-----------------|
| 1 | [OVERVIEW.md](OVERVIEW.md) | What is SafeCity, why does it exist, who is it for |
| 2 | [REQUIREMENTS.md](REQUIREMENTS.md) | Functional + non-functional requirements, user stories, use cases |
| 3 | [ARCHITECTURE.md](ARCHITECTURE.md) | Final architecture proposal, technology justification, decisions |
| 4 | [DATA-MODEL.md](DATA-MODEL.md) | ER diagram and entity dictionary |
| 5 | [API-REFERENCE.md](API-REFERENCE.md) | REST API: conventions, endpoints, examples |
| 6 | [ROLES-AND-ACCESS.md](ROLES-AND-ACCESS.md) | Roles, permission matrix, enforcement points |
| 7 | [SECURITY-AND-PRIVACY.md](SECURITY-AND-PRIVACY.md) | Threat model, controls, privacy & governance |

## Operating SafeCity

| Document | Audience |
|----------|----------|
| [INSTALLATION-GUIDE.md](INSTALLATION-GUIDE.md) | Anyone setting SafeCity up (Docker, native, Kubernetes) |
| [USER-MANUAL.md](USER-MANUAL.md) | Citizens, volunteers, department staff, responders |
| [ADMINISTRATOR-MANUAL.md](ADMINISTRATOR-MANUAL.md) | City administrators and superusers |
| [DEVOPS.md](DEVOPS.md) | Docker, CI/CD, testing strategy, monitoring, backup/DR |
| [KUBERNETES-AND-AWS.md](KUBERNETES-AND-AWS.md) | Helm/Kubernetes deployment and AWS/Terraform infrastructure |
| [COST-CONTROL.md](COST-CONTROL.md) | AWS cost estimate, budget alarms, teardown runbook |

## Project delivery

| Document | Contents |
|----------|----------|
| [PROJECT-MANAGEMENT.md](PROJECT-MANAGEMENT.md) | Milestones, risk register, maintenance, limitations, future work |
| [DEMO-SCRIPT.md](DEMO-SCRIPT.md) | Timed walkthrough for the SDP demonstration |
| [VIVA-QA.md](VIVA-QA.md) | Anticipated viva questions with model answers |
| [../architecture-diagram.md](../architecture-diagram.md) | Standalone Mermaid diagrams |

---

## Generated artifacts

The OpenAPI schema is **generated from the code**, never hand-edited:

```bash
make openapi    # writes docs/api-schema.yaml via drf-spectacular
```

Live, always-current API docs are served by the running backend:

| Format | URL (with this repo's `.env`: `BACKEND_PORT=18081`) |
|--------|-----|
| Swagger UI | http://localhost:18081/api/schema/swagger/ |
| Redoc | http://localhost:18081/api/schema/redoc/ |
| Raw OpenAPI 3 | http://localhost:18081/api/schema/ |

> `docs/api-schema.yaml` is a build artifact. If it is absent from a fresh clone,
> run `make openapi` (or read the live Swagger UI above) rather than trusting a
> checked-in copy.

---

## Conventions used in this package

- **Diagrams** are Mermaid and render natively on GitHub, in VS Code (with a Mermaid
  extension), and at <https://mermaid.live>.
- **Commands** are shown for both Docker and native execution where they differ.
- Shell examples use POSIX syntax; on Windows use Git Bash or WSL.
- **Seed credentials** in this package are deliberately fake and exist only for local
  demonstration. See [INSTALLATION-GUIDE.md](INSTALLATION-GUIDE.md#3-demo-credentials).
- Statements about behaviour are traced to code. Where the implementation diverges
  from the architecture proposal, this is recorded honestly in
  [PROJECT-MANAGEMENT.md](PROJECT-MANAGEMENT.md#2-known-limitations) rather than glossed over.

## Documentation status

`ARCHITECTURE.md` was approved at Phase 1 as the implementation baseline. The remaining
documents in this package are written **from the delivered code**, so they describe what
SafeCity actually does, including its current gaps.

Where a reader needs to know that something planned is not yet built, the doc says so
and links to [Known limitations](PROJECT-MANAGEMENT.md#2-known-limitations).
