# Contributing to SafeCity

Thanks for contributing! This project follows a phased, review-driven workflow.

## Branching strategy

```
main        production-ready; protected; releases tagged v*
develop     integration branch; protected
feature/*   new features (feature/incident-wizard)
fix/*       bug fixes (fix/sla-deadline-drift)
release/*   release stabilization (release/v1.0)
hotfix/*    urgent fixes off main
```

Always branch from `develop` and open PRs back to `develop`. PRs to `main` go through
`release/*` and require review + green CI.

## Commit messages

Conventional Commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `ci:`.

```
feat(incidents): add workload-aware auto-assignment
fix(auth): lock account after 5 failed logins
```

## Pull requests

1. Fill the PR template; link related issues (`Closes #12`).
2. CI must be green: backend tests (coverage ≥ 80%), frontend tests + typecheck, lint, docker build, trivy scan, terraform fmt/validate (if infra touched).
3. Request review from CODEOWNERS.
4. Squash-merge with a descriptive subject.

## Local setup

See README "Quick start". Use `make lint && make test` before pushing.

## Code style

- Backend: Ruff (line length 100), docstrings on services/complex logic.
- Frontend: ESLint + Prettier; TypeScript strict; no `any`.
- No secrets in code — use environment variables.
- Every state-changing backend operation goes through the service layer and writes an audit log.
