# SafeCity Architecture Diagram

> Render the Mermaid blocks in any Mermaid-compatible viewer (GitHub renders them natively).

## System context

See `docs/ARCHITECTURE.md` §1.1 (C4 context diagram).

## Incident lifecycle

```mermaid
flowchart LR
    Citizen[Citizen] -- submits --> API[DRF API]
    API --> V{Authority verification}
    V -- verified --> A[Assignment]
    V -- rejected/duplicate --> X[Closed / merged]
    A --> S[Department staff workflow]
    S --> R[Resolved + evidence]
    R --> C{Citizen confirms?}
    C -- yes --> CL[Closed]
    C -- no --> RO[Reopened]
    RO --> S
    S -. SLA breach .-> E[Escalation]
    E --> S
    API -. every transition .-> AL[(Audit log)]
    API -. events .-> N[Notifications + WebSocket]
```

## Deployment (Docker Compose, local)

```mermaid
flowchart LR
    subgraph compose[docker compose network]
        FE[frontend :5173/80] --> BE[backend :8080]
        BE --> DB[(postgres :5432)]
        BE --> RD[(redis :6379)]
        BE --> M[(minio :9000)]
        CW[celery worker] --> RD
        CB[celery beat] --> RD
        CW --> DB
        BE --> CW
    end
    User[Browser] --> FE
    User --> BE
```

## Deployment (AWS/EKS)

See `docs/ARCHITECTURE.md` §12 (AWS architecture flowchart).
