"""
Public tracking: citizens follow progress via reference number + no auth.
Privacy: returns the public serializer only (no reporter PII, jittered coords).
"""

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.incidents.models import Incident
from apps.incidents.serializers import IncidentPublicSerializer


class PublicTrackingView(APIView):
    """GET /api/v1/incidents/track/<reference>/ — public status tracking."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_scope = "anon"

    def get(self, request, reference: str):
        incident = (
            Incident.objects.filter(
                reference_number__iexact=reference,
                deleted_at__isnull=True,
            )
            .exclude(is_anonymous=True)
            .first()
        )
        if incident is None:
            return Response({"detail": "Incident not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(IncidentPublicSerializer(incident, context={"request": request}).data)
