"""Unit tests for tech_debt/scheduled_jobs.py"""

import pytest
from unittest.mock import MagicMock, patch


class TestScheduledApexJobsMonitoring:
    def _make_record(self, **overrides):
        base = {
            "Id": "cron01",
            "CronJobDetail": {"Name": "MyScheduledJob", "JobType": "7"},
            "CronExpression": "0 0 * * * ?",
            "State": "WAITING",
            "NextFireTime": "2024-02-01T00:00:00.000Z",
            "PreviousFireTime": "2024-01-01T00:00:00.000Z",
            "TimesTriggered": "5",
            "CreatedBy": {"Name": "Admin"},
            "CreatedDate": "2023-01-01T00:00:00.000Z",
        }
        base.update(overrides)
        return base

    def test_sets_gauge_per_job(self, mock_sf):
        from tech_debt.scheduled_jobs import scheduled_apex_jobs_monitoring
        records = [self._make_record(), self._make_record(Id="cron02")]
        mock_gauge = MagicMock()
        with patch("tech_debt.scheduled_jobs.query_records_all", return_value=records), \
             patch("tech_debt.scheduled_jobs.scheduled_apex_jobs_gauge", mock_gauge):
            scheduled_apex_jobs_monitoring(mock_sf)
        assert mock_gauge.labels.call_count == 2
        mock_gauge.clear.assert_called_once()

    def test_times_triggered_set_correctly(self, mock_sf):
        from tech_debt.scheduled_jobs import scheduled_apex_jobs_monitoring
        records = [self._make_record(TimesTriggered="42")]
        mock_gauge = MagicMock()
        with patch("tech_debt.scheduled_jobs.query_records_all", return_value=records), \
             patch("tech_debt.scheduled_jobs.scheduled_apex_jobs_gauge", mock_gauge):
            scheduled_apex_jobs_monitoring(mock_sf)
        mock_gauge.labels().set.assert_called_once_with(42)

    def test_null_next_fire_time_becomes_none_string(self, mock_sf):
        from tech_debt.scheduled_jobs import scheduled_apex_jobs_monitoring
        records = [self._make_record(NextFireTime=None, PreviousFireTime=None)]
        captured = {}
        mock_gauge = MagicMock()
        mock_gauge.labels.side_effect = lambda **kw: captured.update(kw) or MagicMock()
        with patch("tech_debt.scheduled_jobs.query_records_all", return_value=records), \
             patch("tech_debt.scheduled_jobs.scheduled_apex_jobs_gauge", mock_gauge):
            scheduled_apex_jobs_monitoring(mock_sf)
        assert captured.get("next_fire_time") == "None"
        assert captured.get("previous_fire_time") == "None"

    def test_null_cron_job_detail_uses_defaults(self, mock_sf):
        from tech_debt.scheduled_jobs import scheduled_apex_jobs_monitoring
        records = [self._make_record(CronJobDetail=None, CreatedBy=None)]
        captured = {}
        mock_gauge = MagicMock()
        mock_gauge.labels.side_effect = lambda **kw: captured.update(kw) or MagicMock()
        with patch("tech_debt.scheduled_jobs.query_records_all", return_value=records), \
             patch("tech_debt.scheduled_jobs.scheduled_apex_jobs_gauge", mock_gauge):
            scheduled_apex_jobs_monitoring(mock_sf)
        assert captured.get("job_name") == "Unknown"
        assert captured.get("created_by") == "Unknown"

    def test_empty_results(self, mock_sf):
        from tech_debt.scheduled_jobs import scheduled_apex_jobs_monitoring
        mock_gauge = MagicMock()
        with patch("tech_debt.scheduled_jobs.query_records_all", return_value=[]), \
             patch("tech_debt.scheduled_jobs.scheduled_apex_jobs_gauge", mock_gauge):
            scheduled_apex_jobs_monitoring(mock_sf)
        mock_gauge.labels.assert_not_called()

    def test_handles_exception(self, mock_sf):
        from tech_debt.scheduled_jobs import scheduled_apex_jobs_monitoring
        with patch("tech_debt.scheduled_jobs.query_records_all", side_effect=RuntimeError("fail")):
            scheduled_apex_jobs_monitoring(mock_sf)  # Should not raise
