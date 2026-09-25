"""
Department API: list/detail plus workload statistics.
"""

from django.db.models import Count, Q
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import Department, UserRole
from apps.accounts.permissions import IsAuthority
from apps.accounts.serializers import DepartmentSerializer
from apps.incidents.models import Incident, IncidentStatus


class DepartmentViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    # Annotated so DepartmentSerializer.member_count never reads a relation
    # (or runs a COUNT) per row.
    queryset = Department.objects.filter(is_active=True).annotate(
        member_count=Count("members", filter=Q(members__is_active=True), distinct=True)
    )
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.AllowAny]  # reference data for reporting form
    ordering = ["name"]

    @action(detail=True, methods=["get"], permission_classes=[IsAuthority])
    def workload(self, request, pk=None):
        """Open incident counts per staff member of this department (ascending)."""
        staff = self.get_object().members.filter(role=UserRole.DEPARTMENT_STAFF, is_active=True)
        data = []
        for member in staff:
            open_count = Incident.objects.filter(
                assigned_staff=member,
                status__in=[
                    IncidentStatus.ASSIGNED,
                    IncidentStatus.IN_PROGRESS,
                    IncidentStatus.AWAITING_INFO,
                    IncidentStatus.REOPENED,
                ],
            ).count()
            data.append(
                {"id": str(member.id), "name": member.full_name, "open_incidents": open_count}
            )
        data.sort(key=lambda x: x["open_incidents"])
        return Response(data)
