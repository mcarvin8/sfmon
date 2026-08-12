"""Unit tests for orgs.py - org registry and multi-org connection building."""

import json
import os
import sys
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


class TestResolveAuthUrl:
    def test_no_backend_falls_back_to_env_var(self, monkeypatch):
        monkeypatch.delenv("SECRETS_BACKEND", raising=False)
        monkeypatch.setenv("SALESFORCE_AUTH_URL", "force://id:secret:token@my.salesforce.com")
        from sfmon import orgs
        assert orgs.resolve_auth_url("default") == "force://id:secret:token@my.salesforce.com"

    def test_unsupported_backend_raises(self, monkeypatch):
        monkeypatch.setenv("SECRETS_BACKEND", "vault")
        from sfmon import orgs
        with pytest.raises(ValueError, match="Unsupported SECRETS_BACKEND 'vault'"):
            orgs.resolve_auth_url("default")

    def test_aws_backend_fetches_secret_by_env_var_name(self, monkeypatch):
        monkeypatch.setenv("SECRETS_BACKEND", "aws")
        monkeypatch.delenv("AWS_SECRETS_PREFIX", raising=False)
        monkeypatch.setenv("ORG_NAME", "prod")
        from sfmon import orgs
        with patch("sfmon.secrets_manager.get_secret_aws", return_value="force://a:b:c@x.salesforce.com") as mock_get:
            result = orgs.resolve_auth_url("prod")

        assert result == "force://a:b:c@x.salesforce.com"
        mock_get.assert_called_once_with("SALESFORCE_AUTH_URL")

    def test_aws_backend_honors_secrets_prefix(self, tmp_path, monkeypatch):
        cfg = {"orgs": ["prod"]}
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps(cfg))
        monkeypatch.setenv("CONFIG_FILE_PATH", str(cfg_file))
        monkeypatch.setenv("SECRETS_BACKEND", "aws")
        monkeypatch.setenv("AWS_SECRETS_PREFIX", "sfmon/")
        from sfmon import config, orgs
        config.load_config(force_reload=True)
        with patch("sfmon.secrets_manager.get_secret_aws", return_value="force://a:b:c@x.salesforce.com") as mock_get:
            orgs.resolve_auth_url("prod")

        mock_get.assert_called_once_with("sfmon/SALESFORCE_AUTH_URL_PROD")

    def test_aws_backend_missing_boto3_raises_clear_error(self, monkeypatch):
        monkeypatch.setenv("SECRETS_BACKEND", "aws")
        from sfmon import orgs
        with patch.dict(sys.modules, {"sfmon.secrets_manager": None}):
            with pytest.raises(RuntimeError, match="requires the boto3 package"):
                orgs.resolve_auth_url("default")

    def test_build_connections_skips_org_on_unsupported_backend(self, tmp_path, monkeypatch):
        cfg = {"orgs": ["prod"]}
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps(cfg))
        monkeypatch.setenv("CONFIG_FILE_PATH", str(cfg_file))
        monkeypatch.setenv("SECRETS_BACKEND", "azure")
        from sfmon import config, orgs
        config.load_config(force_reload=True)

        connections = orgs.build_connections()

        assert connections == {}
