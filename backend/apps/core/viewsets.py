"""
Reference-data viewsets (wards, zones).
"""

from rest_framework import mixins, viewsets

from apps.core.models import Ward, Zone
from apps.core.serializers import WardSerializer, ZoneSerializer


class WardViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Ward.objects.select_related("zone").all()
    serializer_class = WardSerializer
    filterset_fields = ["zone", "code"]
    search_fields = ["name", "code"]
    ordering = ["code"]


class ZoneViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Zone.objects.all()
    serializer_class = ZoneSerializer
    ordering = ["name"]
