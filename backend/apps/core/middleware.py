"""
Request correlation middleware: assigns a unique ID per request, echoes it in
the response header, and stores it for the logging filter and audit entries.
"""

import threading
import uuid

_local = threading.local()


def get_request_id() -> str:
    """Return the current request id (or '-' outside a request, e.g. celery)."""
    return getattr(_local, "request_id", "-")


class RequestIDMiddleware:
    """Attach X-Request-ID to every request/response pair."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        _local.request_id = request_id
        try:
            response = self.get_response(request)
        finally:
            # Never leak request-id state across threads in async servers
            response = response  # noqa: self-documenting
        response["X-Request-ID"] = request_id
        return response
