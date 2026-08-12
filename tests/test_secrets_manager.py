"""Unit tests for secrets_manager.py – boto3 client is mocked, no live AWS call."""

import pytest
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError


@pytest.fixture(autouse=True)
def reset_client_cache():
    """Reset the module-level cached boto3 client between tests."""
    from sfmon import secrets_manager
    secrets_manager._client = None
    yield
    secrets_manager._client = None


class TestGetSecretAws:
    def test_returns_secret_string(self):
        from sfmon import secrets_manager
        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {
            "SecretString": "force://id:secret:token@my.salesforce.com"
        }
        with patch("sfmon.secrets_manager.boto3.client", return_value=mock_client) as mock_boto_client:
            result = secrets_manager.get_secret_aws("SALESFORCE_AUTH_URL_PROD")

        assert result == "force://id:secret:token@my.salesforce.com"
        mock_client.get_secret_value.assert_called_once_with(SecretId="SALESFORCE_AUTH_URL_PROD")
        mock_boto_client.assert_called_once_with("secretsmanager")

    def test_reuses_cached_client_across_calls(self):
        from sfmon import secrets_manager
        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {"SecretString": "force://a:b:c@x.salesforce.com"}
        with patch("sfmon.secrets_manager.boto3.client", return_value=mock_client) as mock_boto_client:
            secrets_manager.get_secret_aws("SECRET_ONE")
            secrets_manager.get_secret_aws("SECRET_TWO")

        mock_boto_client.assert_called_once()
        assert mock_client.get_secret_value.call_count == 2

    def test_raises_runtime_error_on_client_error(self):
        from sfmon import secrets_manager
        mock_client = MagicMock()
        mock_client.get_secret_value.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Secrets Manager can't find the specified secret."}},
            "GetSecretValue",
        )
        with patch("sfmon.secrets_manager.boto3.client", return_value=mock_client):
            with pytest.raises(RuntimeError, match="Failed to fetch secret"):
                secrets_manager.get_secret_aws("MISSING_SECRET")

    def test_raises_runtime_error_on_empty_secret_string(self):
        from sfmon import secrets_manager
        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {"SecretBinary": b"not-supported"}
        with patch("sfmon.secrets_manager.boto3.client", return_value=mock_client):
            with pytest.raises(RuntimeError, match="no SecretString value"):
                secrets_manager.get_secret_aws("BINARY_SECRET")
