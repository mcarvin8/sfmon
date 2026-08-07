"""Unit tests for logger.py"""

import logging
import os
from unittest.mock import patch


class TestLogger:
    def test_invalid_log_level_falls_back_to_info(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "NOTAVALIDLEVEL")
        import importlib
        import logger
        importlib.reload(logger)
        assert logger.LOG_LEVEL == "INFO"

    def test_valid_log_level_is_preserved(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        import importlib
        import logger
        importlib.reload(logger)
        assert logger.LOG_LEVEL == "DEBUG"


class TestBuildHandlers:
    def test_only_stream_handler_when_otlp_unset(self):
        import logger

        env = {k: v for k, v in os.environ.items() if k != "OTEL_EXPORTER_OTLP_ENDPOINT"}
        with patch.dict(os.environ, env, clear=True):
            handlers = logger._build_handlers()
        assert len(handlers) == 1
        assert isinstance(handlers[0], logging.StreamHandler)

    def test_adds_otlp_handler_when_endpoint_set(self):
        import logger

        with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector:4318"}), \
             patch("opentelemetry.exporter.otlp.proto.http._log_exporter.OTLPLogExporter"):
            handlers = logger._build_handlers()
        assert len(handlers) == 2
