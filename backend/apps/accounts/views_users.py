"""
User management API (city admin / superuser only).
"""

from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import DeletionRequest, User, UserRole
from apps.accounts.permissions import can_manage_users
from apps.accounts.serializers import (
    UserManagementSerializer,
    UserRoleUpdateSerializer,
)
from apps.audit.services import log_action


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List/retrieve users for administration and assignment pickers.

    Staff assignment pickers get a lighter payload via ?lite=true.
    """

    serializer_class = UserManagementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = User.objects.select_related("department")
        if can_manage_users(user):
            return qs.order_by("email")
        # Staff can list colleagues in their department for assignment
        if user.role == UserRole.DEPARTMENT_STAFF and user.department_id:
            return qs.filter(department_id=user.department_id, is_active=True)
        return qs.none()

    def list(self, request, *args, **kwargs):
        # Support multiple roles: ?role=department_staff&role=emergency_responder&role=volunteer
        roles = request.query_params.getlist("role")
        if roles:
            self.queryset = self.filter_queryset(self.get_queryset()).filter(role__in=roles)
        return super().list(request, *args, **kwargs)


class UserRoleUpdateView(APIView):
    """Change a user's role/department. Admin only, fully audited."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not can_manage_users(request.user):
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = UserRoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        old_role, old_dept = user.role, user.department_id
        user.role = serializer.validated_data["role"]
        if "department_id" in serializer.validated_data:
            dept_id = serializer.validated_data["department_id"]
            user.department_id = dept_id
        user.save(update_fields=["role", "department_id"])
        log_action(
            actor=request.user,
            action="user.role_changed",
            obj=user,
            changes={
                "role": {"from": old_role, "to": user.role},
                "department_id": {"from": str(old_dept), "to": str(user.department_id)},
            },
            request=request,
        )
        return Response(UserManagementSerializer(user).data)


class UserDeactivateView(APIView):
    """Deactivate/reactivate a user (soft block). Admin only."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not can_manage_users(request.user):
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        if user.id == request.user.id:
            return Response(
                {"detail": "You cannot deactivate yourself."}, status=status.HTTP_400_BAD_REQUEST
            )
        user.is_active = not user.is_active
        if user.is_active:
            user.locked_until = None
            user.failed_login_count = 0
        user.save(update_fields=["is_active", "locked_until", "failed_login_count"])
        log_action(
            actor=request.user,
            action="user.activation_changed",
            obj=user,
            changes={"is_active": user.is_active, "locked_until": user.locked_until},
            request=request,
        )
        return Response({"id": str(user.id), "is_active": user.is_active, "locked_until": user.locked_until})


class UserUnlockView(APIView):
    """Clear a lockout and restore login access for an admin-managed account."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not can_manage_users(request.user):
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        if user.id == request.user.id:
            return Response({"detail": "You cannot unlock your own account."}, status=status.HTTP_400_BAD_REQUEST)
        user.failed_login_count = 0
        user.locked_until = None
        user.save(update_fields=["failed_login_count", "locked_until"])
        log_action(
            actor=request.user,
            action="user.account_unlocked",
            obj=user,
            changes={"locked_until": None},
            request=request,
        )
        return Response({"id": str(user.id), "is_active": user.is_active, "locked_until": None})


class DeletionRequestListView(APIView):
    """Pending account deletion requests. Admin only."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not can_manage_users(request.user):
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        reqs = DeletionRequest.objects.filter(status="pending").select_related("user")
        return Response(
            [
                {
                    "id": str(r.id),
                    "user_id": str(r.user_id),
                    "email": r.user.email,
                    "reason": r.reason,
                    "requested_at": r.created_at,
                }
                for r in reqs
            ]
        )


class DeletionRequestProcessView(APIView):
    """Approve (soft-delete account) or reject a deletion request. Admin only."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not can_manage_users(request.user):
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        try:
            req = DeletionRequest.objects.select_related("user").get(pk=pk)
        except DeletionRequest.DoesNotExist:
            return Response({"detail": "Request not found."}, status=status.HTTP_404_NOT_FOUND)
        decision = request.data.get("decision")
        if decision == "approve":
            req.user.soft_delete()
            req.status = "completed"
        elif decision == "reject":
            req.status = "rejected"
        else:
            return Response(
                {"detail": "decision must be 'approve' or 'reject'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        req.processed_by = request.user
        req.processed_at = timezone.now()
        req.save(update_fields=["status", "processed_by", "processed_at"])
        log_action(
            actor=request.user,
            action="account.deletion_processed",
            obj=req.user,
            changes={"decision": decision},
            request=request,
        )
        return Response({"detail": f"Request {decision}d."})


class UserUnblockReportingView(APIView):
    """Restore reporting access for a citizen who was auto-blocked. Admin only."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not can_manage_users(request.user):
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        if user.role != UserRole.CITIZEN:
            return Response(
                {"detail": "Only citizens can have reporting access restored."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not user.is_reporting_blocked:
            return Response(
                {"detail": "User is not blocked from reporting."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.false_report_count = 0
        user.rejected_report_count = 0
        user.is_reporting_blocked = False
        user.reporting_blocked_at = None
        user.reporting_blocked_reason = ""
        user.save(update_fields=[
            "false_report_count",
            "rejected_report_count",
            "is_reporting_blocked",
            "reporting_blocked_at",
            "reporting_blocked_reason",
        ])
        log_action(
            actor=request.user,
            action="user.reporting_unblocked",
            obj=user,
            changes={
                "false_report_count": 0,
                "rejected_report_count": 0,
                "is_reporting_blocked": False,
            },
            request=request,
        )
        return Response({"id": str(user.id), "is_reporting_blocked": False})
