"""
SafeCity — base Django settings shared by all environments.

Configuration is environment-driven (12-factor). Every external integration
(email, SMS, AI, S3, malware scanning) degrades to a safe local default when
its credentials are absent, so the platform runs with zero cloud setup.
"""

import os
from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    SECRET_KEY=(str, "insecure-dev-only-key-change-me"),
    ACCESS_TOKEN_MINUTES=(int, 15),
    REFRESH_TOKEN_DAYS=(int, 7),
    RATE_LIMIT_ANON_PER_MIN=(int, 30),
    RATE_LIMIT_INCIDENTS_PER_HOUR=(int, 5),
    ALLOW_ANONYMOUS_REPORTS=(bool, True),
    EMERGENCY_MODE_ENABLED=(bool, True),
    PUBLIC_COORD_JITTER_METERS=(int, 150),
    MEDIA_BACKEND=(str, "local"),
    PUBLIC_URL=(str, "http://localhost:5173"),
)

environ.Env.read_env(os.environ.get("SAFECITY_ENV_FILE", BASE_DIR.parent / ".env"))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

INSTALLED_APPS = [
    "daphne",  # must precede staticfiles for runserver ASGI
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",  # full-text search
    # Third party
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "django_celery_beat",
    # SafeCity apps
    "apps.core.apps.CoreConfig",
    "apps.accounts.apps.AccountsConfig",
    "apps.departments.apps.DepartmentsConfig",
    "apps.incidents.apps.IncidentsConfig",
    "apps.notifications.apps.NotificationsConfig",
    "apps.analytics.apps.AnalyticsConfig",
    "apps.announcements.apps.AnnouncementsConfig",
    "apps.audit.apps.AuditConfig",
    "apps.ai.apps.AIConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # SafeCity structured logging / request-id middleware
    "apps.core.middleware.RequestIDMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="safecity"),
        "USER": env("POSTGRES_USER", default="safecity"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="safecity"),
        "HOST": env("DB_HOST", default="localhost"),
        "PORT": env("DB_PORT", default="5432"),
        "CONN_MAX_AGE": 60,
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://localhost:6379/0"),
    }
}

# ── Channels (realtime) ──────────────────────────────────────
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [env("REDIS_URL", default="redis://localhost:6379/0")]},
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",  # preferred
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
]

# ── DRF ───────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.DefaultPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": f"{env('RATE_LIMIT_ANON_PER_MIN')}/min",
        "user": "120/min",
        "auth": "10/min",
        "incident_create": f"{env('RATE_LIMIT_INCIDENTS_PER_HOUR')}/hour",
        "media_upload": "30/hour",
        "ai": "20/hour",
    },
    "EXCEPTION_HANDLER": "apps.core.exceptions.safecity_exception_handler",
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env("ACCESS_TOKEN_MINUTES")),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env("REFRESH_TOKEN_DAYS")),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# ── OpenAPI ───────────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    "TITLE": "SafeCity API",
    "DESCRIPTION": "Smart City Incident Management and Civic Response Platform",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/api/v1",
}

# ── CORS / security headers ───────────────────────────────────
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
    ],
)
CORS_ALLOW_CREDENTIALS = False  # JWT via Authorization header, not cookies
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=[
        "http://localhost:5173",
        "http://localhost:8080",
    ],
)
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
REFERRER_POLICY = "same-origin"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False

# ── i18n ──────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Celery ────────────────────────────────────────────────────
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_TASK_ALWAYS_EAGER = False  # overridden in tests
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# ── SafeCity application settings ─────────────────────────────
SAFECITY = {
    "ALLOW_ANONYMOUS_REPORTS": env("ALLOW_ANONYMOUS_REPORTS"),
    "EMERGENCY_MODE_ENABLED": env("EMERGENCY_MODE_ENABLED"),
    "PUBLIC_COORD_JITTER_METERS": env("PUBLIC_COORD_JITTER_METERS"),
    "PUBLIC_URL": env("PUBLIC_URL"),
    "MEDIA_BACKEND": env("MEDIA_BACKEND"),  # local | s3
    "S3_ENDPOINT_URL": env("S3_ENDPOINT_URL", default=""),
    "AWS_S3_BUCKET": env("AWS_S3_BUCKET", default=""),
    "AWS_S3_REGION": env("AWS_S3_REGION", default="ap-south-1"),
    "AI_PROVIDER": env("AI_PROVIDER", default="mock"),
    "OPENAI_API_KEY": env("OPENAI_API_KEY", default=""),
    "OPENAI_BASE_URL": env("OPENAI_BASE_URL", default=""),
    "EMAIL_BACKEND_CONFIGURED": bool(env("EMAIL_HOST", default="")),
    "MALWARE_SCAN_PROVIDER": env("MALWARE_SCAN_PROVIDER", default="mock"),
    "CAPTCHA_PROVIDER": env("CAPTCHA_PROVIDER", default="mock"),
    "GOOGLE_CLIENT_ID": env("GOOGLE_CLIENT_ID", default=""),  # empty = OAuth disabled
}

# Upload limits
UPLOAD_LIMITS = {
    "image_max_mb": 10,
    "video_max_mb": 100,
    "doc_max_mb": 5,
    "allowed_image_types": ["image/jpeg", "image/png", "image/webp", "image/heic"],
    "allowed_video_types": ["video/mp4", "video/webm", "video/quicktime"],
    "allowed_doc_types": ["application/pdf"],
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "apps.core.logging.JSONFormatter",
        },
        "console": {"format": "[%(asctime)s] %(levelname)s %(name)s %(message)s"},
    },
    "filters": {"request_id": {"()": "apps.core.logging.RequestIDFilter"}},
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["request_id"],
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.db.backends": {"level": "WARNING"},
        "safecity": {"level": "INFO", "propagate": True},
    },
}
