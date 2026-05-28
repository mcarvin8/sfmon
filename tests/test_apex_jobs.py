"""Unit tests for ops/apex_jobs.py – parse_logs and Salesforce calls are mocked."""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch


class TestAsyncApexJobStatus:
    def test_aggregates_matching_records(self, mock_sf):
        from ops.apex_jobs import async_apex_job_status
        records = [
            {"Status": "Completed", "JobType": "BatchApex", "MethodName": "run", "NumberOfErrors": 0},
            {"Status": "Completed", "JobType": "BatchApex", "MethodName": "run", "NumberOfErrors": 0},
            {"Status": "Failed",    "JobType": "BatchApex", "MethodName": "run", "NumberOfErrors": 1},
        ]
        mock_gauge = MagicMock()
        with patch("ops.apex_jobs.query_records_all", return_value=records), \
             patch("ops.apex_jobs.async_job_status_gauge", mock_gauge):
            async_apex_job_status(mock_sf)
        # 2 unique (status, method, job_type, errors) combos
        assert mock_gauge.labels.call_count == 2

    def test_sets_count_per_unique_key(self, mock_sf):
        from ops.apex_jobs import async_apex_job_status
        records = [
            {"Status": "Completed", "JobType": "BatchApex", "MethodName": "execute", "NumberOfErrors": 0},
        ]
        captured = {}
        mock_gauge = MagicMock()
        mock_gauge.labels.return_value.set.side_effect = lambda v: captured.update({"count": v})
        with patch("ops.apex_jobs.query_records_all", return_value=records), \
             patch("ops.apex_jobs.async_job_status_gauge", mock_gauge):
            async_apex_job_status(mock_sf)
        assert captured["count"] == 1

    def test_empty_results(self, mock_sf):
        from ops.apex_jobs import async_apex_job_status
        mock_gauge = MagicMock()
        with patch("ops.apex_jobs.query_records_all", return_value=[]), \
             patch("ops.apex_jobs.async_job_status_gauge", mock_gauge):
            async_apex_job_status(mock_sf)
        mock_gauge.labels.assert_not_called()
        mock_gauge.clear.assert_called_once()


class TestMonitorApexExecutionTime:
    def _make_log_row(self, entry_point="EP.run", quiddity="S"):
        return {
            "ENTRY_POINT": entry_point, "QUIDDITY": quiddity,
            "RUN_TIME": "1500", "CPU_TIME": "200",
            "EXEC_TIME": "100", "DB_TOTAL_TIME": "50", "CALLOUT_TIME": "0",
        }

    def test_sets_all_time_metrics(self, mock_sf):
        from ops.apex_jobs import monitor_apex_execution_time
        logs = [self._make_log_row()]
        with patch("ops.apex_jobs.parse_logs", return_value=iter(logs)), \
             patch("ops.apex_jobs.run_time_metric") as m_run, \
             patch("ops.apex_jobs.cpu_time_metric") as m_cpu, \
             patch("ops.apex_jobs.exec_time_metric") as m_exec, \
             patch("ops.apex_jobs.db_total_time_metric") as m_db, \
             patch("ops.apex_jobs.callout_time_metric") as m_callout:
            monitor_apex_execution_time(mock_sf)
        m_run.labels.assert_called_once()
        m_cpu.labels.assert_called_once()
        m_exec.labels.assert_called_once()
        m_db.labels.assert_called_once()
        m_callout.labels.assert_called_once()

    def test_handles_none_logs(self, mock_sf):
        from ops.apex_jobs import monitor_apex_execution_time
        with patch("ops.apex_jobs.parse_logs", return_value=None), \
             patch("ops.apex_jobs.run_time_metric") as m_run:
            monitor_apex_execution_time(mock_sf)  # Should not raise
        m_run.labels.assert_not_called()

    def test_handles_exception(self, mock_sf):
        from ops.apex_jobs import monitor_apex_execution_time
        with patch("ops.apex_jobs.parse_logs", side_effect=RuntimeError("fail")):
            monitor_apex_execution_time(mock_sf)  # Should not raise


