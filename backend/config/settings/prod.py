"""
Production settings — hardened: HSTS, secure cookies, no debug, strict CORS.
"""

from .base import *
from .base import env

DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")  # required, no default
assert ALLOWED_HOSTS, "ALLOWED_HOSTS must be set in production"

# Force HTTPS
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Production email — SMTP required for user-facing mail
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = True

# Celery runs as real workers in production
CELERY_TASK_ALWAYS_EAGER = False

# Sendfile-compatible static serving is handled by WhiteNoise in the backend image;
# the SPA is served by nginx in the frontend image.
