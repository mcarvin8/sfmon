"""Unit tests for tech_debt/queues_groups.py"""

import pytest
from unittest.mock import MagicMock, patch


class TestTotalQueuesPerObject:
    def test_sets_gauge_per_sobject(self, mock_sf):
        from tech_debt.queues_groups import total_queues_per_object
        records = [
            {"SobjectType": "Case", "expr0": "5"},
            {"SobjectType": "Lead", "expr0": "2"},
        ]
        mock_gauge = MagicMock()
        with patch("tech_debt.queues_groups.query_records_all", return_value=records), \
             patch("tech_debt.queues_groups.total_queues_per_object_gauge", mock_gauge):
            total_queues_per_object(mock_sf)
        assert mock_gauge.labels.call_count == 2
        mock_gauge.clear.assert_called_once()

    def test_empty_results(self, mock_sf):
        from tech_debt.queues_groups import total_queues_per_object
        mock_gauge = MagicMock()
        with patch("tech_debt.queues_groups.query_records_all", return_value=[]), \
             patch("tech_debt.queues_groups.total_queues_per_object_gauge", mock_gauge):
            total_queues_per_object(mock_sf)
        mock_gauge.labels.assert_not_called()

    def test_handles_exception(self, mock_sf):
        from tech_debt.queues_groups import total_queues_per_object
        with patch("tech_debt.queues_groups.query_records_all", side_effect=RuntimeError("fail")):
            total_queues_per_object(mock_sf)  # Should not raise


class TestQueuesWithNoMembers:
    def test_sets_gauge_per_queue(self, mock_sf):
        from tech_debt.queues_groups import queues_with_no_members
        records = [{"Id": "q01", "Name": "EmptyQueue"}]
        mock_gauge = MagicMock()
        with patch("tech_debt.queues_groups.query_records_all", return_value=records), \
             patch("tech_debt.queues_groups.queues_with_no_members_gauge", mock_gauge):
            queues_with_no_members(mock_sf)
        mock_gauge.labels.assert_called_once_with(queue_id="q01", queue_name="EmptyQueue")
        mock_gauge.labels().set.assert_called_once_with(1)

    def test_handles_exception(self, mock_sf):
        from tech_debt.queues_groups import queues_with_no_members
        with patch("tech_debt.queues_groups.query_records_all", side_effect=RuntimeError("fail")):
            queues_with_no_members(mock_sf)  # Should not raise


class TestQueuesWithZeroOpenCases:
    def test_sets_gauge_per_queue(self, mock_sf):
        from tech_debt.queues_groups import queues_with_zero_open_cases
        records = [{"Id": "q01", "Name": "IdleQueue"}]
        mock_gauge = MagicMock()
        with patch("tech_debt.queues_groups.query_records_all", return_value=records), \
             patch("tech_debt.queues_groups.queues_with_zero_open_cases_gauge", mock_gauge):
            queues_with_zero_open_cases(mock_sf)
        mock_gauge.labels.assert_called_once_with(queue_id="q01", queue_name="IdleQueue")
        mock_gauge.labels().set.assert_called_once_with(1)

    def test_handles_exception(self, mock_sf):
        from tech_debt.queues_groups import queues_with_zero_open_cases
        with patch("tech_debt.queues_groups.query_records_all", side_effect=RuntimeError("fail")):
            queues_with_zero_open_cases(mock_sf)  # Should not raise


class TestPublicGroupsWithNoMembers:
    def test_sets_gauge_per_group(self, mock_sf):
        from tech_debt.queues_groups import public_groups_with_no_members
        records = [{"Id": "g01", "Name": "EmptyGroup"}]
        mock_gauge = MagicMock()
        with patch("tech_debt.queues_groups.query_records_all", return_value=records), \
             patch("tech_debt.queues_groups.public_groups_with_no_members_gauge", mock_gauge):
            public_groups_with_no_members(mock_sf)
        mock_gauge.labels.assert_called_once_with(group_id="g01", group_name="EmptyGroup")
        mock_gauge.labels().set.assert_called_once_with(1)

    def test_handles_exception(self, mock_sf):
        from tech_debt.queues_groups import public_groups_with_no_members
        with patch("tech_debt.queues_groups.query_records_all", side_effect=RuntimeError("fail")):
            public_groups_with_no_members(mock_sf)  # Should not raise