class TestExposeApexExceptionMetrics:
    def _make_exception_row(self, category="ApexException"):
        return {
            "EXCEPTION_CATEGORY": category,
            "REQUEST_ID": "req-001",
            "EXCEPTION_TYPE": "System.NullPointerException",
            "EXCEPTION_MESSAGE": "Attempt to de-reference a null object",
            "STACK_TRACE": "Class.run: line 42",
            "TIMESTAMP_DERIVED": "2024-01-15T10:00:00.000Z",
        }

    def test_exposes_exception_detail_metric(self, mock_sf):
        from ops.apex_jobs import expose_apex_exception_metrics
        logs = [self._make_exception_row()]
        mock_detail = MagicMock()
        mock_category = MagicMock()
        with patch("ops.apex_jobs.parse_logs", return_value=iter(logs)), \
             patch("ops.apex_jobs.apex_exception_details_gauge", mock_detail), \
             patch("ops.apex_jobs.apex_exception_category_count_gauge", mock_category):
            expose_apex_exception_metrics(mock_sf)
        mock_detail.labels.assert_called_once()
        mock_detail.labels().set.assert_called_once_with(1)

    def test_counts_exception_categories(self, mock_sf):
        from ops.apex_jobs import expose_apex_exception_metrics
        logs = [
            self._make_exception_row("ApexException"),
            self._make_exception_row("ApexException"),
            self._make_exception_row("DatabaseError"),
        ]
        mock_detail = MagicMock()
        mock_category = MagicMock()
        with patch("ops.apex_jobs.parse_logs", return_value=iter(logs)), \
             patch("ops.apex_jobs.apex_exception_details_gauge", mock_detail), \
             patch("ops.apex_jobs.apex_exception_category_count_gauge", mock_category):
            expose_apex_exception_metrics(mock_sf)
        assert mock_category.labels.call_count == 2

    def test_handles_empty_logs(self, mock_sf):
        from ops.apex_jobs import expose_apex_exception_metrics
        mock_detail = MagicMock()
        mock_category = MagicMock()
        with patch("ops.apex_jobs.parse_logs", return_value=iter([])), \
             patch("ops.apex_jobs.apex_exception_details_gauge", mock_detail), \
             patch("ops.apex_jobs.apex_exception_category_count_gauge", mock_category):
            expose_apex_exception_metrics(mock_sf)
        mock_detail.labels.assert_not_called()

    def test_handles_missing_key_gracefully(self, mock_sf):
        from ops.apex_jobs import expose_apex_exception_metrics
        # Row missing required keys should not crash
        logs = [{"EXCEPTION_CATEGORY": "ApexException"}]
        mock_detail = MagicMock()
        mock_category = MagicMock()
        with patch("ops.apex_jobs.parse_logs", return_value=iter(logs)), \
             patch("ops.apex_jobs.apex_exception_details_gauge", mock_detail), \
             patch("ops.apex_jobs.apex_exception_category_count_gauge", mock_category):
            expose_apex_exception_metrics(mock_sf)  # Should not raise


