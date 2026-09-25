"""
Consistent API error envelope and safe exception handling.
"""

import logging

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger("safecity")


def safecity_exception_handler(exc, context):
    """
    Wrap DRF errors in a consistent envelope and hide unexpected internals.

    Shape: {"detail": str, "code": str, "errors": {field: [msgs]}}
    Unexpected exceptions return a generic 500 without stack traces.
    """
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    response = drf_exception_handler(exc, context)

    if response is None:
        logger.exception("Unhandled API exception", extra={"view": str(context.get("view"))})
        return Response(
            {"detail": "An unexpected error occurred.", "code": "server_error", "errors": {}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(response.data, dict):
        errors = {
            field: msgs for field, msgs in response.data.items() if field not in ("detail", "code")
        }
        detail = response.data.get("detail", "Request failed.")
        # Prefer a code the raiser supplied explicitly (e.g. WorkflowError), then
        # fall back to the code DRF attached to the underlying ErrorDetail.
        explicit_code = response.data.get("code")
        code = explicit_code if explicit_code else getattr(detail, "code", "error")
    else:  # list-style errors from non-field checks
        errors = {}
        detail = "; ".join(str(m) for m in response.data) if response.data else "Request failed."
        code = "error"

    response.data = {"detail": str(detail), "code": str(code), "errors": errors}
    return response
