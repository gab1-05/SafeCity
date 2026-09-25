"""
Profile routes mounted at /api/v1/: notification preferences, saved locations,
consent records, account deletion request.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.views_profile import (
    ConsentListView,
    DeletionRequestView,
    NotificationPreferenceView,
    SavedLocationViewSet,
)

router = DefaultRouter()
router.register("saved-locations", SavedLocationViewSet, basename="saved-locations")

urlpatterns = [
    path(
        "profile/notification-preferences/",
        NotificationPreferenceView.as_view(),
        name="notification-preferences",
    ),
    path("profile/consents/", ConsentListView.as_view(), name="consents"),
    path("profile/deletion-request/", DeletionRequestView.as_view(), name="deletion-request"),
    path("", include(router.urls)),
]