class TestExposeConcurrentErrorsByAvgRuntime:
    def _make_df(self):
        return pd.DataFrame({
            "ENTRY_POINT": ["EP1", "EP1", "EP2"],
            "RUN_TIME":    [6000.0, 7000.0, 8000.0],
            "EXEC_TIME":   [100.0, 200.0, 300.0],
            "DB_TOTAL_TIME": [50.0, 60.0, 70.0],
        })

    def test_emits_gauge_per_entry_point(self):
        from ops.apex_jobs import expose_concurrent_errors_metrics_sorted_by_average_runtime
        mock_gauge = MagicMock()
        with patch("ops.apex_jobs.top_apex_concurrent_errors_sorted_by_avg_runtime", mock_gauge):
            expose_concurrent_errors_metrics_sorted_by_average_runtime(self._make_df())
        assert mock_gauge.labels.call_count == 2

    def test_handles_empty_dataframe(self):
        from ops.apex_jobs import expose_concurrent_errors_metrics_sorted_by_average_runtime
        df = pd.DataFrame(columns=["ENTRY_POINT", "RUN_TIME", "EXEC_TIME", "DB_TOTAL_TIME"])
        mock_gauge = MagicMock()
        with patch("ops.apex_jobs.top_apex_concurrent_errors_sorted_by_avg_runtime", mock_gauge):
            expose_concurrent_errors_metrics_sorted_by_average_runtime(df)
        mock_gauge.labels.assert_not_called()

    def test_caps_at_top_5(self):
        from ops.apex_jobs import expose_concurrent_errors_metrics_sorted_by_average_runtime
        df = pd.DataFrame({
            "ENTRY_POINT":   [f"EP{i}" for i in range(10)],
            "RUN_TIME":      [float(i * 1000) for i in range(10)],
            "EXEC_TIME":     [100.0] * 10,
            "DB_TOTAL_TIME": [50.0] * 10,
        })
        mock_gauge = MagicMock()
        with patch("ops.apex_jobs.top_apex_concurrent_errors_sorted_by_avg_runtime", mock_gauge):
            expose_concurrent_errors_metrics_sorted_by_average_runtime(df)
        assert mock_gauge.labels.call_count <= 5


class TestExposeConcurrentErrorsByCount:
    def _make_df(self):
        return pd.DataFrame({
            "ENTRY_POINT":   ["EP1", "EP1", "EP1", "EP2"],
            "RUN_TIME":      [6000.0, 7000.0, 8000.0, 9000.0],
            "EXEC_TIME":     [100.0, 200.0, 300.0, 400.0],
            "DB_TOTAL_TIME": [50.0, 60.0, 70.0, 80.0],
        })

    def test_emits_gauge_per_entry_point(self):
        from ops.apex_jobs import expose_concurrent_errors_metrics_sorted_by_request_count
        mock_gauge = MagicMock()
        with patch("ops.apex_jobs.top_apex_concurrent_errors_sorted_by_count", mock_gauge):
            expose_concurrent_errors_metrics_sorted_by_request_count(self._make_df())
        assert mock_gauge.labels.call_count == 2

    def test_handles_empty_dataframe(self):
        from ops.apex_jobs import expose_concurrent_errors_metrics_sorted_by_request_count
        df = pd.DataFrame(columns=["ENTRY_POINT", "RUN_TIME", "EXEC_TIME", "DB_TOTAL_TIME"])
        mock_gauge = MagicMock()
        with patch("ops.apex_jobs.top_apex_concurrent_errors_sorted_by_count", mock_gauge):
            expose_concurrent_errors_metrics_sorted_by_request_count(df)
        mock_gauge.labels.assert_not_called()


