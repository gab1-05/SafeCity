"""
Test settings — fast, deterministic, no external side effects.
"""

from .base import *

DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="safecity_test"),
        "USER": env("POSTGRES_USER", default="safecity"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="safecity"),
        "HOST": env("DB_HOST", default="localhost"),
        "PORT": env("DB_PORT", default="5432"),
        # Never reuse the real database for tests, even when POSTGRES_DB is
        # set (as in compose). A stray "test == dev" name destroyed data once;
        # the _test suffix guarantees isolation.
        "TEST": {"NAME": f"{env('POSTGRES_DB', default='safecity')}_test"},
    }
}

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # speed only

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    # Throttles disabled for tests, but rates stay defined because scoped
    # throttle classes resolve their rate at instantiation time.
    "DEFAULT_THROTTLE_CLASSES": (),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "1000/min",
        "user": "1000/min",
        "auth": "1000/min",
        "incident_create": "1000/hour",
        "media_upload": "1000/hour",
        "ai": "1000/hour",
    },
}

SAFECITY["EMAIL_BACKEND_CONFIGURED"] = False
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
