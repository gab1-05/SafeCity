"""
Serializers for core reference data.
"""

from rest_framework import serializers

from apps.core.models import Ward, Zone


class ZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = ["id", "name", "code"]


class WardSerializer(serializers.ModelSerializer):
    zone = ZoneSerializer(read_only=True)
    zone_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = Ward
        fields = ["id", "name", "code", "zone", "zone_id", "latitude", "longitude"]
