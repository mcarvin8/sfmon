"""Unit tests for tech_debt/permissions.py"""

import json
import os
import pytest
from unittest.mock import MagicMock, patch


class TestUnassignedPermissionSets:
    def test_sets_gauge_per_record(self, mock_sf):
        from tech_debt.permissions import unassigned_permission_sets
        records = [
            {"Id": "ps1", "Name": "EmptyPS1"},
            {"Id": "ps2", "Name": "EmptyPS2"},
        ]
        mock_gauge = MagicMock()
        with patch("tech_debt.permissions.query_records_all", return_value=records), \
             patch("tech_debt.permissions.unused_permissionsets", mock_gauge):
            unassigned_permission_sets(mock_sf)
        assert mock_gauge.labels.call_count == 2
        mock_gauge.clear.assert_called_once()

    def test_empty_results(self, mock_sf):
        from tech_debt.permissions import unassigned_permission_sets
        mock_gauge = MagicMock()
        with patch("tech_debt.permissions.query_records_all", return_value=[]), \
             patch("tech_debt.permissions.unused_permissionsets", mock_gauge):
            unassigned_permission_sets(mock_sf)
        mock_gauge.labels.assert_not_called()

    def test_handles_exception(self, mock_sf):
        from tech_debt.permissions import unassigned_permission_sets
        with patch("tech_debt.permissions.query_records_all", side_effect=RuntimeError("fail")):
            unassigned_permission_sets(mock_sf)  # Should not raise


class TestPermSetsLimitedUsers:
    def test_sets_gauge_per_record(self, mock_sf):
        from tech_debt.permissions import perm_sets_limited_users
        records = [{"Id": "ps1", "Name": "LimitedPS", "expr0": "3"}]
        mock_gauge = MagicMock()
        with patch("tech_debt.permissions.query_records_all", return_value=records), \
             patch("tech_debt.permissions.limited_permissionsets", mock_gauge):
            perm_sets_limited_users(mock_sf)
        mock_gauge.labels.assert_called_once_with(name="LimitedPS", id="ps1")
        mock_gauge.labels().set.assert_called_once_with(3)

    def test_handles_exception(self, mock_sf):
        from tech_debt.permissions import perm_sets_limited_users
        with patch("tech_debt.permissions.query_records_all", side_effect=RuntimeError("fail")):
            perm_sets_limited_users(mock_sf)  # Should not raise


class TestProfileAssignmentUnder5:
    def test_sets_gauge_per_record(self, mock_sf):
        from tech_debt.permissions import profile_assignment_under5
        records = [{"ProfileId": "p01", "Name": "Standard User", "userCount": "2"}]
        mock_gauge = MagicMock()
        with patch("tech_debt.permissions.query_records_all", return_value=records), \
             patch("tech_debt.permissions.five_or_less_profile_assignees", mock_gauge):
            profile_assignment_under5(mock_sf)
        mock_gauge.labels.assert_called_once()
        mock_gauge.labels().set.assert_called_once_with(2)

    def test_handles_exception(self, mock_sf):
        from tech_debt.permissions import profile_assignment_under5
        with patch("tech_debt.permissions.query_records_all", side_effect=RuntimeError("fail")):
            profile_assignment_under5(mock_sf)  # Should not raise


class TestProfileNoActiveUsers:
    def test_sets_gauge_per_record(self, mock_sf):
        from tech_debt.permissions import profile_no_active_users
        records = [{"Id": "p01", "Name": "Empty Profile"}]
        mock_gauge = MagicMock()
        with patch("tech_debt.permissions.query_records_all", return_value=records), \
             patch("tech_debt.permissions.unassigned_profiles", mock_gauge):
            profile_no_active_users(mock_sf)
        mock_gauge.labels.assert_called_once_with(profileId="p01", profileName="Empty Profile")
        mock_gauge.labels().set.assert_called_once_with(0)

    def test_handles_exception(self, mock_sf):
        from tech_debt.permissions import profile_no_active_users
        with patch("tech_debt.permissions.query_records_all", side_effect=RuntimeError("fail")):
            profile_no_active_users(mock_sf)  # Should not raise


class TestMonitorMinimalPermSets:
    def _make_report(self, tmp_path, minimal_sets=None, total=10):
        data = {
            "scan_date": "2024-01-01T00:00:00Z",
            "total_permission_sets": total,
            "threshold": 5,
            "minimal_permission_sets": minimal_sets or [],
        }
        report_path = tmp_path / "minimal-perm-sets.json"
        report_path.write_text(json.dumps(data))
        return report_path

    def test_no_report_file_exits_quietly(self, mock_sf, tmp_path):
        from tech_debt.permissions import monitor_minimal_perm_sets
        # Point script_dir to tmp_path where there's no file
        with patch("tech_debt.permissions.os.path.dirname", return_value=str(tmp_path)):
            monitor_minimal_perm_sets(mock_sf)  # Should not raise

    def test_sets_gauge_per_perm_set(self, mock_sf, tmp_path):
        from tech_debt.permissions import monitor_minimal_perm_sets
        report = self._make_report(tmp_path, minimal_sets=[
            {"name": "MinPS1", "file_path": "MinPS1.permissionset", "permission_count": 2},
            {"name": "MinPS2", "file_path": "MinPS2.permissionset", "permission_count": 4},
        ], total=20)
        mock_gauge = MagicMock()
        mock_pct_gauge = MagicMock()
        with patch("tech_debt.permissions.os.path.dirname", return_value=str(tmp_path)), \
             patch("tech_debt.permissions.minimal_permission_sets_gauge", mock_gauge), \
             patch("tech_debt.permissions.minimal_permission_sets_percentage_gauge", mock_pct_gauge):
            monitor_minimal_perm_sets(mock_sf)
        assert mock_gauge.labels.call_count == 2
        mock_pct_gauge.set.assert_called_once()

    def test_percentage_calculated_correctly(self, mock_sf, tmp_path):
        from tech_debt.permissions import monitor_minimal_perm_sets
        report = self._make_report(tmp_path, minimal_sets=[
            {"name": "PS1", "file_path": "p.xml", "permission_count": 1},
        ], total=10)
        captured = {}
        mock_gauge = MagicMock()
        mock_pct_gauge = MagicMock()
        mock_pct_gauge.set.side_effect = lambda v: captured.update({"pct": v})
        with patch("tech_debt.permissions.os.path.dirname", return_value=str(tmp_path)), \
             patch("tech_debt.permissions.minimal_permission_sets_gauge", mock_gauge), \
             patch("tech_debt.permissions.minimal_permission_sets_percentage_gauge", mock_pct_gauge):
            monitor_minimal_perm_sets(mock_sf)
        assert captured["pct"] == pytest.approx(10.0)

    def test_handles_invalid_json(self, mock_sf, tmp_path):
        from tech_debt.permissions import monitor_minimal_perm_sets
        (tmp_path / "minimal-perm-sets.json").write_text("NOT JSON")
        with patch("tech_debt.permissions.os.path.dirname", return_value=str(tmp_path)):
            monitor_minimal_perm_sets(mock_sf)  # Should not raise
