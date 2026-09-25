"""
Notification routes: /api/v1/notifications/
"""

from django.urls import path

from apps.notifications.views import (
    NotificationListView,
    NotificationReadAllView,
    NotificationReadView,
)

urlpatterns = [
    path("notifications/", NotificationListView.as_view(), name="notifications"),
    path("notifications/<uuid:pk>/read/", NotificationReadView.as_view(), name="notification-read"),
    path(
        "notifications/read-all/", NotificationReadAllView.as_view(), name="notification-read-all"
    ),
]
