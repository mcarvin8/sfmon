"""Unit tests for connection_sf.py – subprocess and shutil are mocked."""

import json
import pytest
from unittest.mock import MagicMock, patch


class TestGetSfCommand:
    def test_finds_sf_cmd_on_windows(self):
        import connection_sf
        with patch("sys.platform", "win32"), \
             patch("shutil.which", return_value="C:\\path\\sf.cmd"):
            result = connection_sf._get_sf_command()
        assert result == "C:\\path\\sf.cmd"

    def test_finds_sf_on_unix(self):
        with patch("shutil.which", return_value="/usr/local/bin/sf") as mock_which:
            import connection_sf
            result = connection_sf._get_sf_command()
            mock_which.assert_called_with("sf")
            assert result == "/usr/local/bin/sf"

    def test_raises_when_sf_not_found(self):
        with patch("shutil.which", return_value=None):
            import connection_sf
            with pytest.raises(FileNotFoundError, match="Salesforce CLI"):
                connection_sf._get_sf_command()


class TestGetSalesforceConnectionUrl:
    def test_raises_on_empty_url(self):
        import connection_sf
        with pytest.raises(ValueError, match="SFDX authentication URL"):
            connection_sf.get_salesforce_connection_url("")

    def test_raises_on_none_url(self):
        import connection_sf
        with pytest.raises(ValueError):
            connection_sf.get_salesforce_connection_url(None)

    def test_successful_connection(self):
        sf_display_output = json.dumps({
            "result": {
                "accessToken": "test_token_abc123",
                "instanceUrl": "https://myorg.my.salesforce.com",
                "apiVersion": "58.0",
            }
        })

        mock_run = MagicMock()
        mock_run.stdout = sf_display_output.encode("utf-8")
        mock_run.returncode = 0

        mock_sf_instance = MagicMock()

        with patch("shutil.which", return_value="/usr/local/bin/sf"), \
             patch("subprocess.run", return_value=mock_run), \
             patch("connection_sf.Salesforce", return_value=mock_sf_instance) as mock_sf_cls:

            import connection_sf
            result = connection_sf.get_salesforce_connection_url("force://token@instance")

            assert result is mock_sf_instance
            mock_sf_cls.assert_called_once_with(
                instance_url="https://myorg.my.salesforce.com",
                session_id="test_token_abc123",
                domain="login",
                version="58.0",
            )

    def test_sandbox_url_uses_test_domain(self):
        sf_display_output = json.dumps({
            "result": {
                "accessToken": "sandbox_token",
                "instanceUrl": "https://myorg--sandbox.sandbox.my.salesforce.com",
                "apiVersion": "59.0",
            }
        })

        mock_run = MagicMock()
        mock_run.stdout = sf_display_output.encode("utf-8")

        with patch("shutil.which", return_value="/usr/local/bin/sf"), \
             patch("subprocess.run", return_value=mock_run), \
             patch("connection_sf.Salesforce") as mock_sf_cls:

            mock_sf_cls.return_value = MagicMock()
            import connection_sf
            connection_sf.get_salesforce_connection_url("force://token@sandbox")

            _, kwargs = mock_sf_cls.call_args
            assert kwargs["domain"] == "test"

    def test_subprocess_error_propagates(self):
        import subprocess
        with patch("shutil.which", return_value="/usr/local/bin/sf"), \
             patch("subprocess.run") as mock_run:

            err = subprocess.CalledProcessError(1, "sf")
            err.stderr = b"Auth failed"
            err.stdout = b""
            mock_run.side_effect = err

            import connection_sf
            with pytest.raises(subprocess.CalledProcessError):
                connection_sf.get_salesforce_connection_url("force://bad_token@instance")

    def test_windows_temp_file_oserror_on_cleanup(self):
        sf_display_output = json.dumps({
            "result": {
                "accessToken": "win_token",
                "instanceUrl": "https://myorg.my.salesforce.com",
                "apiVersion": "58.0",
            }
        })
        mock_run = MagicMock()
        mock_run.stdout = sf_display_output.encode("utf-8")

        with patch("sys.platform", "win32"), \
             patch("shutil.which", return_value="C:\\path\\sf.cmd"), \
             patch("subprocess.run", return_value=mock_run), \
             patch("os.unlink", side_effect=OSError("permission denied")), \
             patch("connection_sf.Salesforce", return_value=MagicMock()):
            import connection_sf
            result = connection_sf.get_salesforce_connection_url("force://token@instance")
        assert result is not None

    def test_windows_uses_temp_file(self):
        sf_display_output = json.dumps({
            "result": {
                "accessToken": "win_token",
                "instanceUrl": "https://myorg.my.salesforce.com",
                "apiVersion": "58.0",
            }
        })
        mock_run = MagicMock()
        mock_run.stdout = sf_display_output.encode("utf-8")

        with patch("sys.platform", "win32"), \
             patch("shutil.which", return_value="C:\\path\\sf.cmd"), \
             patch("subprocess.run", return_value=mock_run), \
             patch("connection_sf.Salesforce", return_value=MagicMock()):
            import connection_sf
            result = connection_sf.get_salesforce_connection_url("force://token@instance")
        assert result is not None

    def test_missing_key_propagates(self):
        sf_display_output = json.dumps({"result": {}})
        mock_run = MagicMock()
        mock_run.stdout = sf_display_output.encode("utf-8")

        with patch("shutil.which", return_value="/usr/local/bin/sf"), \
             patch("subprocess.run", return_value=mock_run):

            import connection_sf
            with pytest.raises(KeyError):
                connection_sf.get_salesforce_connection_url("force://token@instance")
