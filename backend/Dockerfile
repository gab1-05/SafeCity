# SafeCity backend — multi-stage, non-root
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

WORKDIR /app

# System deps for psycopg/Pillow builds are minimal with binary wheels
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ requirements/
RUN pip install -r requirements/prod.txt

COPY . .

# Collect static files at build time (WhiteNoise serves them)
RUN SECRET_KEY=build-time-only-secret-key-value-0000000000 \
    ALLOWED_HOSTS=localhost \
    python manage.py collectstatic --noinput || true

RUN addgroup --system safecity \
    && adduser --system --ingroup safecity safecity \
    && mkdir -p /app/media /app/staticfiles \
    && chown -R safecity:safecity /app
USER safecity

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health/ || exit 1

# Daphne serves HTTP + WebSocket (Channels) in one process
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
