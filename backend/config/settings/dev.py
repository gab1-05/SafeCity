"""
Development settings — verbose, permissive for localhost, eager Celery optional.
"""

from .base import *
from .base import env

DEBUG = True
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "backend"])

# Dev convenience: console emails unless an SMTP host is configured
if SAFECITY["EMAIL_BACKEND_CONFIGURED"]:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = env("EMAIL_HOST")
    EMAIL_PORT = env("EMAIL_PORT", default=587)
    EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
    EMAIL_USE_TLS = True
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Keep the email inbox visible in dev
EMAIL_NOTIFICATION_FALLBACK_TO_DB = True
