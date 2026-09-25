"""
Announcements API: public list, admin CRUD + publish.
"""

from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsCityAdmin
from apps.announcements.models import Announcement
from apps.announcements.serializers import AnnouncementSerializer
from apps.audit.services import log_action


class AnnouncementViewSet(viewsets.ModelViewSet):
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.AllowAny()]
        return [IsCityAdmin()]

    def get_queryset(self):
        qs = Announcement.objects.all()
        if self.action in ("list", "retrieve"):
            # Admins manage drafts too; everyone else sees published only.
            if IsCityAdmin().has_permission(self.request, self):
                return qs
            return qs.filter(is_published=True)
        return qs

    def perform_create(self, serializer):
        serializer.save()
        log_action(
            actor=self.request.user,
            action="announcement.created",
            obj=serializer.instance,
            request=self.request,
        )

    def perform_update(self, serializer):
        serializer.save()
        log_action(
            actor=self.request.user,
            action="announcement.updated",
            obj=serializer.instance,
            request=self.request,
        )

    def perform_destroy(self, instance):
        log_action(
            actor=self.request.user,
            action="announcement.deleted",
            changes={"id": str(instance.id)},
            request=self.request,
        )
        instance.delete()

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        announcement = self.get_object()
        announcement.publish(by=request.user)
        log_action(
            actor=request.user, action="announcement.published", obj=announcement, request=request
        )
        return Response(AnnouncementSerializer(announcement).data)
