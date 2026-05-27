"""Unit tests for audit/report_export.py"""

import pytest
from unittest.mock import MagicMock, patch


class TestHourlyReportExportRecords:
    def _make_row(self, uri="/00O000000000001AAA", user_id="u01",
                  timestamp="2024-01-15T10:00:00.000Z"):
        return {"USER_ID": user_id, "TIMESTAMP_DERIVED": timestamp, "URI": uri}

    def test_sets_gauge_for_valid_report_id(self, mock_sf):
        from audit.report_export import hourly_report_export_records
        rows = [self._make_row()]
        report = [{"Id": "00O000000000001AAA", "Name": "My Report", "ReportTypeApiName": "AccountList"}]
        mock_gauge = MagicMock()
        with patch("audit.report_export.parse_logs", return_value=iter(rows)), \
             patch("audit.report_export.get_user_name", return_value="Alice"), \
             patch("audit.report_export.query_records_all", return_value=report), \
             patch("audit.report_export.hourly_report_export_metric", mock_gauge):
            hourly_report_export_records(mock_sf)
        mock_gauge.labels.assert_called_once()
        mock_gauge.labels().set.assert_called_once_with(1)

    def test_skips_invalid_report_id(self, mock_sf):
        from audit.report_export import hourly_report_export_records
        rows = [self._make_row(uri="/INVALID")]
        mock_gauge = MagicMock()
        with patch("audit.report_export.parse_logs", return_value=iter(rows)), \
             patch("audit.report_export.get_user_name", return_value="Alice"), \
             patch("audit.report_export.hourly_report_export_metric", mock_gauge):
            hourly_report_export_records(mock_sf)
        mock_gauge.labels.assert_not_called()

    def test_handles_uri_without_leading_slash(self, mock_sf):
        from audit.report_export import hourly_report_export_records
        rows = [self._make_row(uri="00O000000000001AAA")]
        report = [{"Id": "00O000000000001AAA", "Name": "Report", "ReportTypeApiName": "Type"}]
        mock_gauge = MagicMock()
        with patch("audit.report_export.parse_logs", return_value=iter(rows)), \
             patch("audit.report_export.get_user_name", return_value="Bob"), \
             patch("audit.report_export.query_records_all", return_value=report), \
             patch("audit.report_export.hourly_report_export_metric", mock_gauge):
            hourly_report_export_records(mock_sf)
        mock_gauge.labels.assert_called_once()

    def test_handles_none_logs(self, mock_sf):
        from audit.report_export import hourly_report_export_records
        mock_gauge = MagicMock()
        with patch("audit.report_export.parse_logs", return_value=None), \
             patch("audit.report_export.hourly_report_export_metric", mock_gauge):
            hourly_report_export_records(mock_sf)  # Should not raise (iterating None → exception → caught)

    def test_handles_exception(self, mock_sf):
        from audit.report_export import hourly_report_export_records
        with patch("audit.report_export.parse_logs", side_effect=RuntimeError("fail")), \
             patch("audit.report_export.hourly_report_export_metric"):
            hourly_report_export_records(mock_sf)  # Should not raise

    def test_sets_none_report_name_when_no_result(self, mock_sf):
        from audit.report_export import hourly_report_export_records
        rows = [self._make_row()]
        mock_gauge = MagicMock()
        captured = {}
        mock_gauge.labels.side_effect = lambda **kw: captured.update(kw) or MagicMock()
        with patch("audit.report_export.parse_logs", return_value=iter(rows)), \
             patch("audit.report_export.get_user_name", return_value="Alice"), \
             patch("audit.report_export.query_records_all", return_value=[]), \
             patch("audit.report_export.hourly_report_export_metric", mock_gauge):
            hourly_report_export_records(mock_sf)
        assert captured.get("report_name") is None
