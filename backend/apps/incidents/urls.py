"""
Incident routes.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.incidents.views import (
    DuplicateCheckView,
    EscalationRuleViewSet,
    IncidentCategoryViewSet,
    IncidentViewSet,
    PublicByTokenView,
    SLAConfigurationViewSet,
)
from apps.incidents.views_public import PublicTrackingView

router = DefaultRouter()
router.register("incidents", IncidentViewSet, basename="incidents")
router.register("categories", IncidentCategoryViewSet, basename="categories")
router.register("sla-config", SLAConfigurationViewSet, basename="sla-config")
router.register("escalation-rules", EscalationRuleViewSet, basename="escalation-rules")

urlpatterns = [
    path("incidents/duplicates/check/", DuplicateCheckView.as_view(), name="duplicate-check"),
    path("incidents/track/<str:reference>/", PublicTrackingView.as_view(), name="public-tracking"),
    path("incidents/public/<uuid:token>/", PublicByTokenView.as_view(), name="public-by-token"),
    path("", include(router.urls)),
]
