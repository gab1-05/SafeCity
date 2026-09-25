"""
Announcement routes: /api/v1/announcements/
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.announcements.views import AnnouncementViewSet

router = DefaultRouter()
router.register("announcements", AnnouncementViewSet, basename="announcements")

urlpatterns = [path("", include(router.urls))]
