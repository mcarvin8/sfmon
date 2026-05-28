"""Unit tests for logger.py"""

import logging


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