class TestConcurrentApexErrors:
    def _make_logs(self):
        return [
            {"ENTRY_POINT": "EP1", "RUN_TIME": "6000", "IS_LONG_RUNNING_REQUEST": "1",
             "EXEC_TIME": "100", "DB_TOTAL_TIME": "50"},
            {"ENTRY_POINT": "EP2", "RUN_TIME": "100",  "IS_LONG_RUNNING_REQUEST": "0",
             "EXEC_TIME": "10",  "DB_TOTAL_TIME": "5"},
        ]

    def test_no_long_running_requests_returns_early(self, mock_sf):
        from ops.apex_jobs import concurrent_apex_errors
        logs = [{"ENTRY_POINT": "EP1", "RUN_TIME": "100", "IS_LONG_RUNNING_REQUEST": "0",
                 "EXEC_TIME": "10", "DB_TOTAL_TIME": "5"}]
        with patch("ops.apex_jobs.parse_logs", return_value=iter(logs)):
            concurrent_apex_errors(mock_sf)  # Should not raise

    def test_long_running_requests_invoke_sub_functions(self, mock_sf):
        from ops.apex_jobs import concurrent_apex_errors
        logs = self._make_logs()
        with patch("ops.apex_jobs.parse_logs", return_value=iter(logs)), \
             patch("ops.apex_jobs.expose_concurrent_errors_metrics_sorted_by_average_runtime") as m_avg, \
             patch("ops.apex_jobs.expose_concurrent_errors_metrics_sorted_by_request_count") as m_cnt:
            concurrent_apex_errors(mock_sf)
        m_avg.assert_called_once()
        m_cnt.assert_called_once()

    def test_handles_none_logs(self, mock_sf):
        from ops.apex_jobs import concurrent_apex_errors
        with patch("ops.apex_jobs.parse_logs", return_value=None):
            concurrent_apex_errors(mock_sf)  # Should not raise

    def test_handles_exception(self, mock_sf):
        from ops.apex_jobs import concurrent_apex_errors
        with patch("ops.apex_jobs.parse_logs", side_effect=RuntimeError("fail")):
            concurrent_apex_errors(mock_sf)  # Should not raise


class TestExposeConcurrentLongRunningApexErrors:
    def test_no_logs_returns_early(self, mock_sf):
        from ops.apex_jobs import expose_concurrent_long_running_apex_errors
        mock_gauge = MagicMock()
        with patch("ops.apex_jobs.parse_logs", return_value=None), \
             patch("ops.apex_jobs.concurrent_errors_count_gauge", mock_gauge):
            expose_concurrent_long_running_apex_errors(mock_sf)
        mock_gauge.labels.assert_not_called()

    def test_counts_request_ids(self, mock_sf):
        from ops.apex_jobs import expose_concurrent_long_running_apex_errors
        logs = [
            {"REQUEST_ID": "req-001", "EVENT_TYPE": "ConcurrentLongRunningApexLimit"},
            {"REQUEST_ID": "req-002", "EVENT_TYPE": "ConcurrentLongRunningApexLimit"},
        ]
        mock_gauge = MagicMock()
        with patch("ops.apex_jobs.parse_logs", return_value=iter(logs)), \
             patch("ops.apex_jobs.concurrent_errors_count_gauge", mock_gauge):
            expose_concurrent_long_running_apex_errors(mock_sf)
        mock_gauge.labels.assert_called_once()
        mock_gauge.labels().set.assert_called_once_with(2)

    def test_handles_exception(self, mock_sf):
        from ops.apex_jobs import expose_concurrent_long_running_apex_errors
        with patch("ops.apex_jobs.parse_logs", side_effect=RuntimeError("fail")):
            expose_concurrent_long_running_apex_errors(mock_sf)  # Should not raise


