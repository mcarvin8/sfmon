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
    - OTEL_EXPORTER_OTLP_ENDPOINT: optional. If set, log records are also
      pushed there (in addition to stdout) for backends that ingest OTLP logs
      directly (Datadog, Honeycomb, ...) rather than tailing container
      stdout. The "event" payload passed via extra={"event": {...}} survives
      as a structured log attribute over OTLP — nested values are supported
      there, unlike Prometheus metric labels. Unset, behavior is unchanged.

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


def _build_handlers():
    """Stdout JSON handler is always on; OTLP push is added only when
    OTEL_EXPORTER_OTLP_ENDPOINT is set, so default behavior is unchanged."""
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(JsonFormatter())
    handlers = [stream_handler]

    if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
        # pylint: disable=import-outside-toplevel
        # LoggingHandler from opentelemetry-sdk._logs is deprecated in favor
        # of this one from opentelemetry-instrumentation-logging — same
        # logger_provider= interface and extra={"event": {...}} forwarding,
        # plus a recursion-deadlock fix the SDK version lacks.
        from opentelemetry.exporter.otlp.proto.http._log_exporter import (
            OTLPLogExporter,
        )
        from opentelemetry.instrumentation.logging.handler import LoggingHandler
        from opentelemetry.sdk._logs import LoggerProvider
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

        otlp_provider = LoggerProvider()
        otlp_provider.add_log_record_processor(
            BatchLogRecordProcessor(OTLPLogExporter())
        )
        handlers.append(LoggingHandler(logger_provider=otlp_provider))

    return handlers


logging.basicConfig(level=getattr(logging, LOG_LEVEL), handlers=_build_handlers(), force=True)

logger = logging.getLogger(__name__)
