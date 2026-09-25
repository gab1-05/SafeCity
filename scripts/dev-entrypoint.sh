#!/usr/bin/env bash
# SafeCity backend entrypoint: wait for DB, run migrations, exec the CMD.
set -euo pipefail

echo "[entrypoint] waiting for database…"
python - <<'PY'
import os, sys, time
import psycopg

for attempt in range(60):
    try:
        psycopg.connect(
            dbname=os.environ.get("POSTGRES_DB", "safecity"),
            user=os.environ.get("POSTGRES_USER", "safecity"),
            password=os.environ.get("POSTGRES_PASSWORD", "safecity"),
            host=os.environ.get("DB_HOST", "db"),
            port=os.environ.get("DB_PORT", "5432"),
            connect_timeout=3,
        ).close()
        print("[entrypoint] database is ready")
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        print(f"[entrypoint] attempt {attempt + 1}: {exc.__class__.__name__}")
        time.sleep(2)
print("[entrypoint] database never became ready", file=sys.stderr)
sys.exit(1)
PY

echo "[entrypoint] applying migrations…"
python manage.py migrate --noinput

echo "[entrypoint] starting: $*"
exec "$@"
