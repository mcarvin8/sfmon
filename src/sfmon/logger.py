"""
Logger Configuration Module

This module configures Python logging for the production monitoring service.
It emits single-line JSON records so log aggregation platforms (AWS CloudWatch
Logs, Loki, Vector, Fluent Bit, Datadog Logs) can parse structured fields
without a custom grok pattern. Collectors that need to expose per-record detail
(audit entries, deployments, login/geolocation events, report exports) that
doesn't belong in a low-cardinality Prometheus label should pass it via
`logger.info(msg, extra={"event": {...}})` — the payload is emitted under the
"event" key.

Environment Variables:
    - LOG_LEVEL: Logging verbosity level (default: INFO)
                 Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

Exports:
    - logger: Configured logging instance for use across monitoring modules
"""

import json
import logging
import os

# Get log level from environment variable, default to INFO
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Validate log level
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
if LOG_LEVEL not in VALID_LOG_LEVELS:
    LOG_LEVEL = "INFO"


class JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON.

    Any structured payload passed via `extra={"event": {...}}` is emitted
    under the "event" key so log pipelines can filter/query on its fields
    without parsing the free-text message.
    """

    def format(self, record):
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        event = getattr(record, "event", None)
        if event is not None:
            payload["event"] = event
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


_handler = logging.StreamHandler()
_handler.setFormatter(JsonFormatter())

logging.basicConfig(level=getattr(logging, LOG_LEVEL), handlers=[_handler], force=True)

logger = logging.getLogger(__name__)
