"""Uniform JSON error format for every API error.

    {"error": {"status": 400, "code": "validation_error", "message": "...", "details": {...}}}
"""
import logging

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:  # unhandled -> 500, never leak internals
        logger.exception("Unhandled error", exc_info=exc)
        return Response(
            {"error": {"status": 500, "code": "server_error",
                       "message": "Internal server error", "details": None}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, ValidationError):
        code, message, details = "validation_error", "Validation failed", response.data
    else:
        code = getattr(exc, "default_code", "error")
        data = response.data
        message = str(data.get("detail", "Error")) if isinstance(data, dict) else str(data)
        details = None

    response.data = {
        "error": {"status": response.status_code, "code": code,
                  "message": message, "details": details}
    }
    return response
