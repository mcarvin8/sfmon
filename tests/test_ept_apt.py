"""Unit tests for ops/ept_apt.py"""

from collections import defaultdict
from unittest.mock import MagicMock, patch

import pytest


class TestFetchLatestLightningPageviewLog:
    def test_returns_first_record(self, mock_sf):
        from ops.ept_apt import fetch_latest_lightning_pageview_log
        records = [{"Id": "elf001", "EventType": "LightningPageView"}]
        with patch("ops.ept_apt.query_records_all", return_value=records):
            result = fetch_latest_lightning_pageview_log(mock_sf)
        assert result == records[0]

    def test_returns_none_when_empty(self, mock_sf):
        from ops.ept_apt import fetch_latest_lightning_pageview_log
        with patch("ops.ept_apt.query_records_all", return_value=[]):
            result = fetch_latest_lightning_pageview_log(mock_sf)
        assert result is None


class TestDownloadLogFile:
    def _make_sf(self):
        sf = MagicMock()
        sf.base_url = "https://org.salesforce.com"
        sf.session_id = "TOKEN"
        return sf

    def test_returns_text_on_200(self):
        from ops.ept_apt import download_log_file
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "FIELD1,FIELD2\nval1,val2"
        with patch("ops.ept_apt.requests.get", return_value=mock_resp):
            result = download_log_file(self._make_sf(), "logId")
        assert result == "FIELD1,FIELD2\nval1,val2"

    def test_returns_none_on_non_200(self):
        from ops.ept_apt import download_log_file
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        with patch("ops.ept_apt.requests.get", return_value=mock_resp):
            result = download_log_file(self._make_sf(), "logId")
        assert result is None


class TestParseLogData:
    def _make_csv(self, rows):
        header = "PAGE_APP_NAME,DURATION,EFFECTIVE_PAGE_TIME_DEVIATION,EFFECTIVE_PAGE_TIME"
        lines = [header] + [
            f"{r['PAGE_APP_NAME']},{r.get('DURATION','')},{r.get('EFFECTIVE_PAGE_TIME_DEVIATION','')},{r.get('EFFECTIVE_PAGE_TIME','')}"
            for r in rows
        ]
        return "\n".join(lines)

    def test_accumulates_page_time(self):
        from ops.ept_apt import parse_log_data
        csv_data = self._make_csv([
            {"PAGE_APP_NAME": "Sales", "DURATION": "2000"},
            {"PAGE_APP_NAME": "Sales", "DURATION": "4000"},
        ])
        page_time_data, ept_rows = parse_log_data(csv_data)
        assert page_time_data["Sales"]["count"] == 2
        assert ept_rows == []

    def test_collects_ept_rows(self):
        from ops.ept_apt import parse_log_data
        csv_data = self._make_csv([
            {"PAGE_APP_NAME": "Home", "DURATION": "3000",
             "EFFECTIVE_PAGE_TIME_DEVIATION": "HIGH", "EFFECTIVE_PAGE_TIME": "2500"},
        ])
        page_time_data, ept_rows = parse_log_data(csv_data)
        assert len(ept_rows) == 1


class TestUpdatePageTimeData:
    def test_accumulates_duration(self):
        from ops.ept_apt import update_page_time_data
        data = defaultdict(lambda: {"total_time": 0, "count": 0})
        update_page_time_data(data, {"PAGE_APP_NAME": "Home", "DURATION": "3000"})
        update_page_time_data(data, {"PAGE_APP_NAME": "Home", "DURATION": "1000"})
        assert data["Home"]["count"] == 2
        assert data["Home"]["total_time"] == pytest.approx(4.0)

    def test_handles_missing_duration(self):
        from ops.ept_apt import update_page_time_data
        data = defaultdict(lambda: {"total_time": 0, "count": 0})
        update_page_time_data(data, {"PAGE_APP_NAME": "About"})
        assert data["About"]["count"] == 1
        assert data["About"]["total_time"] == 0

    def test_unknown_page_name(self):
        from ops.ept_apt import update_page_time_data
        data = defaultdict(lambda: {"total_time": 0, "count": 0})
        update_page_time_data(data, {"PAGE_APP_NAME": None, "DURATION": "500"})
        assert "Unknown_Page" in data


