"""
Two-factor authentication (TOTP) utilities.
"""

import base64
import hashlib
import hmac
import secrets
import struct
import time


def generate_totp_secret(length: int = 20) -> str:
    """Generate a base32-encoded TOTP secret."""
    return base64.b32encode(secrets.token_bytes(length)).decode("ascii").rstrip("=")


def generate_recovery_codes(count: int = 10, length: int = 8) -> list[str]:
    """Generate single-use recovery codes."""
    return [secrets.token_hex(length // 2).upper() for _ in range(count)]


def verify_totp_token(secret: str, token: str, window: int = 1) -> bool:
    """
    Verify a TOTP token against the secret.

    Args:
        secret: Base32-encoded secret
        token: 6-digit token from authenticator app
        window: Number of time steps (30s each) to check before/after current

    Returns:
        True if token is valid within the window
    """
    try:
        # Decode base32 secret
        key = base64.b32decode(secret.upper() + "=" * (-len(secret) % 8))
    except Exception:
        return False

    try:
        token_int = int(token)
    except ValueError:
        return False

    if not (100000 <= token_int <= 999999):
        return False

    current_time_step = int(time.time() // 30)

    for offset in range(-window, window + 1):
        time_step = current_time_step + offset
        expected = _hotp(key, time_step)
        if hmac.compare_digest(f"{expected:06d}", f"{token_int:06d}"):
            return True

    return False


def _hotp(key: bytes, counter: int, digits: int = 6) -> int:
    """Generate HMAC-based One-Time Password (HOTP)."""
    msg = struct.pack(">Q", counter)
    hmac_hash = hmac.new(key, msg, hashlib.sha1).digest()
    offset = hmac_hash[-1] & 0x0F
    code = (
        (hmac_hash[offset] & 0x7F) << 24
        | (hmac_hash[offset + 1] & 0xFF) << 16
        | (hmac_hash[offset + 2] & 0xFF) << 8
        | (hmac_hash[offset + 3] & 0xFF)
    )
    return code % (10 ** digits)


def hash_recovery_code(code: str) -> str:
    """Hash a recovery code for storage."""
    return hashlib.sha256(code.encode()).hexdigest()


def verify_recovery_code(stored_hash: str, provided_code: str) -> bool:
    """Verify a provided recovery code against its stored hash."""
    return hmac.compare_digest(hash_recovery_code(provided_code.upper()), stored_hash)
