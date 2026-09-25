"""
Google OAuth sign-in (ID token verification).

Design:
- The SPA obtains a Google ID token (Google Identity Services) and POSTs it to
  /api/v1/auth/oauth/google/ — stateless, no server-side session or redirect.
- Verification uses google-auth when installed; otherwise a stdlib fallback
  (signature check against Google's published JWKS via PyJWT-free RSA is NOT
  attempted) — we only allow the stdlib path when `django.conf.settings`
  explicitly sets OAUTH_ALLOW_UNVERIFIED_FALLBACK (dev only).
- Returns SafeCity JWTs + user. Auto-provisions citizens on first login.
"""

from __future__ import annotations

import logging

from django.conf import settings

logger = logging.getLogger("safecity")

GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = ("https://accounts.google.com", "aud:accounts.google.com")


def google_client_id() -> str:
    return str(settings.SAFECITY.get("GOOGLE_CLIENT_ID", "") or "")


def google_enabled() -> bool:
    return bool(google_client_id())


def verify_google_id_token(token: str) -> dict:
    """
    Verify a Google ID token and return its claims.

    Raises ValueError with a safe message on any failure. Prefers google-auth;
    falls back to a strict manual check (JWKS signature) only via PyJWT.
    """
    if not google_enabled():
        raise ValueError("Google sign-in is not configured on this server.")

    try:
        from google.auth.transport.requests import Request as GoogleRequest
        from google.oauth2 import id_token as google_id_token

        claims = google_id_token.verify_oauth2_token(
            token, GoogleRequest(), google_client_id()
        )
        if claims.get("iss") not in (
            "accounts.google.com",
            "https://accounts.google.com",
        ):
            raise ValueError("Invalid token issuer.")
        return claims
    except ImportError:
        pass

    # Optional PyJWT path (still a real cryptographic check).
    try:
        import jwt
        from jwt import PyJWKClient

        jwks_client = PyJWKClient(GOOGLE_CERTS_URL)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=google_client_id(),
        )
        if claims.get("iss") not in (
            "accounts.google.com",
            "https://accounts.google.com",
        ):
            raise ValueError("Invalid token issuer.")
        return claims
    except ImportError:
        raise ValueError(
            "Server is missing a JWT verification library (google-auth or pyjwt)."
        ) from None
