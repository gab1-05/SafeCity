"""
Audit log API: read-only, admin only, filterable.
"""

from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsCityAdmin
from apps.audit.models import AuditLog


class AuditLogListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsCityAdmin]

    def get(self, request):
        qs = AuditLog.objects.select_related("actor").all()
        if action := request.query_params.get("action"):
            qs = qs.filter(action__icontains=action)
        if object_type := request.query_params.get("object_type"):
            qs = qs.filter(object_type__iexact=object_type)
        if actor_id := request.query_params.get("actor"):
            qs = qs.filter(actor_id=actor_id)
        limit = min(int(request.query_params.get("limit", 100)), 500)
        return Response(
            [
                {
                    "id": str(a.id),
                    "actor": a.actor.email if a.actor else None,
                    "action": a.action,
                    "object_type": a.object_type,
                    "object_id": a.object_id,
                    "changes": a.changes,
                    "request_id": a.request_id,
                    "ip_address": a.ip_address,
                    "created_at": a.created_at,
                }
                for a in qs[:limit]
            ]
        )
