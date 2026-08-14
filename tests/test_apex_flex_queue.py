"""Unit tests for ops/apex_flex_queue.py"""

import pytest
from unittest.mock import MagicMock, patch


class TestMonitorApexFlexQueue:
    def test_sets_gauge_per_record(self, mock_sf):
        from sfmon.ops.apex_flex_queue import monitor_apex_flex_queue
        records = [
            {"Id": "job1", "ApexClassId": "cls1"},
            {"Id": "job2", "ApexClassId": "cls2"},
        ]
        mock_gauge = MagicMock()
        with patch("sfmon.ops.apex_flex_queue.query_records_all", return_value=records), \
             patch("sfmon.ops.apex_flex_queue.apex_flex_queue", mock_gauge):
            monitor_apex_flex_queue(mock_sf)
        assert mock_gauge.labels.call_count == 2
        mock_gauge.clear.assert_called_once()

    def test_empty_results_emits_zero_series(self, mock_sf):
        from sfmon.ops.apex_flex_queue import monitor_apex_flex_queue
        mock_gauge = MagicMock()
        with patch("sfmon.ops.apex_flex_queue.query_records_all", return_value=[]), \
             patch("sfmon.ops.apex_flex_queue.apex_flex_queue", mock_gauge):
            monitor_apex_flex_queue(mock_sf)
        mock_gauge.labels.assert_called_once_with(id="none", ApexClassId="none")
        mock_gauge.labels().set.assert_called_once_with(0)

    def test_handles_exception(self, mock_sf):
        from sfmon.ops.apex_flex_queue import monitor_apex_flex_queue
        with patch("sfmon.ops.apex_flex_queue.query_records_all", side_effect=RuntimeError("fail")):
            monitor_apex_flex_queue(mock_sf)  # Should not raise

    def test_syncs_empty_alerts_below_threshold(self, mock_sf):
        from sfmon.ops.apex_flex_queue import monitor_apex_flex_queue
        records = [{"Id": f"job{i}", "ApexClassId": "cls1"} for i in range(10)]
        with patch("sfmon.ops.apex_flex_queue.query_records_all", return_value=records), \
             patch("sfmon.ops.apex_flex_queue.apex_flex_queue"), \
             patch("sfmon.ops.apex_flex_queue.sync_alerts") as mock_sync:
            monitor_apex_flex_queue(mock_sf)
        mock_sync.assert_called_once_with("apex_flex_queue", {})

    def test_syncs_warning_alert_at_default_threshold(self, mock_sf):
        from sfmon.ops.apex_flex_queue import monitor_apex_flex_queue
        records = [{"Id": f"job{i}", "ApexClassId": "cls1"} for i in range(85)]  # 85%
        with patch("sfmon.ops.apex_flex_queue.query_records_all", return_value=records), \
             patch("sfmon.ops.apex_flex_queue.apex_flex_queue"), \
             patch("sfmon.ops.apex_flex_queue.sync_alerts") as mock_sync:
            monitor_apex_flex_queue(mock_sf)
        category, breached = mock_sync.call_args.args
        assert category == "apex_flex_queue"
        assert set(breached) == {"apex_flex_queue"}
        assert breached["apex_flex_queue"]["severity"] == "warning"
        assert "85/100" in breached["apex_flex_queue"]["title"]

    def test_syncs_critical_alert_at_hard_cap(self, mock_sf):
        from sfmon.ops.apex_flex_queue import monitor_apex_flex_queue
        records = [{"Id": f"job{i}", "ApexClassId": "cls1"} for i in range(100)]
        with patch("sfmon.ops.apex_flex_queue.query_records_all", return_value=records), \
             patch("sfmon.ops.apex_flex_queue.apex_flex_queue"), \
             patch("sfmon.ops.apex_flex_queue.sync_alerts") as mock_sync:
            monitor_apex_flex_queue(mock_sf)
        _, breached = mock_sync.call_args.args
        assert breached["apex_flex_queue"]["severity"] == "critical"

    def test_custom_limit_and_threshold(self, mock_sf):
        import sfmon.ops.apex_flex_queue as flex_queue
        records = [{"Id": f"job{i}", "ApexClassId": "cls1"} for i in range(6)]  # 60% of 10
        with patch.object(flex_queue, "FLEX_QUEUE_LIMIT", 10), \
             patch.object(flex_queue, "FLEX_QUEUE_ALERT_THRESHOLD_PERCENT", 50), \
             patch.object(flex_queue, "query_records_all", return_value=records), \
             patch.object(flex_queue, "apex_flex_queue"), \
             patch.object(flex_queue, "sync_alerts") as mock_sync:
            flex_queue.monitor_apex_flex_queue(mock_sf)
        _, breached = mock_sync.call_args.args
        assert set(breached) == {"apex_flex_queue"}
        assert breached["apex_flex_queue"]["severity"] == "warning"
