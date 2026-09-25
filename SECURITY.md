# Security Policy

## Reporting a vulnerability

**Do not open a public issue for security vulnerabilities.**

Email: security@safecity.local (SDP project — placeholder; replace with a monitored inbox)

Include: description, reproduction steps, affected component, impact assessment.
We acknowledge within 72 hours and aim to triage within 7 days.

## Supported versions

| Version | Supported |
|---------|-----------|
| main / develop | ✅ |

## Security controls summary

- JWT access (15 min) + rotating refresh (7 d) with blacklist; session invalidation UI
- Server-side RBAC + object-level permission checks on every endpoint
- Account lockout after repeated failed logins; rate limiting on auth & submissions
- Upload validation: extension, MIME, magic bytes, size caps; EXIF stripped; malware-scan adapter interface
- CORS allowlist, CSP, HSTS (prod), secure headers, secure cookies where applicable
- Secrets only via environment variables / K8s Secret templates / AWS Secrets Manager
- Append-only audit log for all state-changing actions (superuser included)
- Privacy-safe public responses: no citizen PII, jittered coordinates, unguessable share tokens
- Dependency and Docker image scanning (Trivy) in CI; dependabot recommended

## Deployment security checklist

See `docs/SECURITY-DESIGN.md` for the full design and `docs/runbooks/` for operational procedures.
