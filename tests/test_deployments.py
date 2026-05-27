"""Unit tests for audit/deployments.py"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch


class TestParseDatetime:
    def test_parses_valid_datetime(self):
        from audit.deployments import parse_datetime
        result = parse_datetime("2024-01-15T10:30:00.000+0000")
        assert isinstance(result, datetime)

    def test_returns_none_for_none_input(self):
        from audit.deployments import parse_datetime
        assert parse_datetime(None) is None

    def test_returns_none_for_empty_string(self):
        from audit.deployments import parse_datetime
        assert parse_datetime("") is None


class TestCalculateMinutesDifference:
    def test_calculates_minutes(self):
        from audit.deployments import calculate_minutes_difference
        start = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 1, 10, 30, 0, tzinfo=timezone.utc)
        result = calculate_minutes_difference(start, end)
        assert result == pytest.approx(30.0)

    def test_returns_zero_when_start_is_none(self):
        from audit.deployments import calculate_minutes_difference
        end = datetime(2024, 1, 1, 10, 30, 0, tzinfo=timezone.utc)
        assert calculate_minutes_difference(None, end) == 0.0

    def test_returns_zero_when_end_is_none(self):
        from audit.deployments import calculate_minutes_difference
        start = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        assert calculate_minutes_difference(start, None) == 0.0

    def test_returns_zero_when_both_none(self):
        from audit.deployments import calculate_minutes_difference
        assert calculate_minutes_difference(None, None) == 0.0


class TestReportDeploymentMetrics:
    def _make_record(self, check_only=False):
        return {
            "Id": "dep01",
            "Status": "Succeeded",
            "StartDate": "2024-01-15T10:00:00.000+0000",
            "CompletedDate": "2024-01-15T10:30:00.000+0000",
            "CreatedBy": {"Name": "Admin"},
            "CheckOnly": check_only,
        }

    def test_uses_deployment_gauges_when_not_validation(self):
        from audit.deployments import report_deployment_metrics
        status_mapping = {"Succeeded": 1, "Failed": 0, "Canceled": -1}
        record = self._make_record(check_only=False)
        mock_detail = MagicMock()
        mock_pending = MagicMock()
        mock_time = MagicMock()
        with patch("audit.deployments.deployment_details_gauge", mock_detail), \
             patch("audit.deployments.pending_time_gauge", mock_pending), \
             patch("audit.deployments.deployment_time_gauge", mock_time):
            report_deployment_metrics(record, 30.0, 5.0, status_mapping, is_validation=False)
        mock_detail.labels.assert_called_once()
        mock_pending.labels.assert_called_once()
        mock_time.labels.assert_called_once()

    def test_uses_validation_gauges_when_check_only(self):
        from audit.deployments import report_deployment_metrics
        status_mapping = {"Succeeded": 1, "Failed": 0}
        record = self._make_record(check_only=True)
        mock_val_detail = MagicMock()
        mock_val_pending = MagicMock()
        mock_val_time = MagicMock()
        with patch("audit.deployments.validation_details_gauge", mock_val_detail), \
             patch("audit.deployments.validation_pending_time_gauge", mock_val_pending), \
             patch("audit.deployments.validation_time_gauge", mock_val_time):
            report_deployment_metrics(record, 20.0, 2.0, status_mapping, is_validation=True)
        mock_val_detail.labels.assert_called_once()
        mock_val_pending.labels.assert_called_once()
        mock_val_time.labels.assert_called_once()


class TestProcessDeploymentRecord:
    def _make_record(self):
        return {
            "Id": "dep01",
            "Status": "Succeeded",
            "StartDate": "2024-01-15T10:00:00.000+0000",
            "CompletedDate": "2024-01-15T10:30:00.000+0000",
            "CreatedDate": "2024-01-15T09:55:00.000+0000",
            "CreatedBy": {"Name": "Admin"},
        }

    def test_calls_report_with_calculated_times(self):
        from audit.deployments import process_deployment_record
        record = self._make_record()
        with patch("audit.deployments.report_deployment_metrics") as m_report:
            process_deployment_record(record, {"Succeeded": 1}, is_validation=False)
        m_report.assert_called_once()
        _, deployment_time, pending_time, _, _ = m_report.call_args.args
        assert deployment_time == pytest.approx(30.0)
        assert pending_time == pytest.approx(5.0)


class TestGetDeploymentStatus:
    def _make_record(self, status="Succeeded", check_only=False):
        return {
            "Id": "dep01",
            "Status": status,
            "StartDate": "2024-01-15T10:00:00.000+0000",
            "CompletedDate": "2024-01-15T10:30:00.000+0000",
            "CreatedDate": "2024-01-15T09:55:00.000+0000",
            "CreatedBy": {"Name": "Admin"},
            "CheckOnly": check_only,
        }

    def test_processes_succeeded_records(self, mock_sf):
        from audit.deployments import get_deployment_status
        records = [self._make_record("Succeeded")]
        with patch("audit.deployments.tooling_query_records_all", return_value=records), \
             patch("audit.deployments.process_deployment_record") as m_process:
            get_deployment_status(mock_sf)
        m_process.assert_called_once()

    def test_skips_in_progress_records(self, mock_sf):
        from audit.deployments import get_deployment_status
        records = [self._make_record("InProgress")]
        with patch("audit.deployments.tooling_query_records_all", return_value=records), \
             patch("audit.deployments.process_deployment_record") as m_process:
            get_deployment_status(mock_sf)
        m_process.assert_not_called()

    def test_processes_validation_records(self, mock_sf):
        from audit.deployments import get_deployment_status
        records = [self._make_record("Succeeded", check_only=True)]
        captured = {}
        def capture(record, mapping, is_validation):
            captured["is_validation"] = is_validation
        with patch("audit.deployments.tooling_query_records_all", return_value=records), \
             patch("audit.deployments.process_deployment_record", side_effect=capture):
            get_deployment_status(mock_sf)
        assert captured["is_validation"] is True

    def test_handles_exception(self, mock_sf):
        from audit.deployments import get_deployment_status
        with patch("audit.deployments.tooling_query_records_all", side_effect=RuntimeError("fail")):
            get_deployment_status(mock_sf)  # Should not raise
