"""
Authentication views: registration, login (with lockout), refresh, logout,
profile, password reset (email-token), change password, session management,
two-factor authentication.
"""

import logging
from datetime import timedelta

from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.accounts.models import User
from apps.accounts.serializers import (
    ChangePasswordSerializer,
    MeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    SafeCityTokenObtainPairSerializer,
)
from apps.audit.services import log_action
from apps.notifications.services import notify

logger = logging.getLogger("safecity")

MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 15


class RegisterView(generics.CreateAPIView):
    """Citizen self-registration."""

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_scope = "auth"

    def perform_create(self, serializer):
        user = serializer.save()
        log_action(actor=user, action="auth.register", obj=user, request=self.request)
        notify(
            user=user,
            verb="welcome",
            title="Welcome to SafeCity",
            body="Your account is ready. Report civic issues and track their resolution.",
        )


class LoginThrottledView(TokenObtainPairView):
    """Login with brute-force lockout, 2FA support, and audit logging."""

    serializer_class = SafeCityTokenObtainPairSerializer
    throttle_scope = "auth"

    def post(self, request, *args, **kwargs):
        email = (request.data.get("email") or "").lower()

        # Brute-force defence: check the lockout BEFORE verifying credentials,
        # so a locked account cannot keep guessing passwords during the window.
        from datetime import timedelta as _timedelta

        from django.utils import timezone as _tz

        user = User.objects.filter(email__iexact=email).first()
        if user and user.locked_until and user.locked_until > _tz.now():
            remaining = int((user.locked_until - _tz.now()).total_seconds() // 60) + 1
            log_action(
                actor=None,
                action="auth.login_locked_attempt",
                changes={"email": email},
                request=request,
            )
            return Response(
                {
                    "detail": f"Account temporarily locked after too many failed logins. Try again in {remaining} minute(s).",
                    "code": "account_locked",
                },
                status=status.HTTP_423_LOCKED,
            )

        try:
            response = super().post(request, *args, **kwargs)
        except Exception:
            user = User.objects.filter(email__iexact=email).first()
            if user:
                user.failed_login_count += 1
                if user.failed_login_count >= MAX_FAILED_LOGINS:
                    user.locked_until = _tz.now() + _timedelta(minutes=LOCKOUT_MINUTES)
                    user.failed_login_count = 0
                    notify(
                        user=user,
                        verb="security_lockout",
                        title="Account locked temporarily",
                        body=f"Too many failed logins. Try again in {LOCKOUT_MINUTES} minutes.",
                    )
                    log_action(actor=user, action="auth.lockout", obj=user, request=request)
                user.save(update_fields=["failed_login_count", "locked_until"])
            log_action(
                actor=None, action="auth.login_failed", changes={"email": email}, request=request
            )
            raise
        user = User.objects.filter(email__iexact=email).first()
        if user is not None:
            user.failed_login_count = 0
            user.locked_until = None
            user.save(update_fields=["failed_login_count", "locked_until"])
            log_action(actor=user, action="auth.login", obj=user, request=request)

            payload = response.data
            # 2FA challenge: hand back a 2-minute access token carrying
            # `2fa_pending`. It authenticates ONLY the /auth/token/2fa/ exchange
            # (StrictJWTAuthentication rejects it everywhere else).
            if payload.get("requires_2fa"):
                challenge = AccessToken.for_user(user)
                challenge.set_exp(lifetime=timedelta(minutes=2))
                challenge["2fa_pending"] = True
                payload["access"] = str(challenge)
                return Response(payload, status=status.HTTP_200_OK)

        return response


class GoogleOAuthView(APIView):
    """
    POST /api/v1/auth/oauth/google/ {"id_token": "..."}

    Verifies a Google-issued ID token, auto-provisions a citizen account on
    first sign-in (email from Google, marked verified), and returns the same
    JWT pair + user payload as password login. Degrades to 503 when Google
    sign-in is not configured (no GOOGLE_CLIENT_ID).
    """

    permission_classes = [AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        from apps.accounts.oauth import google_enabled, verify_google_id_token

        if not google_enabled():
            return Response(
                {"detail": "Google sign-in is not configured on this server.", "code": "oauth_unconfigured"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        token = (request.data.get("id_token") or "").strip()
        if not token:
            return Response(
                {"detail": "id_token is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        # Optional: first-time Google *signup* can request an elevated role
        # (same rules as password signup — citizen account + pending request).
        from apps.accounts.models import Department, RoleRequest
        from apps.accounts.roles import REQUESTABLE_ROLES

        requested_role = (request.data.get("requested_role") or "").strip() or None
        if requested_role == "citizen":
            requested_role = None
        if requested_role and requested_role not in REQUESTABLE_ROLES:
            return Response(
                {"detail": "That role cannot be requested. Contact an administrator."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        requested_department = None
        if request.data.get("requested_department_id"):
            from uuid import UUID

            try:
                requested_department = Department.objects.filter(
                    pk=UUID(str(request.data["requested_department_id"])), is_active=True
                ).first()
            except (ValueError, AttributeError):
                requested_department = None
        role_request_reason = str(request.data.get("role_request_reason") or "")[:2000]
        try:
            claims = verify_google_id_token(token)
        except ValueError as exc:
            log_action(
                actor=None,
                action="auth.oauth_failed",
                changes={"reason": str(exc)},
                request=request,
            )
            return Response({"detail": str(exc)}, status=status.HTTP_401_UNAUTHORIZED)

        email = str(claims.get("email", "")).lower()
        if not email:
            return Response(
                {"detail": "Google account has no email address."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if not claims.get("email_verified", True):
            return Response(
                {"detail": "Google email is not verified."}, status=status.HTTP_401_UNAUTHORIZED
            )

        from django.utils import timezone

        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            user = User.objects.create_user(
                email=email,
                password=None,
                first_name=str(claims.get("given_name", ""))[:80],
                last_name=str(claims.get("family_name", ""))[:80],
            )
            user.email_verified_at = timezone.now()
            user.save(update_fields=["email_verified_at"])
            log_action(actor=user, action="auth.oauth_registered", obj=user, request=request)
            if requested_role:
                RoleRequest.objects.create(
                    user=user,
                    requested_role=requested_role,
                    department=requested_department,
                    reason=role_request_reason,
                )
                log_action(
                    actor=user,
                    action="user.role_requested",
                    obj=user,
                    changes={"requested_role": requested_role, "via": "oauth_signup"},
                    request=request,
                )
        elif not user.is_active or user.deleted_at:
            return Response(
                {"detail": "This account has been deactivated."},
                status=status.HTTP_403_FORBIDDEN,
            )
        else:
            if not user.email_verified_at:
                user.email_verified_at = timezone.now()
                user.save(update_fields=["email_verified_at"])

        user.failed_login_count = 0
        user.locked_until = None
        user.save(update_fields=["failed_login_count", "locked_until"])

        refresh = RefreshToken.for_user(user)
        refresh["role"] = user.role
        refresh["department_id"] = str(user.department_id) if user.department_id else None
        log_action(actor=user, action="auth.oauth_login", obj=user, request=request)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "role": user.role,
                    "full_name": user.full_name,
                },
            }
        )


class LogoutView(APIView):
    """Blacklist the provided refresh token (session invalidation)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response(
                {"detail": "Refresh token required."}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            token = RefreshToken(refresh)
            token.blacklist()
        except Exception:  # noqa: BLE001 — invalid/expired tokens are fine on logout
            pass
        log_action(actor=request.user, action="auth.logout", obj=request.user, request=request)
        return Response({"detail": "Logged out."})


class MeView(generics.RetrieveUpdateAPIView):
    """Current user profile: GET/PATCH."""

    serializer_class = MeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return ProfileUpdateSerializer
        return MeSerializer


class PasswordResetRequestView(APIView):
    """Request a password-reset email. Always returns 202 (no user enumeration)."""

    permission_classes = [AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(
            email__iexact=serializer.validated_data["email"], is_active=True
        ).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_link = (
                f"{request.scheme}://{request.get_host()}/reset-password?uid={uid}&token={token}"
            )
            send_mail(
                subject="SafeCity password reset",
                message=f"Reset your password using this link (valid for a short time):\n{reset_link}",
                from_email=None,
                recipient_list=[user.email],
                fail_silently=True,
            )
            log_action(
                actor=user, action="auth.password_reset_requested", obj=user, request=request
            )
        return Response(
            {"detail": "If the account exists, a reset link has been sent."},
            status=status.HTTP_202_ACCEPTED,
        )


class PasswordResetConfirmView(APIView):
    """Complete password reset with uid+token."""

    permission_classes = [AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            uid = force_str(urlsafe_base64_decode(data["uid"]))
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response({"detail": "Invalid reset link."}, status=status.HTTP_400_BAD_REQUEST)
        if not default_token_generator.check_token(user, data["token"]):
            return Response(
                {"detail": "Invalid or expired reset link."}, status=status.HTTP_400_BAD_REQUEST
            )
        user.set_password(data["password"])
        user.failed_login_count = 0
        user.locked_until = None
        user.save(update_fields=["password", "failed_login_count", "locked_until"])
        log_action(actor=user, action="auth.password_reset", obj=user, request=request)
        return Response({"detail": "Password updated. You can now log in."})


class ChangePasswordView(APIView):
    """Authenticated password change; invalidates all sessions."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        log_action(
            actor=request.user, action="auth.password_changed", obj=request.user, request=request
        )
        return Response({"detail": "Password changed. Please log in again."})


class SessionListView(APIView):
    """List outstanding refresh tokens (sessions) for the current user."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

        tokens = OutstandingToken.objects.filter(user=request.user).order_by("-created_at")
        blacklisted = set(request.user.blacklistedtoken_set.values_list("token_id", flat=True))
        data = [
            {
                "id": str(t.id),
                "created_at": t.created_at,
                "expires_at": t.expires_at,
                "active": str(t.id) not in blacklisted,
            }
            for t in tokens[:50]
        ]
        return Response(data)


class SessionDeleteView(APIView):
    """Revoke (blacklist) one session by outstanding-token id."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        from rest_framework_simplejwt.token_blacklist.models import (
            BlacklistedToken,
            OutstandingToken,
        )

        try:
            token = OutstandingToken.objects.get(pk=pk, user=request.user)
        except OutstandingToken.DoesNotExist:
            return Response({"detail": "Session not found."}, status=status.HTTP_404_NOT_FOUND)
        BlacklistedToken.objects.get_or_create(token=token)
        log_action(
            actor=request.user,
            action="auth.session_revoked",
            obj=request.user,
            changes={"session": str(pk)},
            request=request,
        )
        return Response({"detail": "Session revoked."})
