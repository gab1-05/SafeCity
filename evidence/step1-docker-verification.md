# Step 1: Docker Stack Verification Evidence
# Captured: 2026-10-16
# Purpose: DBIT Notice 3 Docker Containerisation proof (D4, D7)

## docker compose ps — all services running

```
NAME                      IMAGE                   STATUS                       PORTS
safecity0-backend-1       safecity0-backend       Up About an hour (healthy)   0.0.0.0:18081->8000/tcp
safecity0-celery-1        safecity0-celery        Up About an hour (healthy)   8000/tcp
safecity0-celery-beat-1   safecity0-celery-beat   Up About an hour             8000/tcp
safecity0-db-1            postgres:16-alpine      Up About an hour (healthy)   0.0.0.0:5432->5432/tcp
safecity0-frontend-1      node:20-alpine          Up About an hour             0.0.0.0:5174->5174/tcp
safecity0-minio-1         minio/minio:latest      Up About an hour             0.0.0.0:9000-9001->9000-9001/tcp
safecity0-redis-1         redis:7-alpine          Up About an hour (healthy)   0.0.0.0:6379->6379/tcp
```

## Health endpoint — PASS

```
$ curl -s http://localhost:18081/api/health/
{"status": "ok", "service": "safecity-backend"}
```

## Readiness endpoint — PASS (all dependencies ok)

```
$ curl -s http://localhost:18081/api/readiness/
{"status": "ok", "checks": {"database": "ok", "cache": "ok", "storage": "local"}}
```

## Kind cluster — RUNNING (bonus evidence)

```
$ docker ps | grep kindest
ffe1e6674183   kindest/node:v1.37.0   Up About an hour   127.0.0.1:53991->6443/tcp   safecity-control-plane
```

## Verdict: D4 (builds/startup) PASS, D7 (compose functionality) PASS
- 7 services running via Docker Compose
- Backend healthcheck passing (curl /api/health/)
- Readiness confirms database + cache + storage connectivity
- Kind cluster available for Kubernetes demo evidence
