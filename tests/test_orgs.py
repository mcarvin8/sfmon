"""Unit tests for orgs.py - org registry and multi-org connection building."""

import json
import os
import pytest
from unittest.mock import patch


class TestGetOrgNames:
    def test_legacy_mode_uses_org_name_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CONFIG_FILE_PATH", str(tmp_path / "missing.json"))
        monkeypatch.setenv("ORG_NAME", "my-org")
        from sfmon import config, orgs
        config.load_config(force_reload=True)
        assert orgs.get_org_names() == ["my-org"]

    def test_legacy_mode_defaults_to_default_when_org_name_unset(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CONFIG_FILE_PATH", str(tmp_path / "missing.json"))
        monkeypatch.delenv("ORG_NAME", raising=False)
        from sfmon import config, orgs
        config.load_config(force_reload=True)
        assert orgs.get_org_names() == ["default"]

    def test_fleet_mode_uses_orgs_from_config(self, tmp_path, monkeypatch):
        cfg = {"orgs": ["prod", "sandbox-uat"]}
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps(cfg))
        monkeypatch.setenv("CONFIG_FILE_PATH", str(cfg_file))
        from sfmon import config, orgs
        config.load_config(force_reload=True)
        assert orgs.get_org_names() == ["prod", "sandbox-uat"]


class TestIsFleetMode:
    def test_false_without_orgs(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CONFIG_FILE_PATH", str(tmp_path / "missing.json"))
        from sfmon import config, orgs
        config.load_config(force_reload=True)
        assert orgs.is_fleet_mode() is False

    def test_true_with_orgs(self, tmp_path, monkeypatch):
        cfg = {"orgs": ["prod"]}
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps(cfg))
        monkeypatch.setenv("CONFIG_FILE_PATH", str(cfg_file))
        from sfmon import config, orgs
        config.load_config(force_reload=True)
        assert orgs.is_fleet_mode() is True


class TestAuthUrlEnvVar:
    def test_legacy_mode_uses_plain_var(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CONFIG_FILE_PATH", str(tmp_path / "missing.json"))
        from sfmon import config, orgs
        config.load_config(force_reload=True)
        assert orgs.auth_url_env_var("default") == "SALESFORCE_AUTH_URL"

    def test_fleet_mode_builds_suffixed_var(self, tmp_path, monkeypatch):
        cfg = {"orgs": ["prod", "sandbox-uat"]}
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps(cfg))
        monkeypatch.setenv("CONFIG_FILE_PATH", str(cfg_file))
        from sfmon import config, orgs
        config.load_config(force_reload=True)
        assert orgs.auth_url_env_var("prod") == "SALESFORCE_AUTH_URL_PROD"
        assert orgs.auth_url_env_var("sandbox-uat") == "SALESFORCE_AUTH_URL_SANDBOX_UAT"


class TestBuildConnections:
    def test_connects_to_every_configured_org(self, tmp_path, monkeypatch):
        cfg = {"orgs": ["prod", "sandbox"]}
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps(cfg))
        monkeypatch.setenv("CONFIG_FILE_PATH", str(cfg_file))
        monkeypatch.setenv("SALESFORCE_AUTH_URL_PROD", "force://id:secret:token@prod.my.salesforce.com")
        monkeypatch.setenv("SALESFORCE_AUTH_URL_SANDBOX", "force://id:secret:token@sandbox.my.salesforce.com")
        from sfmon import config, orgs
        config.load_config(force_reload=True)

        fake_conn = object()
        with patch("sfmon.orgs.get_salesforce_connection_url", return_value=fake_conn) as mock_connect:
            connections = orgs.build_connections()

        assert connections == {"prod": fake_conn, "sandbox": fake_conn}
        assert mock_connect.call_count == 2

    def test_skips_org_that_fails_to_authenticate_without_raising(self, tmp_path, monkeypatch):
        cfg = {"orgs": ["prod", "broken"]}
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps(cfg))
        monkeypatch.setenv("CONFIG_FILE_PATH", str(cfg_file))
        monkeypatch.setenv("SALESFORCE_AUTH_URL_PROD", "force://id:secret:token@prod.my.salesforce.com")
        monkeypatch.delenv("SALESFORCE_AUTH_URL_BROKEN", raising=False)
        from sfmon import config, orgs
        config.load_config(force_reload=True)

        fake_conn = object()

        def fake_connect(url):
            if not url:
                raise ValueError("SFDX authentication URL is required")
            return fake_conn

        with patch("sfmon.orgs.get_salesforce_connection_url", side_effect=fake_connect):
            connections = orgs.build_connections()

        assert connections == {"prod": fake_conn}

    def test_legacy_single_org_connects_via_plain_auth_url(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CONFIG_FILE_PATH", str(tmp_path / "missing.json"))
        monkeypatch.setenv("ORG_NAME", "prod")
        monkeypatch.setenv("SALESFORCE_AUTH_URL", "force://id:secret:token@my.salesforce.com")
        from sfmon import config, orgs
        config.load_config(force_reload=True)

        fake_conn = object()
        with patch("sfmon.orgs.get_salesforce_connection_url", return_value=fake_conn) as mock_connect:
            connections = orgs.build_connections()

        assert connections == {"prod": fake_conn}
        mock_connect.assert_called_once_with(
            url="force://id:secret:token@my.salesforce.com"
        )
