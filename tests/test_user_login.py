"""Unit tests for audit/user_login.py"""

import pytest
import requests
from unittest.mock import MagicMock, patch


class TestResetLoginGauges:
    def test_sets_all_gauges_to_zero(self):
        from audit.user_login import reset_login_gauges
        mock_success = MagicMock()
        mock_failure = MagicMock()
        mock_unique = MagicMock()
        with patch("audit.user_login.login_success_gauge", mock_success), \
             patch("audit.user_login.login_failure_gauge", mock_failure), \
             patch("audit.user_login.unique_login_attempts_gauge", mock_unique):
            reset_login_gauges()
        mock_success.set.assert_called_once_with(0)
        mock_failure.set.assert_called_once_with(0)
        mock_unique.set.assert_called_once_with(0)


class TestFetchLatestLoginLog:
    def _make_sf(self):
        sf = MagicMock()
        sf.base_url = "https://org.salesforce.com"
        sf.session_id = "TOKEN"
        return sf

    def test_returns_none_when_no_records(self):
        from audit.user_login import fetch_latest_login_log
        with patch("audit.user_login.query_records_all", return_value=[]):
            result = fetch_latest_login_log(self._make_sf())
        assert result is None

    def test_returns_log_text_on_success(self):
        from audit.user_login import fetch_latest_login_log
        sf = self._make_sf()
        records = [{"Id": "elf001"}]
        mock_resp = MagicMock()
        mock_resp.text = "LOGIN_STATUS,USER_ID\nLOGIN_NO_ERROR,u01"
        with patch("audit.user_login.query_records_all", return_value=records), \
             patch("audit.user_login.requests.get", return_value=mock_resp):
            result = fetch_latest_login_log(sf)
        assert result == mock_resp.text

    def test_returns_none_when_empty_response(self):
        from audit.user_login import fetch_latest_login_log
        sf = self._make_sf()
        records = [{"Id": "elf001"}]
        mock_resp = MagicMock()
        mock_resp.text = ""
        with patch("audit.user_login.query_records_all", return_value=records), \
             patch("audit.user_login.requests.get", return_value=mock_resp):
            result = fetch_latest_login_log(sf)
        assert result is None


class TestProcessLoginLog:
    def test_counts_successes_and_failures(self):
        from audit.user_login import process_login_log
        csv_text = "LOGIN_STATUS,USER_ID\nLOGIN_NO_ERROR,u01\nLOGIN_NO_ERROR,u02\nPASSWORD_LOCKOUT,u03\n"
        mock_success = MagicMock()
        mock_failure = MagicMock()
        mock_unique = MagicMock()
        with patch("audit.user_login.login_success_gauge", mock_success), \
             patch("audit.user_login.login_failure_gauge", mock_failure), \
             patch("audit.user_login.unique_login_attempts_gauge", mock_unique):
            process_login_log(csv_text)
        mock_success.set.assert_called_once_with(2)
        mock_failure.set.assert_called_once_with(1)
        mock_unique.set.assert_called_once_with(3)

    def test_sets_unique_user_count(self):
        from audit.user_login import process_login_log
        # Two rows with same USER_ID
        csv_text = "LOGIN_STATUS,USER_ID\nLOGIN_NO_ERROR,u01\nLOGIN_NO_ERROR,u01\n"
        mock_success = MagicMock()
        mock_failure = MagicMock()
        mock_unique = MagicMock()
        with patch("audit.user_login.login_success_gauge", mock_success), \
             patch("audit.user_login.login_failure_gauge", mock_failure), \
             patch("audit.user_login.unique_login_attempts_gauge", mock_unique):
            process_login_log(csv_text)
        mock_unique.set.assert_called_once_with(1)

    def test_handles_missing_user_id_column(self):
        from audit.user_login import process_login_log
        csv_text = "LOGIN_STATUS\nLOGIN_NO_ERROR\n"
        mock_success = MagicMock()
        mock_failure = MagicMock()
        mock_unique = MagicMock()
        with patch("audit.user_login.login_success_gauge", mock_success), \
             patch("audit.user_login.login_failure_gauge", mock_failure), \
             patch("audit.user_login.unique_login_attempts_gauge", mock_unique):
            process_login_log(csv_text)  # Should not raise
        mock_unique.set.assert_not_called()


