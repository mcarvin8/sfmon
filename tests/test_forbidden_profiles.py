"""Unit tests for audit/forbidden_profiles.py"""

import os
import pytest
from unittest.mock import MagicMock, patch


class TestGetForbiddenProfiles:
    def test_returns_empty_list_when_unset(self):
        with patch.dict(os.environ, {"FORBIDDEN_PROD_PROFILES": ""}):
            # reload to pick up env var at module level
            import importlib
            import audit.forbidden_profiles as fp
            importlib.reload(fp)
            result = fp._get_forbidden_profiles()
        assert result == []

    def test_parses_comma_separated_values(self):
        with patch.dict(os.environ, {"FORBIDDEN_PROD_PROFILES": "AdminProfile, DevProfile"}):
            import importlib
            import audit.forbidden_profiles as fp
            result = fp._get_forbidden_profiles()
        assert result == ["AdminProfile", "DevProfile"]


class TestMonitorForbiddenProfileAssignments:
    def test_no_configured_profiles_sets_not_configured_label(self, mock_sf):
        from audit.forbidden_profiles import monitor_forbidden_profile_assignments
        mock_gauge = MagicMock()
        with patch("audit.forbidden_profiles.FORBIDDEN_PROD_PROFILES", []), \
             patch("audit.forbidden_profiles.forbidden_profile_users_gauge", mock_gauge):
            monitor_forbidden_profile_assignments(mock_sf)
        mock_gauge.labels.assert_called_once_with(
            user_id="none", user_name="Not Configured",
            username="none", profile_name="none",
        )
        mock_gauge.labels().set.assert_called_once_with(0)

    def test_no_violations_sets_no_violations_label(self, mock_sf):
        from audit.forbidden_profiles import monitor_forbidden_profile_assignments
        mock_gauge = MagicMock()
        with patch("audit.forbidden_profiles.FORBIDDEN_PROD_PROFILES", ["AdminProfile"]), \
             patch("audit.forbidden_profiles.query_records_all", return_value=[]), \
             patch("audit.forbidden_profiles.forbidden_profile_users_gauge", mock_gauge):
            monitor_forbidden_profile_assignments(mock_sf)
        mock_gauge.labels.assert_called_once_with(
            user_id="none", user_name="No Violations",
            username="none", profile_name="none",
        )

    def test_violation_sets_user_label(self, mock_sf):
        from audit.forbidden_profiles import monitor_forbidden_profile_assignments
        user = {
            "Id": "u01", "Name": "Bad Admin", "Username": "bad@example.com",
            "Profile": {"Name": "AdminProfile"},
        }
        mock_gauge = MagicMock()
        with patch("audit.forbidden_profiles.FORBIDDEN_PROD_PROFILES", ["AdminProfile"]), \
             patch("audit.forbidden_profiles.query_records_all", return_value=[user]), \
             patch("audit.forbidden_profiles.forbidden_profile_users_gauge", mock_gauge):
            monitor_forbidden_profile_assignments(mock_sf)
        mock_gauge.labels.assert_called_once_with(
            user_id="u01", user_name="Bad Admin",
            username="bad@example.com", profile_name="AdminProfile",
        )
        mock_gauge.labels().set.assert_called_once_with(1)

    def test_handles_exception(self, mock_sf):
        from audit.forbidden_profiles import monitor_forbidden_profile_assignments
        with patch("audit.forbidden_profiles.FORBIDDEN_PROD_PROFILES", ["AdminProfile"]), \
             patch("audit.forbidden_profiles.query_records_all", side_effect=RuntimeError("fail")), \
             patch("audit.forbidden_profiles.forbidden_profile_users_gauge"):
            monitor_forbidden_profile_assignments(mock_sf)  # Should not raise
