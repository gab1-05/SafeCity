"""
User management routes: /api/v1/users/...
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.views_users import (
    DeletionRequestListView,
    DeletionRequestProcessView,
    UserDeactivateView,
    UserRoleUpdateView,
    UserUnlockView,
    UserViewSet,
)

router = DefaultRouter()
router.register("", UserViewSet, basename="users")

urlpatterns = [
    path("<uuid:pk>/role/", UserRoleUpdateView.as_view(), name="user-role-update"),
    path("<uuid:pk>/deactivate/", UserDeactivateView.as_view(), name="user-deactivate"),
    path("<uuid:pk>/unlock/", UserUnlockView.as_view(), name="user-unlock"),
    path("deletion-requests/", DeletionRequestListView.as_view(), name="deletion-requests"),
    path(
        "deletion-requests/<uuid:pk>/process/",
        DeletionRequestProcessView.as_view(),
        name="deletion-request-process",
    ),
    path("", include(router.urls)),
]
