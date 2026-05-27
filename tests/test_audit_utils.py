"""Unit tests for audit/utils.py – Salesforce calls are mocked."""

import pytest
from unittest.mock import patch, MagicMock


class TestGetUserName:
    def test_returns_name_when_found(self, mock_sf):
        from audit.utils import get_user_name
        with patch("audit.utils.query_records_all", return_value=[{"Name": "John Doe"}]):
            result = get_user_name(mock_sf, "001000000000001AAA")
        assert result == "John Doe"

    def test_returns_unknown_when_not_found(self, mock_sf):
        from audit.utils import get_user_name
        with patch("audit.utils.query_records_all", return_value=[]):
            result = get_user_name(mock_sf, "001000000000001AAA")
        assert result == "Unknown User"

    def test_returns_unknown_for_none_id(self, mock_sf):
        from audit.utils import get_user_name
        result = get_user_name(mock_sf, None)
        assert result == "Unknown User"

    def test_returns_unknown_for_short_id(self, mock_sf):
        from audit.utils import get_user_name
        result = get_user_name(mock_sf, "short")
        assert result == "Unknown User"

    def test_returns_unknown_on_exception(self, mock_sf):
        from audit.utils import get_user_name
        with patch("audit.utils.query_records_all", side_effect=RuntimeError("db error")):
            result = get_user_name(mock_sf, "001000000000001AAA")
        assert result == "Unknown User"

    def test_valid_15_char_id(self, mock_sf):
        from audit.utils import get_user_name
        with patch("audit.utils.query_records_all", return_value=[{"Name": "Jane"}]):
            result = get_user_name(mock_sf, "001000000000001")
        assert result == "Jane"


class TestCategorizeUserGroup:
    def test_integration_user_categorized(self, monkeypatch):
        monkeypatch.setenv("INTEGRATION_USER_NAMES", "Bot User,Service Account")
        import importlib
        import audit.utils
        importlib.reload(audit.utils)
        from audit.utils import categorize_user_group
        assert categorize_user_group("Bot User") == "Integration User"

    def test_other_user_categorized(self, monkeypatch):
        monkeypatch.setenv("INTEGRATION_USER_NAMES", "Bot User")
        import importlib
        import audit.utils
        importlib.reload(audit.utils)
        from audit.utils import categorize_user_group
        assert categorize_user_group("Regular Human") == "Other"

    def test_empty_integration_users_all_other(self, monkeypatch):
        monkeypatch.delenv("INTEGRATION_USER_NAMES", raising=False)
        import importlib
        import audit.utils
        importlib.reload(audit.utils)
        from audit.utils import categorize_user_group
        assert categorize_user_group("Anyone") == "Other"

    def test_multiple_integration_users(self, monkeypatch):
        monkeypatch.setenv("INTEGRATION_USER_NAMES", "Bot1, Bot2 , Bot3")
        import importlib
        import audit.utils
        importlib.reload(audit.utils)
        from audit.utils import categorize_user_group
        assert categorize_user_group("Bot2") == "Integration User"
        assert categorize_user_group("Bot1") == "Integration User"
        assert categorize_user_group("Bot4") == "Other"
