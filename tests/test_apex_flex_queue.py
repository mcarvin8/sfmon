"""Unit tests for ops/apex_flex_queue.py"""

import pytest
from unittest.mock import MagicMock, patch


class TestMonitorApexFlexQueue:
    def test_sets_gauge_per_record(self, mock_sf):
        from ops.apex_flex_queue import monitor_apex_flex_queue
        records = [
            {"Id": "job1", "ApexClassId": "cls1"},
            {"Id": "job2", "ApexClassId": "cls2"},
        ]
        mock_gauge = MagicMock()
        with patch("ops.apex_flex_queue.query_records_all", return_value=records), \
             patch("ops.apex_flex_queue.apex_flex_queue", mock_gauge):
            monitor_apex_flex_queue(mock_sf)
        assert mock_gauge.labels.call_count == 2
        mock_gauge.clear.assert_called_once()

    def test_empty_results_emits_zero_series(self, mock_sf):
        from ops.apex_flex_queue import monitor_apex_flex_queue
        mock_gauge = MagicMock()
        with patch("ops.apex_flex_queue.query_records_all", return_value=[]), \
             patch("ops.apex_flex_queue.apex_flex_queue", mock_gauge):
            monitor_apex_flex_queue(mock_sf)
        mock_gauge.labels.assert_called_once_with(id="none", ApexClassId="none")
        mock_gauge.labels().set.assert_called_once_with(0)

    def test_handles_exception(self, mock_sf):
        from ops.apex_flex_queue import monitor_apex_flex_queue
        with patch("ops.apex_flex_queue.query_records_all", side_effect=RuntimeError("fail")):
            monitor_apex_flex_queue(mock_sf)  # Should not raise
