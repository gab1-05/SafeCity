"""
Profile views: preferences, saved locations, consent records, deletion request.
"""

from rest_framework import permissions, serializers, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import ConsentRecord, DeletionRequest, SavedLocation
from apps.audit.services import log_action
from apps.notifications.models import NotificationPreference


class NotificationPreferenceView(APIView):
    """GET/PATCH per-user notification preferences (created on demand)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        prefs, _ = NotificationPreference.objects.get_or_create(user=request.user)
        return Response(
            {
                "in_app": prefs.in_app,
                "email": prefs.email,
                "sms": prefs.sms,
                "push": prefs.push,
                "events_enabled": prefs.events_enabled or {},
            }
        )

    def patch(self, request):
        prefs, _ = NotificationPreference.objects.get_or_create(user=request.user)
        for field in ("in_app", "email", "sms", "push", "events_enabled"):
            if field in request.data:
                setattr(prefs, field, request.data[field])
        prefs.save()
        return Response({"detail": "Preferences updated."})


class SavedLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedLocation
        fields = ["id", "label", "latitude", "longitude", "address", "is_default"]


class SavedLocationViewSet(viewsets.ModelViewSet):
    """CRUD for the current user's saved locations."""

    serializer_class = SavedLocationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SavedLocation.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        if serializer.validated_data.get("is_default"):
            SavedLocation.objects.filter(user=self.request.user).update(is_default=False)
        serializer.save(user=self.request.user)


class ConsentListView(APIView):
    """List the current user's consent records."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        consents = ConsentRecord.objects.filter(user=request.user)
        return Response(
            [
                {
                    "id": str(c.id),
                    "kind": c.kind,
                    "version": c.version,
                    "granted_at": c.granted_at,
                    "revoked_at": c.revoked_at,
                }
                for c in consents
            ]
        )


class DeletionRequestView(APIView):
    """Create an account deletion request (processed by an administrator)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if DeletionRequest.objects.filter(user=request.user, status="pending").exists():
            return Response(
                {"detail": "A deletion request is already pending."},
                status=status.HTTP_409_CONFLICT,
            )
        DeletionRequest.objects.create(user=request.user, reason=request.data.get("reason", ""))
        log_action(
            actor=request.user,
            action="account.deletion_requested",
            obj=request.user,
            request=request,
        )
        return Response({"detail": "Deletion request submitted."}, status=status.HTTP_201_CREATED)
