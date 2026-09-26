"""Role-request API: users request elevated roles, admins approve/reject."""

from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Department, RoleRequest, User
from apps.accounts.permissions import can_manage_users
from apps.accounts.serializers import (
    RoleRequestCreateSerializer,
    RoleRequestReviewSerializer,
    RoleRequestSerializer,
)
from apps.audit.services import log_action


class RoleRequestListCreateView(APIView):
    """GET: admin sees pending queue (or all with ?status=); users see own.
    POST: authenticated user creates a request for a requestable role."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if can_manage_users(request.user):
            status_filter = request.query_params.get("status", "pending")
            qs = RoleRequest.objects.select_related("user", "department", "reviewed_by")
            if status_filter and status_filter != "all":
                qs = qs.filter(status=status_filter)
            qs = qs.order_by("-created_at")[:200]
        else:
            qs = (
                RoleRequest.objects.filter(user=request.user)
                .select_related("user", "department", "reviewed_by")
                .order_by("-created_at")
            )
        return Response(RoleRequestSerializer(qs, many=True).data)

    def post(self, request):
        serializer = RoleRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if RoleRequest.objects.filter(user=request.user, status="pending").exists():
            return Response(
                {"detail": "You already have a pending role request."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        department = None
        if data.get("department_id"):
            department = Department.objects.filter(
                pk=data["department_id"], is_active=True
            ).first()
            if department is None:
                return Response(
                    {"detail": "Department not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        req = RoleRequest.objects.create(
            user=request.user,
            requested_role=data["requested_role"],
            department=department,
            reason=data.get("reason", ""),
        )
        log_action(
            actor=request.user,
            action="user.role_requested",
            obj=request.user,
            changes={"requested_role": req.requested_role},
            request=request,
        )
        return Response(RoleRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class RoleRequestReviewView(APIView):
    """Approve (applies role + department) or reject. Admin only."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not can_manage_users(request.user):
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        try:
            req = RoleRequest.objects.select_related("user", "department").get(pk=pk)
        except RoleRequest.DoesNotExist:
            return Response({"detail": "Request not found."}, status=status.HTTP_404_NOT_FOUND)
        if req.status != "pending":
            return Response(
                {"detail": f"Request already {req.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = RoleRequestReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decision = serializer.validated_data["decision"]

        user = req.user
        if decision == "approve":
            old_role = user.role
            user.role = req.requested_role
            if req.department_id:
                user.department_id = req.department_id
            user.save(update_fields=["role", "department_id"])
            # Keep any other pending requests from going stale.
            RoleRequest.objects.filter(user=user, status="pending").exclude(pk=req.pk).update(
                status="rejected",
                reviewed_by=request.user,
                reviewed_at=timezone.now(),
            )
            req.status = "approved"
            log_action(
                actor=request.user,
                action="user.role_changed",
                obj=user,
                changes={
                    "role": {"from": old_role, "to": user.role},
                    "via": "role_request",
                    "request_id": str(req.id),
                },
                request=request,
            )
        else:
            req.status = "rejected"
        req.reviewed_by = request.user
        req.reviewed_at = timezone.now()
        req.save(update_fields=["status", "reviewed_by", "reviewed_at"])
        log_action(
            actor=request.user,
            action="user.role_request_reviewed",
            obj=user,
            changes={"decision": decision, "requested_role": req.requested_role},
            request=request,
        )
        return Response(RoleRequestSerializer(req).data)
