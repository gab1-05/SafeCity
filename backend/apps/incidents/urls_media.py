"""
Media routes: /api/v1/incidents/media/ and /api/v1/incidents/media/<uuid>/.

These paths MUST be included before `apps.incidents.urls`, because the
incidents DefaultRouter registers `incidents/<pk>/` with a `[^/.]+` pk
pattern, which would otherwise match `incidents/media/` and 404.
"""

from django.urls import path

from apps.incidents.views_media import IncidentMediaViewSet

urlpatterns = [
    path(
        "incidents/media/",
        IncidentMediaViewSet.as_view({"get": "list", "post": "create"}),
        name="media-list-create",
    ),
    path(
        "incidents/media/<uuid:pk>/",
        IncidentMediaViewSet.as_view({"get": "retrieve", "delete": "destroy"}),
        name="media-detail",
    ),
]
