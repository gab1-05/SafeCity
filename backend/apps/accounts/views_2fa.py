"""
Two-factor authentication views (TOTP + recovery codes).
"""

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.serializers import TwoFactorVerifySerializer
from apps.accounts.two_factor import (
    generate_recovery_codes,
    generate_totp_secret,
    hash_recovery_code,
    verify_recovery_code,
    verify_totp_token,
)
from apps.audit.services import log_action

logger = logging.getLogger("safecity")


class TwoFactorSetupView(APIView):
    """Generate TOTP secret and recovery codes for 2FA enrollment."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.two_factor_enabled:
            return Response({"detail": "2FA is already enabled."}, status=status.HTTP_400_BAD_REQUEST)

        secret = generate_totp_secret()
        recovery_codes = generate_recovery_codes()

        # Store secret temporarily in session (not in DB until verified)
        request.session["2fa_setup_secret"] = secret
        request.session["2fa_setup_recovery"] = [hash_recovery_code(c) for c in recovery_codes]

        # Return QR code URI for authenticator apps
        issuer = "SafeCity"
        account = user.email
        otpauth = f"otpauth://totp/{issuer}:{account}?secret={secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30"

        return Response(
            {
                "secret": secret,
                "otpauth_uri": otpauth,
                "recovery_codes": recovery_codes,  # Shown once only
            }
        )

    def post(self, request):
        """Verify the first TOTP token and enable 2FA."""
        user = request.user
        if user.two_factor_enabled:
            return Response({"detail": "2FA is already enabled."}, status=status.HTTP_400_BAD_REQUEST)

        secret = request.session.get("2fa_setup_secret")
        recovery_hashes = request.session.get("2fa_setup_recovery")

        if not secret or not recovery_hashes:
            return Response({"detail": "Setup session expired. Start over."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = TwoFactorVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]

        if not verify_totp_token(secret, token):
            log_action(actor=user, action="auth.2fa_setup_failed", obj=user, request=request)
            return Response({"detail": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)

        # Enable 2FA
        user.two_factor_enabled = True
        user.two_factor_secret = secret
        user.two_factor_recovery_codes = recovery_hashes
        user.save(update_fields=["two_factor_enabled", "two_factor_secret", "two_factor_recovery_codes"])

        # Clear session
        request.session.pop("2fa_setup_secret", None)
        request.session.pop("2fa_setup_recovery", None)

        log_action(actor=user, action="auth.2fa_enabled", obj=user, request=request)

        return Response({"detail": "Two-factor authentication enabled.", "recovery_codes": recovery_hashes})


class TwoFactorDisableView(APIView):
    """Disable 2FA (requires current TOTP or recovery code)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.two_factor_enabled:
            return Response({"detail": "2FA is not enabled."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = TwoFactorVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]

        # Check TOTP first
        if verify_totp_token(user.two_factor_secret, token):
            pass
        else:
            # Check recovery codes
            for i, stored_hash in enumerate(user.two_factor_recovery_codes):
                if verify_recovery_code(stored_hash, token):
                    # Remove used recovery code
                    user.two_factor_recovery_codes.pop(i)
                    user.save(update_fields=["two_factor_recovery_codes"])
                    break
            else:
                log_action(actor=user, action="auth.2fa_disable_failed", obj=user, request=request)
                return Response({"detail": "Invalid token or recovery code."}, status=status.HTTP_400_BAD_REQUEST)

        user.two_factor_enabled = False
        user.two_factor_secret = ""
        user.two_factor_recovery_codes = []
        user.save(update_fields=["two_factor_enabled", "two_factor_secret", "two_factor_recovery_codes"])

        log_action(actor=user, action="auth.2fa_disabled", obj=user, request=request)

        return Response({"detail": "Two-factor authentication disabled."})


class TwoFactorVerifyLoginView(APIView):
    """Verify TOTP or recovery code during login (called after password auth)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.two_factor_enabled:
            return Response({"detail": "2FA not required for this account."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = TwoFactorVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]

        if verify_totp_token(user.two_factor_secret, token):
            pass
        else:
            # Check recovery codes
            for i, stored_hash in enumerate(user.two_factor_recovery_codes):
                if verify_recovery_code(stored_hash, token):
                    user.two_factor_recovery_codes.pop(i)
                    user.save(update_fields=["two_factor_recovery_codes"])
                    break
            else:
                log_action(actor=user, action="auth.2fa_login_failed", obj=user, request=request)
                return Response({"detail": "Invalid token or recovery code."}, status=status.HTTP_400_BAD_REQUEST)

        log_action(actor=user, action="auth.2fa_login_success", obj=user, request=request)
        return Response({"detail": "2FA verified."})


class TwoFactorRegenerateRecoveryCodesView(APIView):
    """Regenerate recovery codes (requires TOTP)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.two_factor_enabled:
            return Response({"detail": "2FA not enabled."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = TwoFactorVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]

        if not verify_totp_token(user.two_factor_secret, token):
            return Response({"detail": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)

        recovery_codes = generate_recovery_codes()
        user.two_factor_recovery_codes = [hash_recovery_code(c) for c in recovery_codes]
        user.save(update_fields=["two_factor_recovery_codes"])

        log_action(actor=user, action="auth.2fa_recovery_regenerated", obj=user, request=request)

        return Response({"recovery_codes": recovery_codes})
