"""Unit tests for tech_debt/dashboards.py"""

import pytest
from unittest.mock import MagicMock, patch


class TestDashboardsWithInactiveUsers:
    def _make_record(self, **overrides):
        base = {
            "Id": "dash01",
            "Title": "Sales Dashboard",
            "RunningUser": {"Name": "Inactive User", "IsActive": False},
            "CreatedDate": "2022-01-01T00:00:00.000Z",
            "LastReferencedDate": "2023-06-01T00:00:00.000Z",
        }
        base.update(overrides)
        return base

    def test_sets_gauge_per_dashboard(self, mock_sf):
        from tech_debt.dashboards import dashboards_with_inactive_users
        records = [self._make_record(), self._make_record(Id="dash02", Title="Ops Dashboard")]
        mock_gauge = MagicMock()
        with patch("tech_debt.dashboards.query_records_all", return_value=records), \
             patch("tech_debt.dashboards.dashboards_with_inactive_users_gauge", mock_gauge):
            dashboards_with_inactive_users(mock_sf)
        assert mock_gauge.labels.call_count == 2
        mock_gauge.clear.assert_called_once()

    def test_null_running_user_becomes_unknown(self, mock_sf):
        from tech_debt.dashboards import dashboards_with_inactive_users
        record = self._make_record(RunningUser=None)
        captured = {}
        mock_gauge = MagicMock()
        mock_gauge.labels.side_effect = lambda **kw: captured.update(kw) or MagicMock()
        with patch("tech_debt.dashboards.query_records_all", return_value=[record]), \
             patch("tech_debt.dashboards.dashboards_with_inactive_users_gauge", mock_gauge):
            dashboards_with_inactive_users(mock_sf)
        assert captured.get("running_user_name") == "Unknown"

    def test_null_last_referenced_date_becomes_never(self, mock_sf):
        from tech_debt.dashboards import dashboards_with_inactive_users
        record = self._make_record(LastReferencedDate=None)
        captured = {}
        mock_gauge = MagicMock()
        mock_gauge.labels.side_effect = lambda **kw: captured.update(kw) or MagicMock()
        with patch("tech_debt.dashboards.query_records_all", return_value=[record]), \
             patch("tech_debt.dashboards.dashboards_with_inactive_users_gauge", mock_gauge):
            dashboards_with_inactive_users(mock_sf)
        assert captured.get("last_referenced_date") == "Never"

    def test_empty_results(self, mock_sf):
        from tech_debt.dashboards import dashboards_with_inactive_users
        mock_gauge = MagicMock()
        with patch("tech_debt.dashboards.query_records_all", return_value=[]), \
             patch("tech_debt.dashboards.dashboards_with_inactive_users_gauge", mock_gauge):
            dashboards_with_inactive_users(mock_sf)
        mock_gauge.labels.assert_not_called()

    def test_handles_exception(self, mock_sf):
        from tech_debt.dashboards import dashboards_with_inactive_users
        with patch("tech_debt.dashboards.query_records_all", side_effect=RuntimeError("fail")):
            dashboards_with_inactive_users(mock_sf)  # Should not raise
