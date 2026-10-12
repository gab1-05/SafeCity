"""
Request correlation middleware: assigns a unique ID per request, echoes it in
the response header, and stores it for the logging filter and audit entries.
"""

import uuid
from contextvars import ContextVar

_request_id_ctx: ContextVar[str] = ContextVar("safecity_request_id", default="-")


def get_request_id() -> str:
    """Return the current request id (or '-' outside a request, e.g. celery)."""
    return _request_id_ctx.get()


def _validated_request_id(raw: str | None) -> str:
    """Accept a client-supplied ID only if it is a UUID/32-hex value.

    Anything else (missing, overlong, or free-form text) is replaced with a
    freshly generated ID so log correlation and audit rows cannot be
    polluted or confused by untrusted input.
    """
    if raw:
        candidate = raw.strip()
        if len(candidate) <= 64:
            try:
                uuid.UUID(candidate)
                return candidate
            except ValueError:
                pass
            hexpart = candidate.replace("-", "")
            if len(hexpart) == 32 and all(
                c in "0123456789abcdefABCDEF" for c in hexpart
            ):
                return candidate
    return uuid.uuid4().hex


class RequestIDMiddleware:
    """Attach X-Request-ID to every request/response pair."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = _validated_request_id(request.headers.get("X-Request-ID"))
        token = _request_id_ctx.set(request_id)
        try:
            response = self.get_response(request)
        finally:
            # Never leak request-id state across requests/tasks sharing a thread
            _request_id_ctx.reset(token)
        response["X-Request-ID"] = request_id
        return response
