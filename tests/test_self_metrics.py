"""Unit tests for self_metrics.py and its wiring into _run_job / query.py."""

from unittest.mock import MagicMock, patch

import pytest
import requests as requests_lib

from sfmon import self_metrics
from sfmon import salesforce_monitoring as sm
from sfmon.query import query_records_all


def _value(gauge, job, org="prod"):
    return gauge._values.get((("job", job), ("org", org)))


@pytest.fixture(autouse=True)
def _clear_gauges():
    for gauge in (
        self_metrics.job_success_gauge,
        self_metrics.job_last_run_gauge,
        self_metrics.job_last_success_gauge,
        self_metrics.job_duration_gauge,
        self_metrics.job_query_errors_gauge,
    ):
        gauge.clear_all()
    yield


class TestRecordJobResult:
    def test_success_sets_all_gauges(self):
        with patch("sfmon.org_gauge.get_current_org", return_value="prod"):
            started = self_metrics.start_job_run()
            self_metrics.record_job_result("my_job", started, True)

        assert _value(self_metrics.job_success_gauge, "my_job") == 1
        assert _value(self_metrics.job_query_errors_gauge, "my_job") == 0
        assert _value(self_metrics.job_duration_gauge, "my_job") >= 0
        last_run = _value(self_metrics.job_last_run_gauge, "my_job")
        assert last_run > 0
        assert _value(self_metrics.job_last_success_gauge, "my_job") == last_run

    def test_failure_keeps_previous_last_success(self):
        with patch("sfmon.org_gauge.get_current_org", return_value="prod"):
            self_metrics.record_job_result("my_job", self_metrics.start_job_run(), True)
            first_success = _value(self_metrics.job_last_success_gauge, "my_job")
            self_metrics.record_job_result("my_job", self_metrics.start_job_run(), False)

        assert _value(self_metrics.job_success_gauge, "my_job") == 0
        assert _value(self_metrics.job_last_success_gauge, "my_job") == first_success

    def test_failure_without_prior_success_leaves_last_success_unset(self):
        with patch("sfmon.org_gauge.get_current_org", return_value="prod"):
            self_metrics.record_job_result("my_job", self_metrics.start_job_run(), False)

        assert _value(self_metrics.job_success_gauge, "my_job") == 0
        assert _value(self_metrics.job_last_success_gauge, "my_job") is None


class TestQueryErrorCounting:
    def test_counts_errors_within_a_run(self):
        self_metrics.start_job_run()
        self_metrics.record_query_error()
        self_metrics.record_query_error()
        assert self_metrics.query_error_count() == 2

    def test_start_job_run_resets_count(self):
        self_metrics.start_job_run()
        self_metrics.record_query_error()
        self_metrics.start_job_run()
        assert self_metrics.query_error_count() == 0

    def test_failed_query_is_counted(self, mock_sf):
        mock_sf.query_all.side_effect = requests_lib.exceptions.Timeout()
        self_metrics.start_job_run()
        assert query_records_all(mock_sf, "SELECT Id FROM Account") == []
        assert self_metrics.query_error_count() == 1

    def test_failed_event_log_download_is_counted(self, mock_sf):
        from sfmon.query import get_event_log_file
        not_found = MagicMock(status_code=404, ok=False)
        self_metrics.start_job_run()
        with patch("sfmon.query.requests.get", return_value=not_found):
            assert get_event_log_file(mock_sf, "0AT1") is not_found
        assert self_metrics.query_error_count() == 1

    def test_successful_query_is_not_counted(self, mock_sf):
        mock_sf.query_all.return_value = {"records": []}
        self_metrics.start_job_run()
        query_records_all(mock_sf, "SELECT Id FROM Account")
        assert self_metrics.query_error_count() == 0


class TestRunJobSelfMetrics:
    def test_successful_job_reports_success(self):
        assert sm._run_job("prod", MagicMock(), MagicMock(), "My Job", "my_job") is True
        assert _value(self_metrics.job_success_gauge, "my_job") == 1

    def test_raising_job_reports_failure(self):
        func = MagicMock(side_effect=RuntimeError("boom"))
        assert sm._run_job("prod", MagicMock(), func, "My Job", "my_job") is False
        assert _value(self_metrics.job_success_gauge, "my_job") == 0

    def test_failed_query_does_not_stop_the_job(self, mock_sf):
        """One failed query is recorded, but the collector keeps running."""
        mock_sf.query_all.side_effect = [
            requests_lib.exceptions.Timeout(),
            {"records": [{"Id": "001"}]},
        ]
        results = []

        def collector(sf):
            results.append(query_records_all(sf, "SELECT Id FROM Account"))
            results.append(query_records_all(sf, "SELECT Id FROM Contact"))

        assert sm._run_job("prod", mock_sf, collector, "My Job", "my_job") is False
        assert results == [[], [{"Id": "001"}]]
        assert _value(self_metrics.job_success_gauge, "my_job") == 0
        assert _value(self_metrics.job_query_errors_gauge, "my_job") == 1

    def test_metrics_failure_does_not_break_the_job(self):
        func = MagicMock()
        with patch.object(
            self_metrics, "record_job_result", side_effect=RuntimeError("metrics broke")
        ):
            assert sm._run_job("prod", MagicMock(), func, "My Job", "my_job") is True
        func.assert_called_once()

    def test_run_once_exposes_self_metrics(self, capsys):
        with patch("sfmon.orgs.build_connections", return_value={"prod": MagicMock()}), \
             patch("sfmon.core.overall_sf_org.query_records_all", return_value=[]):
            sm.run_once(job_filter="monitor_salesforce_limits")

        out = capsys.readouterr().out
        assert 'sfmon_job_success{job="monitor_salesforce_limits",org="prod"}' in out
        assert "sfmon_job_duration_seconds" in out