class TestAsyncApexExecutionSummary:
    def _make_logs(self):
        return [
            {"ENTRY_POINT": "EP1", "QUIDDITY": "S", "RUN_TIME": "6000", "CPU_TIME": "500"},
            {"ENTRY_POINT": "EP1", "QUIDDITY": "S", "RUN_TIME": "11000", "CPU_TIME": "800"},
            {"ENTRY_POINT": "EP2", "QUIDDITY": "BA", "RUN_TIME": "3000", "CPU_TIME": "200"},
        ]

    def test_sets_summary_gauges(self, mock_sf):
        from ops.apex_jobs import async_apex_execution_summary
        logs = self._make_logs()
        mocks = {
            "apex_entry_point_count": MagicMock(),
            "apex_avg_runtime": MagicMock(),
            "apex_max_runtime": MagicMock(),
            "apex_total_runtime": MagicMock(),
            "apex_avg_cputime": MagicMock(),
            "apex_max_cputime": MagicMock(),
            "apex_runtime_gt_5s_count": MagicMock(),
            "apex_runtime_gt_10s_count": MagicMock(),
            "apex_runtime_gt_5s_percentage": MagicMock(),
        }
        patches = {f"ops.apex_jobs.{k}": v for k, v in mocks.items()}
        with patch("ops.apex_jobs.parse_logs", return_value=iter(logs)):
            with patch.multiple("ops.apex_jobs", **{k.split(".")[-1]: v for k, v in patches.items()}):
                async_apex_execution_summary(mock_sf)

    def test_filters_invalid_quiddities(self, mock_sf):
        from ops.apex_jobs import async_apex_execution_summary
        logs = [
            {"ENTRY_POINT": "EP1", "QUIDDITY": "INVALID", "RUN_TIME": "1000", "CPU_TIME": "100"},
        ]
        with patch("ops.apex_jobs.parse_logs", return_value=iter(logs)), \
             patch("ops.apex_jobs.apex_entry_point_count") as m:
            async_apex_execution_summary(mock_sf)
        m.labels.assert_not_called()

    def test_handles_none_logs(self, mock_sf):
        from ops.apex_jobs import async_apex_execution_summary
        with patch("ops.apex_jobs.parse_logs", return_value=None):
            async_apex_execution_summary(mock_sf)  # Should not raise

    def test_handles_exception(self, mock_sf):
        from ops.apex_jobs import async_apex_execution_summary
        with patch("ops.apex_jobs.parse_logs", side_effect=RuntimeError("fail")):
            async_apex_execution_summary(mock_sf)  # Should not raise


class TestExposeApexExceptionMetricsExceptions:
    """Tests for exception branches in expose_apex_exception_metrics."""

    def test_handles_key_error_in_row(self, mock_sf):
        from ops.apex_jobs import expose_apex_exception_metrics
        # Row missing required keys → KeyError
        logs = [{"EXCEPTION_CATEGORY": "ApexException"}]
        mock_detail = MagicMock()
        mock_detail.labels.side_effect = KeyError("EXCEPTION_TYPE")
        mock_category = MagicMock()
        with patch("ops.apex_jobs.parse_logs", return_value=iter(logs)), \
             patch("ops.apex_jobs.apex_exception_details_gauge", mock_detail), \
             patch("ops.apex_jobs.apex_exception_category_count_gauge", mock_category):
            expose_apex_exception_metrics(mock_sf)  # Should not raise

    def test_handles_category_count_exception(self, mock_sf):
        from ops.apex_jobs import expose_apex_exception_metrics
        logs = [{"EXCEPTION_CATEGORY": "ApexException", "REQUEST_ID": "r1",
                 "EXCEPTION_TYPE": "System.NullPointerException",
                 "EXCEPTION_MESSAGE": "msg", "STACK_TRACE": "trace",
                 "TIMESTAMP_DERIVED": "2024-01-15T10:00:00Z"}]
        mock_detail = MagicMock()
        mock_category = MagicMock()
        mock_category.labels.side_effect = RuntimeError("gauge error")
        with patch("ops.apex_jobs.parse_logs", return_value=iter(logs)), \
             patch("ops.apex_jobs.apex_exception_details_gauge", mock_detail), \
             patch("ops.apex_jobs.apex_exception_category_count_gauge", mock_category):
            expose_apex_exception_metrics(mock_sf)  # Should not raise


