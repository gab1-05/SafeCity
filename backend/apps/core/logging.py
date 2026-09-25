"""
Structured JSON logging with request correlation.
"""

import logging
from datetime import UTC

from apps.core.middleware import get_request_id


class RequestIDFilter(logging.Filter):
    """Injects request_id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


class JSONFormatter(logging.Formatter):
    """
    Minimal JSON log formatter (no external dependency). CloudWatch/ELK friendly.
    Unexpected values fall back to string representation so logging never raises.
    """

    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import datetime

        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        # Extra context passed via `extra={...}`
        for key, value in record.__dict__.items():
            if key not in payload and key not in {
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "msecs_str",
                "message",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "stack",
                "thread",
                "threadName",
                "taskName",
            }:
                try:
                    json.dumps(value)
                    payload[key] = value
                except (TypeError, ValueError):
                    payload[key] = str(value)
        return json.dumps(payload, ensure_ascii=False)
