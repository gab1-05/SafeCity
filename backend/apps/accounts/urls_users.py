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
    UserUnblockReportingView,
    UserUnlockView,
    UserViewSet,
)
from apps.accounts.views_role_requests import RoleRequestListCreateView, RoleRequestReviewView

router = DefaultRouter()
router.register("", UserViewSet, basename="users")

urlpatterns = [
    path("<uuid:pk>/role/", UserRoleUpdateView.as_view(), name="user-role-update"),
    path("<uuid:pk>/deactivate/", UserDeactivateView.as_view(), name="user-deactivate"),
    path("<uuid:pk>/unlock/", UserUnlockView.as_view(), name="user-unlock"),
    path("<uuid:pk>/unblock-reporting/", UserUnblockReportingView.as_view(), name="user-unblock-reporting"),
    path("deletion-requests/", DeletionRequestListView.as_view(), name="deletion-requests"),
    path("role-requests/", RoleRequestListCreateView.as_view(), name="role-requests"),
    path(
        "role-requests/<uuid:pk>/review/",
        RoleRequestReviewView.as_view(),
        name="role-request-review",
    ),
    path(
        "deletion-requests/<uuid:pk>/process/",
        DeletionRequestProcessView.as_view(),
        name="deletion-request-process",
    ),
    path("", include(router.urls)),
]
