"""Unit tests for audit/__init__.py (run_hourly_audit, run_daily_audit)"""

import pytest
from unittest.mock import MagicMock, patch


class TestRunHourlyAudit:
    def test_calls_all_hourly_functions(self, mock_sf):
        from audit import run_hourly_audit
        with patch("audit.audit.hourly_observe_user_querying_large_records") as m_large, \
             patch("audit.audit.monitor_forbidden_profile_assignments") as m_fp:
            run_hourly_audit(mock_sf)
        m_large.assert_called_once_with(mock_sf)
        m_fp.assert_called_once_with(mock_sf)


class TestRunDailyAudit:
    def test_calls_all_daily_functions(self, mock_sf):
        from audit import run_daily_audit
        with patch("audit.audit.expose_suspicious_records") as m_sus, \
             patch("audit.audit.monitor_org_wide_sharing_settings") as m_share, \
             patch("audit.audit.get_deployment_status") as m_dep, \
             patch("audit.audit.monitor_login_events") as m_login, \
             patch("audit.audit.geolocation") as m_geo:
            run_daily_audit(mock_sf)
        m_sus.assert_called_once_with(mock_sf)
        m_share.assert_called_once_with(mock_sf)
        m_dep.assert_called_once_with(mock_sf)
        m_login.assert_called_once_with(mock_sf)
        m_geo.assert_called_once_with(mock_sf, chunk_size=100)
