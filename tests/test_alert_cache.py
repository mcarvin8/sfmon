"""Unit tests for alert_cache.py"""

import json

import pytest


class TestGetCacheDir:
    def test_default_relative_to_cwd(self, monkeypatch, tmp_path):
        from sfmon import alert_cache

        monkeypatch.delenv("SLACK_ALERT_CACHE_DIR", raising=False)
        monkeypatch.chdir(tmp_path)
        assert alert_cache.get_cache_dir() == tmp_path / "sfmon_alert_cache"

    def test_env_override_relative(self, monkeypatch, tmp_path):
        from sfmon import alert_cache

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("SLACK_ALERT_CACHE_DIR", "custom_cache")
        assert alert_cache.get_cache_dir() == tmp_path / "custom_cache"

    def test_env_override_absolute(self, monkeypatch, tmp_path):
        from sfmon import alert_cache

        abs_dir = tmp_path / "abs_cache"
        monkeypatch.setenv("SLACK_ALERT_CACHE_DIR", str(abs_dir))
        assert alert_cache.get_cache_dir() == abs_dir


class TestSafeKey:
    def test_sanitizes_special_characters(self):
        from sfmon.alert_cache import _safe_key

        assert _safe_key("prod/org name!") == "prod_org_name_"

    def test_empty_string_becomes_underscore(self):
        from sfmon.alert_cache import _safe_key

        assert _safe_key("") == "_"


@pytest.fixture(autouse=True)
def isolated_cache_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("SLACK_ALERT_CACHE_DIR", str(tmp_path / "cache"))


class TestLoadActiveItems:
    def test_missing_file_returns_empty_dict(self):
        from sfmon.alert_cache import load_active_items

        assert load_active_items("prod", "salesforce_limits") == {}

    def test_roundtrip_save_then_load(self):
        from sfmon.alert_cache import load_active_items, save_active_items

        items = {"DailyApiRequests": {"title": "over limit", "severity": "critical"}}
        save_active_items("prod", "salesforce_limits", items)
        assert load_active_items("prod", "salesforce_limits") == items

    def test_corrupt_json_returns_empty_dict(self, tmp_path):
        from sfmon import alert_cache

        cache_file = alert_cache._cache_path("prod", "salesforce_limits")
        cache_file.write_text("not json", encoding="utf-8")
        assert alert_cache.load_active_items("prod", "salesforce_limits") == {}

    def test_non_dict_json_returns_empty_dict(self):
        from sfmon import alert_cache

        cache_file = alert_cache._cache_path("prod", "salesforce_limits")
        cache_file.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        assert alert_cache.load_active_items("prod", "salesforce_limits") == {}

    def test_different_org_category_use_different_files(self):
        from sfmon.alert_cache import load_active_items, save_active_items

        save_active_items("prod", "salesforce_limits", {"a": {"title": "x"}})
        save_active_items("sandbox", "salesforce_limits", {"b": {"title": "y"}})
        assert load_active_items("prod", "salesforce_limits") == {"a": {"title": "x"}}
        assert load_active_items("sandbox", "salesforce_limits") == {"b": {"title": "y"}}


class TestSaveActiveItems:
    def test_creates_cache_dir_if_missing(self, tmp_path):
        from sfmon import alert_cache

        assert not alert_cache.get_cache_dir().exists()
        alert_cache.save_active_items("prod", "salesforce_limits", {})
        assert alert_cache.get_cache_dir().exists()

    def test_no_leftover_temp_file(self):
        from sfmon import alert_cache

        alert_cache.save_active_items("prod", "salesforce_limits", {"a": {"title": "x"}})
        cache_file = alert_cache._cache_path("prod", "salesforce_limits")
        assert cache_file.exists()
        assert not cache_file.with_suffix(".json.tmp").exists()

    def test_save_failure_logs_and_does_not_raise(self, monkeypatch):
        from sfmon import alert_cache

        def _boom(*args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(alert_cache, "open", _boom, raising=False)
        alert_cache.save_active_items("prod", "salesforce_limits", {"a": {"title": "x"}})
