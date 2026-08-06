"""Unit tests for connection_sf.py – requests is mocked, no sf CLI involved."""

import pytest
from unittest.mock import MagicMock, patch

import requests

VERSIONS_RESPONSE = [
    {"version": "58.0", "label": "Winter '24", "url": "/services/data/v58.0"},
    {"version": "60.0", "label": "Summer '24", "url": "/services/data/v60.0"},
    {"version": "59.0", "label": "Spring '24", "url": "/services/data/v59.0"},
]


def _mock_versions_response():
    mock_response = MagicMock()
    mock_response.json.return_value = VERSIONS_RESPONSE
    mock_response.raise_for_status.return_value = None
    return mock_response


class TestGetSalesforceConnectionUrl:
    def test_raises_on_empty_url(self):
        import connection_sf
        with pytest.raises(ValueError, match="SFDX authentication URL"):
            connection_sf.get_salesforce_connection_url("")

    def test_raises_on_none_url(self):
        import connection_sf
        with pytest.raises(ValueError):
            connection_sf.get_salesforce_connection_url(None)

    def test_raises_on_malformed_url(self):
        import connection_sf
        with pytest.raises(ValueError, match="Invalid SFDX auth URL format"):
            connection_sf.get_salesforce_connection_url("not-a-valid-sfdx-url")

    def test_successful_connection(self):
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "access_token": "test_token_abc123",
            "instance_url": "https://myorg.my.salesforce.com",
        }

        mock_sf_instance = MagicMock()

        with patch("requests.post", return_value=mock_token_response) as mock_post, \
             patch("requests.get", return_value=_mock_versions_response()), \
             patch("connection_sf.Salesforce", return_value=mock_sf_instance) as mock_sf_cls:

            import connection_sf
            result = connection_sf.get_salesforce_connection_url(
                "force://clientid:clientsecret:refreshtoken@https://login.salesforce.com"
            )

            assert result is mock_sf_instance
            mock_post.assert_called_once_with(
                "https://login.salesforce.com/services/oauth2/token",
                data={
                    "grant_type": "refresh_token",
                    "client_id": "clientid",
                    "refresh_token": "refreshtoken",
                    "client_secret": "clientsecret",
                },
                timeout=30,
            )
            mock_sf_cls.assert_called_once_with(
                instance_url="https://myorg.my.salesforce.com",
                session_id="test_token_abc123",
                domain="login",
                version="60.0",
            )

    def test_platform_cli_url_with_empty_secret(self):
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "access_token": "test_token_abc123",
            "instance_url": "https://myorg.my.salesforce.com",
        }

        with patch("requests.post", return_value=mock_token_response) as mock_post, \
             patch("requests.get", return_value=_mock_versions_response()), \
             patch("connection_sf.Salesforce", return_value=MagicMock()):

            import connection_sf
            connection_sf.get_salesforce_connection_url(
                "force://PlatformCLI::refreshtoken@https://login.salesforce.com"
            )

            _, kwargs = mock_post.call_args
            assert "client_secret" not in kwargs["data"]
            assert kwargs["data"]["client_id"] == "PlatformCLI"

    def test_sandbox_url_uses_test_domain(self):
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "access_token": "sandbox_token",
            "instance_url": "https://myorg--sandbox.sandbox.my.salesforce.com",
        }

        with patch("requests.post", return_value=mock_token_response), \
             patch("requests.get", return_value=_mock_versions_response()), \
             patch("connection_sf.Salesforce") as mock_sf_cls:

            mock_sf_cls.return_value = MagicMock()
            import connection_sf
            connection_sf.get_salesforce_connection_url(
                "force://clientid:clientsecret:refreshtoken@https://test.salesforce.com"
            )

            _, kwargs = mock_sf_cls.call_args
            assert kwargs["domain"] == "test"

    def test_http_error_propagates(self):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("Auth failed")
        mock_response.text = "Auth failed"

        with patch("requests.post", return_value=mock_response):
            import connection_sf
            with pytest.raises(requests.HTTPError):
                connection_sf.get_salesforce_connection_url(
                    "force://clientid:clientsecret:badtoken@https://login.salesforce.com"
                )

    def test_missing_key_propagates(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {}

        with patch("requests.post", return_value=mock_response):
            import connection_sf
            with pytest.raises(KeyError):
                connection_sf.get_salesforce_connection_url(
                    "force://clientid:clientsecret:refreshtoken@https://login.salesforce.com"
                )


class TestGetLatestApiVersion:
    def test_returns_highest_version(self):
        import connection_sf
        with patch("requests.get", return_value=_mock_versions_response()):
            result = connection_sf._get_latest_api_version(
                "https://myorg.my.salesforce.com", "token"
            )
        assert result == "60.0"

    def test_falls_back_on_request_exception(self):
        import connection_sf
        with patch("requests.get", side_effect=requests.ConnectionError("network down")):
            result = connection_sf._get_latest_api_version(
                "https://myorg.my.salesforce.com", "token"
            )
        assert result == connection_sf.DEFAULT_API_VERSION

    def test_falls_back_on_malformed_json(self):
        import connection_sf
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = "not-a-list"
        with patch("requests.get", return_value=mock_response):
            result = connection_sf._get_latest_api_version(
                "https://myorg.my.salesforce.com", "token"
            )
        assert result == connection_sf.DEFAULT_API_VERSION

    def test_falls_back_on_missing_version_key(self):
        import connection_sf
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = [{"label": "no version key here"}]
        with patch("requests.get", return_value=mock_response):
            result = connection_sf._get_latest_api_version(
                "https://myorg.my.salesforce.com", "token"
            )
        assert result == connection_sf.DEFAULT_API_VERSION
