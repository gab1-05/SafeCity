"""
SafeCity root URL configuration.

API is versioned under /api/v1/. OpenAPI docs: /api/schema/swagger/ and
/api/schema/redoc/. Health/readiness under /api/.
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.core.views import health, meta_config, readiness
from apps.core.views_admin import AdminOverviewView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/readiness/", readiness, name="readiness"),
    path("api/meta/config/", meta_config, name="meta-config"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"
    ),
    path("api/schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("api/v1/auth/", include("apps.accounts.urls_auth")),
    path("api/v1/users/", include("apps.accounts.urls_users")),
    path("api/v1/", include("apps.core.urls")),
    # Grouped with the other api/v1/ includes so no non-api/v1/ path sits above them.
    path("api/v1/admin/overview/", AdminOverviewView.as_view(), name="admin-overview"),
    path("api/v1/", include("apps.accounts.urls_profile")),
    path("api/v1/", include("apps.departments.urls")),
    # Media routes are listed before the incidents router on purpose: the router
    # registers "incidents/<pk>/" with a `[^/.]+` pk pattern, which would
    # otherwise swallow "incidents/media/" and 404 every upload.
    path("api/v1/", include("apps.incidents.urls_media")),
    path("api/v1/", include("apps.incidents.urls")),
    path("api/v1/", include("apps.notifications.urls")),
    path("api/v1/", include("apps.announcements.urls")),
    path("api/v1/analytics/", include("apps.analytics.urls")),
    path("api/v1/audit-logs/", include("apps.audit.urls")),
    path("api/v1/ai/", include("apps.ai.urls")),
]

# Media in local development (S3 in production)
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
