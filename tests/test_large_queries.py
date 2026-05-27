"""Unit tests for audit/large_queries.py"""

import pytest
from unittest.mock import MagicMock, patch


class TestIsLargeQuery:
    def test_returns_true_above_threshold(self):
        from audit.large_queries import is_large_query
        row = {"ROWS_PROCESSED": "50000"}
        assert is_large_query(row) is True

    def test_returns_false_below_threshold(self):
        from audit.large_queries import is_large_query
        row = {"ROWS_PROCESSED": "100"}
        assert is_large_query(row) is False

    def test_returns_false_for_empty_string(self):
        from audit.large_queries import is_large_query
        row = {"ROWS_PROCESSED": ""}
        assert is_large_query(row) is False

    def test_returns_false_for_missing_key(self):
        from audit.large_queries import is_large_query
        row = {}
        assert is_large_query(row) is False


class TestReportLargeQueries:
    def test_sets_metric_when_queries_present(self):
        from audit.large_queries import report_large_queries
        queries = {("u1", "Alice", "query", "Account", 50000)}
        mock_gauge = MagicMock()
        with patch("audit.large_queries.hourly_large_query_metric", mock_gauge):
            report_large_queries(queries)
        mock_gauge.labels.assert_called_once_with(
            user_id="u1", user_name="Alice", method="query", entity_name="Account"
        )
        mock_gauge.labels().set.assert_called_once_with(50000)

    def test_sets_none_label_when_no_queries(self):
        from audit.large_queries import report_large_queries
        mock_gauge = MagicMock()
        with patch("audit.large_queries.hourly_large_query_metric", mock_gauge):
            report_large_queries(set())
        mock_gauge.labels.assert_called_once_with(
            user_id="none", user_name="No Large Queries", method="none", entity_name="none"
        )


class TestCollectLargeQueries:
    def test_returns_empty_set_when_no_logs(self, mock_sf):
        from audit.large_queries import collect_large_queries
        with patch("audit.large_queries.parse_logs", return_value=None):
            result = collect_large_queries(mock_sf)
        assert result == set()

    def test_collects_large_queries(self, mock_sf):
        from audit.large_queries import collect_large_queries
        logs = [
            {"USER_ID": "u1", "ROWS_PROCESSED": "50000", "METHOD_NAME": "query", "ENTITY_NAME": "Account"},
        ]
        with patch("audit.large_queries.parse_logs", return_value=iter(logs)), \
             patch("audit.large_queries.get_user_name", return_value="Alice"):
            result = collect_large_queries(mock_sf)
        assert len(result) == 1

    def test_skips_rows_below_threshold(self, mock_sf):
        from audit.large_queries import collect_large_queries
        logs = [
            {"USER_ID": "u1", "ROWS_PROCESSED": "100", "METHOD_NAME": "query", "ENTITY_NAME": "Account"},
        ]
        with patch("audit.large_queries.parse_logs", return_value=iter(logs)):
            result = collect_large_queries(mock_sf)
        assert result == set()

    def test_skips_rows_without_user_id(self, mock_sf):
        from audit.large_queries import collect_large_queries
        logs = [
            {"USER_ID": "", "ROWS_PROCESSED": "50000", "METHOD_NAME": "query", "ENTITY_NAME": "Account"},
        ]
        with patch("audit.large_queries.parse_logs", return_value=iter(logs)):
            result = collect_large_queries(mock_sf)
        assert result == set()


class TestHourlyObserveUserQueryingLargeRecords:
    def test_calls_collect_and_report(self, mock_sf):
        from audit.large_queries import hourly_observe_user_querying_large_records
        with patch("audit.large_queries.collect_large_queries", return_value=set()) as m_collect, \
             patch("audit.large_queries.report_large_queries") as m_report:
            hourly_observe_user_querying_large_records(mock_sf)
        m_collect.assert_called_once()
        m_report.assert_called_once_with(set())

    def test_handles_exception(self, mock_sf):
        from audit.large_queries import hourly_observe_user_querying_large_records
        with patch("audit.large_queries.collect_large_queries", side_effect=RuntimeError("fail")):
            hourly_observe_user_querying_large_records(mock_sf)  # Should not raise