class TestMonitorLoginEvents:
    def test_calls_process_when_log_data_present(self, mock_sf):
        from audit.user_login import monitor_login_events
        log_text = "LOGIN_STATUS,USER_ID\nLOGIN_NO_ERROR,u01\n"
        with patch("audit.user_login.reset_login_gauges") as m_reset, \
             patch("audit.user_login.fetch_latest_login_log", return_value=log_text) as m_fetch, \
             patch("audit.user_login.process_login_log") as m_process:
            monitor_login_events(mock_sf)
        m_reset.assert_called_once()
        m_fetch.assert_called_once_with(mock_sf)
        m_process.assert_called_once_with(log_text)

    def test_skips_process_when_no_log(self, mock_sf):
        from audit.user_login import monitor_login_events
        with patch("audit.user_login.reset_login_gauges"), \
             patch("audit.user_login.fetch_latest_login_log", return_value=None), \
             patch("audit.user_login.process_login_log") as m_process:
            monitor_login_events(mock_sf)
        m_process.assert_not_called()

    def test_handles_exception(self, mock_sf):
        from audit.user_login import monitor_login_events
        with patch("audit.user_login.reset_login_gauges"), \
             patch("audit.user_login.fetch_latest_login_log", side_effect=RuntimeError("fail")):
            monitor_login_events(mock_sf)  # Should not raise


class TestGeolocation:
    def _make_location(self, user_id="u01", has_geo=True):
        rec = {
            "UserId": user_id,
            "Status": "Success",
            "Browser": "Chrome",
        }
        if has_geo:
            rec["LoginGeo"] = {"Latitude": "37.77", "Longitude": "-122.41"}
        else:
            rec["LoginGeo"] = None
        return rec

    def test_sets_gauge_for_location_with_geo(self, mock_sf):
        from audit.user_login import geolocation
        locations = [self._make_location()]
        mock_gauge = MagicMock()
        with patch("audit.user_login.query_records_all", side_effect=[locations, [{"Id": "u01", "Name": "Alice"}]]), \
             patch("audit.user_login.geolocation_gauge", mock_gauge):
            geolocation(mock_sf, chunk_size=100)
        mock_gauge.labels.assert_called_once()
        mock_gauge.labels().set.assert_called_once_with(1)

    def test_skips_record_without_geo(self, mock_sf):
        from audit.user_login import geolocation
        locations = [self._make_location(has_geo=False)]
        mock_gauge = MagicMock()
        with patch("audit.user_login.query_records_all", side_effect=[locations, [{"Id": "u01", "Name": "Alice"}]]), \
             patch("audit.user_login.geolocation_gauge", mock_gauge):
            geolocation(mock_sf, chunk_size=100)
        mock_gauge.labels.assert_not_called()

    def test_handles_empty_results(self, mock_sf):
        from audit.user_login import geolocation
        mock_gauge = MagicMock()
        with patch("audit.user_login.query_records_all", return_value=[]), \
             patch("audit.user_login.geolocation_gauge", mock_gauge):
            geolocation(mock_sf, chunk_size=100)
        mock_gauge.labels.assert_not_called()

    def test_handles_exception(self, mock_sf):
        from audit.user_login import geolocation
        with patch("audit.user_login.query_records_all", side_effect=RuntimeError("fail")):
            geolocation(mock_sf, chunk_size=100)  # Should not raise

    def test_uses_default_chunk_size(self, mock_sf):
        from audit.user_login import geolocation
        with patch("audit.user_login.query_records_all", return_value=[]), \
             patch("audit.user_login.geolocation_gauge"):
            geolocation(mock_sf)  # no chunk_size arg → hits line 140

    def test_handles_key_error_in_record(self, mock_sf):
        from audit.user_login import geolocation
        # Record missing UserId → KeyError in list comprehension
        with patch("audit.user_login.query_records_all", return_value=[{"NoUserId": "xxx"}]):
            geolocation(mock_sf, chunk_size=100)  # Should not raise

    def test_chunks_user_lookups(self, mock_sf):
        from audit.user_login import geolocation
        # 3 users, chunk_size=2 → 2 user queries
        locations = [self._make_location(f"u{i}") for i in range(3)]
        user_results = [{"Id": f"u{i}", "Name": f"User{i}"} for i in range(3)]
        with patch("audit.user_login.query_records_all", side_effect=[locations, user_results[:2], user_results[2:]]), \
             patch("audit.user_login.geolocation_gauge"):
            geolocation(mock_sf, chunk_size=2)
