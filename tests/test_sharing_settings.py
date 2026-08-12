"""Unit tests for audit/sharing_settings.py"""

import pytest
from unittest.mock import MagicMock, patch


class TestMonitorOrgWideSharingSettings:
    def _make_change(self, section="Sharing Defaults", **overrides):
        base = {
            "Section": section,
            "Action": "Changed",
            "CreatedDate": "2024-01-15T10:00:00.000Z",
            "CreatedById": "u01",
            "Display": "Account: Private -> Public Read Only",
        }
        base.update(overrides)
        return base

    def test_sets_gauge_for_sharing_change(self, mock_sf):
        from sfmon.audit.sharing_settings import monitor_org_wide_sharing_settings
        changes = [self._make_change()]
        mock_gauge = MagicMock()
        with patch("sfmon.audit.sharing_settings.query_setup_audit_trail", return_value=changes), \
             patch("sfmon.audit.sharing_settings.get_user_name", return_value="Admin"), \
             patch("sfmon.audit.sharing_settings.categorize_user_group", return_value="Integration"), \
             patch("sfmon.audit.sharing_settings.org_wide_sharing__setting_changes", mock_gauge):
            monitor_org_wide_sharing_settings(mock_sf)
        mock_gauge.labels.assert_called_once()
        mock_gauge.labels().set.assert_called_once_with(1)

    def test_ignores_non_sharing_sections(self, mock_sf):
        from sfmon.audit.sharing_settings import monitor_org_wide_sharing_settings
        changes = [self._make_change(section="Manage Users")]
        mock_gauge = MagicMock()
        with patch("sfmon.audit.sharing_settings.query_setup_audit_trail", return_value=changes), \
             patch("sfmon.audit.sharing_settings.org_wide_sharing__setting_changes", mock_gauge):
            monitor_org_wide_sharing_settings(mock_sf)
        # no_changes branch → labels called once with placeholder action
        labels_kwargs = mock_gauge.labels.call_args.kwargs
        assert labels_kwargs["action"] == "none"

    def test_no_changes_sets_placeholder(self, mock_sf):
        from sfmon.audit.sharing_settings import monitor_org_wide_sharing_settings
        mock_gauge = MagicMock()
        with patch("sfmon.audit.sharing_settings.query_setup_audit_trail", return_value=[]), \
             patch("sfmon.audit.sharing_settings.org_wide_sharing__setting_changes", mock_gauge):
            monitor_org_wide_sharing_settings(mock_sf)
        mock_gauge.labels.assert_called_once_with(
            user_group="Other",
            action="none",
        )
        mock_gauge.labels().set.assert_called_once_with(0)

    def test_handles_exception(self, mock_sf):
        from sfmon.audit.sharing_settings import monitor_org_wide_sharing_settings
        with patch("sfmon.audit.sharing_settings.query_setup_audit_trail", side_effect=RuntimeError("fail")), \
             patch("sfmon.audit.sharing_settings.org_wide_sharing__setting_changes"):
            monitor_org_wide_sharing_settings(mock_sf)  # Should not raise
