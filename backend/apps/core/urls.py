"""
Core API routes: wards, zones reference data, and geocoding.
"""

from django.urls import path
from rest_framework import routers

from apps.core.views import geocode_reverse, geocode_search
from apps.core.viewsets import WardViewSet, ZoneViewSet

router = routers.DefaultRouter(trailing_slash=True)
router.register("wards", WardViewSet, basename="wards")
router.register("zones", ZoneViewSet, basename="zones")

urlpatterns = [
    *router.urls,
    path("geocode/search/", geocode_search, name="geocode-search"),
    path("geocode/reverse/", geocode_reverse, name="geocode-reverse"),
]
