"""Unit tests for config.py."""

import json
import os
import pytest


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def test_no_file_returns_defaults(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CONFIG_FILE_PATH", str(tmp_path / "nonexistent.json"))
        import config
        result = config.load_config(force_reload=True)
        assert result["schedules"] == {}
        assert result["integration_user_names"] is None
        assert result["exclude_users"] == []

    def test_valid_file_loaded(self, tmp_path, monkeypatch):
        cfg = {
            "schedules": {"monitor_salesforce_limits": "*/5"},
            "integration_user_names": ["Bot1"],
            "exclude_users": ["Admin"],
        }
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps(cfg))
        monkeypatch.setenv("CONFIG_FILE_PATH", str(cfg_file))
        import config
        result = config.load_config(force_reload=True)
        assert result["schedules"] == {"monitor_salesforce_limits": "*/5"}
        assert result["integration_user_names"] == ["Bot1"]
        assert result["exclude_users"] == ["Admin"]

    def test_invalid_json_returns_defaults(self, tmp_path, monkeypatch):
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text("not valid json {{{")
        monkeypatch.setenv("CONFIG_FILE_PATH", str(cfg_file))
        import config
        result = config.load_config(force_reload=True)
        assert result["schedules"] == {}

    def test_empty_schedules_in_file(self, tmp_path, monkeypatch):
        cfg = {"schedules": {}, "integration_user_names": None, "exclude_users": []}
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps(cfg))
        monkeypatch.setenv("CONFIG_FILE_PATH", str(cfg_file))
        import config
        result = config.load_config(force_reload=True)
        assert result["schedules"] == {}

    def test_caching_avoids_re_read(self, tmp_path, monkeypatch):
        cfg = {"schedules": {"job_a": "*/10"}}
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps(cfg))
        monkeypatch.setenv("CONFIG_FILE_PATH", str(cfg_file))
        import config
        first = config.load_config(force_reload=True)
        # Overwrite the file - cached value should still be returned
        cfg_file.write_text(json.dumps({"schedules": {"job_b": "*/20"}}))
        second = config.load_config()
        assert second is first


# ---------------------------------------------------------------------------
# has_custom_schedules
# ---------------------------------------------------------------------------

class TestHasCustomSchedules:
    def test_no_file_returns_false(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CONFIG_FILE_PATH", str(tmp_path / "missing.json"))
        import config
        config.load_config(force_reload=True)
        assert config.has_custom_schedules() is False

    def test_file_with_schedules_returns_true(self, tmp_path, monkeypatch):
        cfg = {"schedules": {"my_job": "*/5"}}
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps(cfg))
        monkeypatch.setenv("CONFIG_FILE_PATH", str(cfg_file))
        import config
        config.load_config(force_reload=True)
        assert config.has_custom_schedules() is True


# ---------------------------------------------------------------------------
# parse_cron_schedule
# ---------------------------------------------------------------------------

class TestParseCronSchedule:
    @pytest.fixture(autouse=True)
    def _import(self):
        import config as c
        self.c = c

    def test_disabled_returns_none(self):
        assert self.c.parse_cron_schedule("disabled") is None
        assert self.c.parse_cron_schedule("DISABLED") is None
        assert self.c.parse_cron_schedule("none") is None
        assert self.c.parse_cron_schedule("") is None
        assert self.c.parse_cron_schedule(None) is None

    def test_simple_minute(self):
        result = self.c.parse_cron_schedule("*/5")
        assert result == {"minute": "*/5"}

    def test_five_part_cron(self):
        result = self.c.parse_cron_schedule("*/5 * * * *")
        assert result == {"minute": "*/5"}

    def test_five_part_cron_with_specific_values(self):
        result = self.c.parse_cron_schedule("30 7 * * *")
        assert result == {"minute": "30", "hour": "7"}

    def test_key_value_format_single(self):
        result = self.c.parse_cron_schedule("minute=*/5")
        assert result == {"minute": "*/5"}

    def test_key_value_format_multiple(self):
        result = self.c.parse_cron_schedule("hour=7,minute=30")
        assert result == {"hour": "7", "minute": "30"}

    def test_json_format(self):
        result = self.c.parse_cron_schedule('{"minute": "*/5"}')
        assert result == {"minute": "*/5"}

    def test_json_format_multiple_keys(self):
        result = self.c.parse_cron_schedule('{"hour": "7", "minute": "30"}')
        assert result == {"hour": "7", "minute": "30"}

    def test_comma_minute_list(self):
        result = self.c.parse_cron_schedule("10,50")
        assert result == {"minute": "10,50"}


# ---------------------------------------------------------------------------
# get_schedule_from_config
# ---------------------------------------------------------------------------

