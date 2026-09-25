"""
JWT authentication classes.

``StrictJWTAuthentication`` is the project-wide default: it behaves exactly like
SimpleJWT's ``JWTAuthentication`` except that it refuses *2FA challenge* tokens —
short-lived access tokens issued by the login endpoint when an account has
two-factor authentication enabled. Those tokens exist for one purpose only:
authorising the ``/api/v1/auth/token/2fa/`` exchange. The exchange endpoint
opts back in by using SimpleJWT's stock ``JWTAuthentication``.
"""

from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication


class StrictJWTAuthentication(JWTAuthentication):
    """Reject tokens carrying the ``2fa_pending`` claim."""

    def get_validated_token(self, raw_token):
        validated = super().get_validated_token(raw_token)
        if validated.payload.get("2fa_pending"):
            raise AuthenticationFailed(
                "Complete two-factor verification before using this token.",
                code="2fa_pending",
            )
        return validated
