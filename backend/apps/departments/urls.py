"""
Department routes.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.departments.views import DepartmentViewSet

router = DefaultRouter()
router.register("departments", DepartmentViewSet, basename="departments")

urlpatterns = [
    path("", include(router.urls)),
]