class TestGetScheduleFromConfig:
    def test_no_config_uses_default(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CONFIG_FILE_PATH", str(tmp_path / "missing.json"))
        import config
        config.load_config(force_reload=True)
        default = {"minute": "*/5"}
        result = config.get_schedule_from_config("my_job", default)
        assert result == default

    def test_no_config_opt_in_job_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CONFIG_FILE_PATH", str(tmp_path / "missing.json"))
        import config
        config.load_config(force_reload=True)
        result = config.get_schedule_from_config("pmd_job", None)
        assert result is None

    def test_opt_in_mode_job_not_listed_skipped(self, tmp_path, monkeypatch):
        cfg = {"schedules": {"other_job": "*/10"}}
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps(cfg))
        monkeypatch.setenv("CONFIG_FILE_PATH", str(cfg_file))
        import config
        config.load_config(force_reload=True)
        result = config.get_schedule_from_config("my_job", {"minute": "*/5"})
        assert result is None

    def test_opt_in_mode_job_listed_parsed(self, tmp_path, monkeypatch):
        cfg = {"schedules": {"my_job": "*/15"}}
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps(cfg))
        monkeypatch.setenv("CONFIG_FILE_PATH", str(cfg_file))
        import config
        config.load_config(force_reload=True)
        result = config.get_schedule_from_config("my_job", {"minute": "*/5"})
        assert result == {"minute": "*/15"}

    def test_opt_in_mode_disabled_job_returns_none(self, tmp_path, monkeypatch):
        cfg = {"schedules": {"my_job": "disabled"}}
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps(cfg))
        monkeypatch.setenv("CONFIG_FILE_PATH", str(cfg_file))
        import config
        config.load_config(force_reload=True)
        result = config.get_schedule_from_config("my_job", {"minute": "*/5"})
        assert result is None


# ---------------------------------------------------------------------------
# get_integration_user_names / get_exclude_users
# ---------------------------------------------------------------------------

class TestGettersFromConfig:
    def test_get_integration_user_names_none_when_unset(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CONFIG_FILE_PATH", str(tmp_path / "missing.json"))
        import config
        config.load_config(force_reload=True)
        assert config.get_integration_user_names() is None

    def test_get_integration_user_names_from_file(self, tmp_path, monkeypatch):
        cfg = {"schedules": {}, "integration_user_names": ["Bot"]}
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps(cfg))
        monkeypatch.setenv("CONFIG_FILE_PATH", str(cfg_file))
        import config
        config.load_config(force_reload=True)
        assert config.get_integration_user_names() == ["Bot"]

    def test_get_exclude_users_empty_default(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CONFIG_FILE_PATH", str(tmp_path / "missing.json"))
        import config
        config.load_config(force_reload=True)
        assert config.get_exclude_users() == []

    def test_get_exclude_users_from_file(self, tmp_path, monkeypatch):
        cfg = {"schedules": {}, "exclude_users": ["Admin", "Bot"]}
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps(cfg))
        monkeypatch.setenv("CONFIG_FILE_PATH", str(cfg_file))
        import config
        config.load_config(force_reload=True)
        assert config.get_exclude_users() == ["Admin", "Bot"]


class TestLoadConfigExceptions:
    def test_generic_exception_returns_defaults(self, tmp_path, monkeypatch):
        """Test that a non-JSON error (e.g. PermissionError) falls through to defaults."""
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text('{"schedules": {}}')
        monkeypatch.setenv("CONFIG_FILE_PATH", str(cfg_file))
        import config
        from unittest.mock import patch as _patch
        with _patch("builtins.open", side_effect=PermissionError("no access")):
            result = config.load_config(force_reload=True)
        assert result["schedules"] == {}

    def test_has_custom_schedules_triggers_load_when_cache_empty(self, tmp_path, monkeypatch):
        """has_custom_schedules() must call load_config() when cache is None."""
        monkeypatch.setenv("CONFIG_FILE_PATH", str(tmp_path / "missing.json"))
        import config
        # Reset so _config_file_has_schedules is None
        config._config_file_has_schedules = None
        result = config.has_custom_schedules()
        assert result is False  # No file → False


class TestParseCronScheduleUnparseable:
    def test_unparseable_string_returns_none(self):
        import config
        # "@ special" doesn't match any parser
        result = config.parse_cron_schedule("@ special cron")
        assert result is None

    def test_json_with_decode_error_falls_through(self):
        import config
        # Starts with { but invalid JSON → _parse_json_cron returns None → tries other parsers
        result = config.parse_cron_schedule('{"broken"')
        # Falls through to other parsers; none match either → returns None (with warning)
        assert result is None
