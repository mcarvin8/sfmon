"""Unit tests for tech_debt/users.py – Salesforce calls are mocked."""

import pytest
from unittest.mock import MagicMock, patch


class TestDormantSalesforceUsers:
    def _make_user_record(self, **overrides):
        base = {
            "Id": "005000000000001AAA",
            "Name": "John Doe",
            "Username": "john@example.com",
            "Email": "john@example.com",
            "IsActive": True,
            "CreatedDate": "2020-01-01T00:00:00.000Z",
            "LastLoginDate": "2021-01-01T00:00:00.000Z",
            "Profile": {"Name": "Standard User"},
        }
        base.update(overrides)
        return base

    def test_sets_gauge_for_each_user(self, mock_sf):
        from tech_debt.users import dormant_salesforce_users
        records = [self._make_user_record(), self._make_user_record(Id="005000000000002AAA", Name="Jane")]
        mock_gauge = MagicMock()
        with patch("tech_debt.users.query_records_all", return_value=records), \
             patch("tech_debt.users.dormant_salesforce_users_gauge", mock_gauge):
            dormant_salesforce_users(mock_sf)
        assert mock_gauge.labels.call_count == 2
        mock_gauge.labels().set.assert_called_with(1)

    def test_null_last_login_becomes_never(self, mock_sf):
        from tech_debt.users import dormant_salesforce_users
        record = self._make_user_record(LastLoginDate=None)
        captured = {}
        mock_gauge = MagicMock()
        mock_gauge.labels.side_effect = lambda **kw: captured.update(kw) or MagicMock()

        with patch("tech_debt.users.query_records_all", return_value=[record]), \
             patch("tech_debt.users.dormant_salesforce_users_gauge", mock_gauge):
            dormant_salesforce_users(mock_sf)

        assert captured.get("last_login_date") == "Never"

    def test_empty_results_clears_gauge(self, mock_sf):
        from tech_debt.users import dormant_salesforce_users
        mock_gauge = MagicMock()
        with patch("tech_debt.users.query_records_all", return_value=[]), \
             patch("tech_debt.users.dormant_salesforce_users_gauge", mock_gauge):
            dormant_salesforce_users(mock_sf)
        mock_gauge.clear.assert_called_once()
        mock_gauge.labels.assert_not_called()

    def test_handles_exception_gracefully(self, mock_sf):
        from tech_debt.users import dormant_salesforce_users
        mock_gauge = MagicMock()
        with patch("tech_debt.users.query_records_all", side_effect=RuntimeError("db error")), \
             patch("tech_debt.users.dormant_salesforce_users_gauge", mock_gauge):
            dormant_salesforce_users(mock_sf)  # Should not raise


class TestDormantPortalUsers:
    def _make_portal_record(self, **overrides):
        base = {
            "Id": "005000000000010AAA",
            "Name": "Portal User",
            "Username": "portal@example.com",
            "Email": "portal@example.com",
            "IsActive": True,
            "CreatedDate": "2019-06-01T00:00:00.000Z",
            "LastLoginDate": "2021-06-01T00:00:00.000Z",
            "Profile": {"Name": "Customer Community User"},
        }
        base.update(overrides)
        return base

    def test_sets_gauge_for_each_portal_user(self, mock_sf):
        from tech_debt.users import dormant_portal_users
        records = [self._make_portal_record()]
        mock_gauge = MagicMock()
        with patch("tech_debt.users.query_records_all", return_value=records), \
             patch("tech_debt.users.dormant_portal_users_gauge", mock_gauge):
            dormant_portal_users(mock_sf)
        mock_gauge.labels.assert_called_once()
        mock_gauge.labels().set.assert_called_once_with(1)

    def test_null_last_login_becomes_never(self, mock_sf):
        from tech_debt.users import dormant_portal_users
        record = self._make_portal_record(LastLoginDate=None)
        captured = {}
        mock_gauge = MagicMock()
        mock_gauge.labels.side_effect = lambda **kw: captured.update(kw) or MagicMock()

        with patch("tech_debt.users.query_records_all", return_value=[record]), \
             patch("tech_debt.users.dormant_portal_users_gauge", mock_gauge):
            dormant_portal_users(mock_sf)

        assert captured.get("last_login_date") == "Never"

    def test_handles_exception_gracefully(self, mock_sf):
        from tech_debt.users import dormant_portal_users
        mock_gauge = MagicMock()
        with patch("tech_debt.users.query_records_all", side_effect=Exception("fail")), \
             patch("tech_debt.users.dormant_portal_users_gauge", mock_gauge):
            dormant_portal_users(mock_sf)  # Should not raise
