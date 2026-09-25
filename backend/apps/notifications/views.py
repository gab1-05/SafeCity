"""
Notification API: list, mark read, mark all read.
"""

from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import Notification


class NotificationListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = Notification.objects.filter(recipient=request.user)[:100]
        unread = Notification.objects.filter(recipient=request.user, read_at__isnull=True).count()
        return Response(
            {
                "unread_count": unread,
                "results": [
                    {
                        "id": str(n.id),
                        "verb": n.verb,
                        "title": n.title,
                        "body": n.body,
                        "incident_id": str(n.incident_id) if n.incident_id else None,
                        "payload": n.payload,
                        "read_at": n.read_at,
                        "created_at": n.created_at,
                    }
                    for n in qs
                ],
            }
        )


class NotificationReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        updated = Notification.objects.filter(
            recipient=request.user, pk=pk, read_at__isnull=True
        ).update(read_at=timezone.now())
        return Response({"detail": "Marked read." if updated else "Already read."})


class NotificationReadAllView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        count = Notification.objects.filter(recipient=request.user, read_at__isnull=True).update(
            read_at=timezone.now()
        )
        return Response({"detail": f"Marked {count} notifications read."})