class TestReportAptMetrics:
    def test_sets_metric_per_page(self):
        from ops.ept_apt import report_apt_metrics
        page_time_data = defaultdict(lambda: {"total_time": 0, "count": 0})
        page_time_data["Home"]["total_time"] = 6.0
        page_time_data["Home"]["count"] = 3
        mock_apt = MagicMock()
        with patch("ops.ept_apt.apt_metric", mock_apt):
            report_apt_metrics(page_time_data)
        mock_apt.labels.assert_called_once_with(Page_name="Home")
        mock_apt.labels().set.assert_called_once_with(2.0)

    def test_skips_zero_count(self):
        from ops.ept_apt import report_apt_metrics
        page_time_data = defaultdict(lambda: {"total_time": 0, "count": 0})
        page_time_data["Home"]["total_time"] = 0
        page_time_data["Home"]["count"] = 0
        mock_apt = MagicMock()
        with patch("ops.ept_apt.apt_metric", mock_apt):
            report_apt_metrics(page_time_data)
        mock_apt.labels.assert_not_called()


class TestReportEptMetrics:
    def test_sets_metric_per_row(self):
        from ops.ept_apt import report_ept_metrics
        rows = [{
            "EFFECTIVE_PAGE_TIME_DEVIATION_REASON": "SLOW",
            "EFFECTIVE_PAGE_TIME_DEVIATION_ERROR_TYPE": "network",
            "PREVPAGE_ENTITY_TYPE": "Case",
            "PREVPAGE_APP_NAME": "Service",
            "PAGE_ENTITY_TYPE": "Lead",
            "PAGE_APP_NAME": "Sales",
            "BROWSER_NAME": "Chrome",
            "EFFECTIVE_PAGE_TIME": "3000",
        }]
        mock_ept = MagicMock()
        with patch("ops.ept_apt.ept_metric", mock_ept):
            report_ept_metrics(rows)
        mock_ept.labels.assert_called_once()
        mock_ept.labels().set.assert_called_once_with(3.0)


class TestGetSalesforceEptAndApt:
    def test_handles_no_record(self, mock_sf):
        from ops.ept_apt import get_salesforce_ept_and_apt
        with patch("ops.ept_apt.fetch_latest_lightning_pageview_log", return_value=None):
            get_salesforce_ept_and_apt(mock_sf)  # Should not raise

    def test_handles_no_log_data(self, mock_sf):
        from ops.ept_apt import get_salesforce_ept_and_apt
        with patch("ops.ept_apt.fetch_latest_lightning_pageview_log", return_value={"Id": "e01"}), \
             patch("ops.ept_apt.download_log_file", return_value=None):
            get_salesforce_ept_and_apt(mock_sf)  # Should not raise

    def test_handles_exception(self, mock_sf):
        from ops.ept_apt import get_salesforce_ept_and_apt
        with patch("ops.ept_apt.fetch_latest_lightning_pageview_log", side_effect=RuntimeError("fail")):
            get_salesforce_ept_and_apt(mock_sf)  # Should not raise

    def test_full_flow(self, mock_sf):
        from ops.ept_apt import get_salesforce_ept_and_apt
        with patch("ops.ept_apt.fetch_latest_lightning_pageview_log", return_value={"Id": "e01"}), \
             patch("ops.ept_apt.download_log_file", return_value="PAGE_APP_NAME,DURATION\nHome,2000"), \
             patch("ops.ept_apt.report_apt_metrics") as m_apt, \
             patch("ops.ept_apt.report_ept_metrics") as m_ept:
            get_salesforce_ept_and_apt(mock_sf)
        m_apt.assert_called_once()
        m_ept.assert_called_once()