class TestExposeConcurrentErrorsExceptions:
    """Tests for KeyError branches in concurrent error gauge functions."""

    def test_avg_runtime_handles_key_error(self):
        import pandas as pd
        from ops.apex_jobs import expose_concurrent_errors_metrics_sorted_by_average_runtime
        # Pass DataFrame missing required column
        df = pd.DataFrame({"ENTRY_POINT": ["EP1"], "MISSING": [1.0]})
        mock_gauge = MagicMock()
        with patch("ops.apex_jobs.top_apex_concurrent_errors_sorted_by_avg_runtime", mock_gauge):
            expose_concurrent_errors_metrics_sorted_by_average_runtime(df)  # Should not raise

    def test_request_count_handles_key_error(self):
        import pandas as pd
        from ops.apex_jobs import expose_concurrent_errors_metrics_sorted_by_request_count
        df = pd.DataFrame({"ENTRY_POINT": ["EP1"], "MISSING": [1.0]})
        mock_gauge = MagicMock()
        with patch("ops.apex_jobs.top_apex_concurrent_errors_sorted_by_count", mock_gauge):
            expose_concurrent_errors_metrics_sorted_by_request_count(df)  # Should not raise

    def test_avg_runtime_handles_exception(self):
        import pandas as pd
        from ops.apex_jobs import expose_concurrent_errors_metrics_sorted_by_average_runtime
        df = pd.DataFrame({"ENTRY_POINT": ["EP1"], "RUN_TIME": [1.0], "EXEC_TIME": [0.5], "DB_TOTAL_TIME": [0.2]})
        mock_gauge = MagicMock()
        mock_gauge.clear.side_effect = RuntimeError("gauge error")
        with patch("ops.apex_jobs.top_apex_concurrent_errors_sorted_by_avg_runtime", mock_gauge):
            expose_concurrent_errors_metrics_sorted_by_average_runtime(df)  # Should not raise

    def test_request_count_handles_exception(self):
        import pandas as pd
        from ops.apex_jobs import expose_concurrent_errors_metrics_sorted_by_request_count
        df = pd.DataFrame({"ENTRY_POINT": ["EP1"], "RUN_TIME": [1.0], "EXEC_TIME": [0.5], "DB_TOTAL_TIME": [0.2]})
        mock_gauge = MagicMock()
        mock_gauge.clear.side_effect = RuntimeError("gauge error")
        with patch("ops.apex_jobs.top_apex_concurrent_errors_sorted_by_count", mock_gauge):
            expose_concurrent_errors_metrics_sorted_by_request_count(df)  # Should not raise


class TestExposeApexExceptionMetricsTypeAndGenericErrors:
    """Tests for TypeError and generic Exception branches in expose_apex_exception_metrics."""

    def test_handles_type_error_in_row(self, mock_sf):
        from ops.apex_jobs import expose_apex_exception_metrics
        logs = [{"EXCEPTION_CATEGORY": "ApexException", "REQUEST_ID": "r1",
                 "EXCEPTION_TYPE": "NullPointerException", "EXCEPTION_MESSAGE": "msg",
                 "STACK_TRACE": "trace", "TIMESTAMP_DERIVED": "2024-01-15"}]
        mock_detail = MagicMock()
        mock_detail.labels.side_effect = TypeError("bad type")
        mock_category = MagicMock()
        with patch("ops.apex_jobs.parse_logs", return_value=iter(logs)), \
             patch("ops.apex_jobs.apex_exception_details_gauge", mock_detail), \
             patch("ops.apex_jobs.apex_exception_category_count_gauge", mock_category):
            expose_apex_exception_metrics(mock_sf)  # Should not raise

    def test_handles_generic_exception_in_row(self, mock_sf):
        from ops.apex_jobs import expose_apex_exception_metrics
        logs = [{"EXCEPTION_CATEGORY": "ApexException", "REQUEST_ID": "r1",
                 "EXCEPTION_TYPE": "NullPointerException", "EXCEPTION_MESSAGE": "msg",
                 "STACK_TRACE": "trace", "TIMESTAMP_DERIVED": "2024-01-15"}]
        mock_detail = MagicMock()
        mock_detail.labels.side_effect = RuntimeError("unexpected error")
        mock_category = MagicMock()
        with patch("ops.apex_jobs.parse_logs", return_value=iter(logs)), \
             patch("ops.apex_jobs.apex_exception_details_gauge", mock_detail), \
             patch("ops.apex_jobs.apex_exception_category_count_gauge", mock_category):
            expose_apex_exception_metrics(mock_sf)  # Should not raise
