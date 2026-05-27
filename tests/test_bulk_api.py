"""Unit tests for ops/bulk_api.py"""

import csv
import io
from collections import defaultdict
from unittest.mock import MagicMock, patch

import pytest


def make_csv_reader(headers, rows):
    """Build a csv.DictReader from lists."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=headers)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    buf.seek(0)
    return csv.DictReader(buf)


class TestSafeInt:
    def test_converts_string_int(self):
        from ops.bulk_api import safe_int
        assert safe_int("42") == 42

    def test_converts_float_string(self):
        from ops.bulk_api import safe_int
        assert safe_int("3.9") == 3

    def test_handles_none(self):
        from ops.bulk_api import safe_int
        assert safe_int(None) == 0

    def test_handles_empty_string(self):
        from ops.bulk_api import safe_int
        assert safe_int("") == 0

    def test_handles_invalid(self):
        from ops.bulk_api import safe_int
        assert safe_int("abc") == 0

    def test_handles_comma_separated(self):
        from ops.bulk_api import safe_int
        assert safe_int("1,000") == 1000

    def test_handles_integer(self):
        from ops.bulk_api import safe_int
        assert safe_int(7) == 7

    def test_handles_whitespace(self):
        from ops.bulk_api import safe_int
        assert safe_int("  5  ") == 5


class TestIntFromRow:
    def test_first_key_found(self):
        from ops.bulk_api import int_from_row
        row = {"ROWS_PROCESSED": "10", "OTHER": "20"}
        assert int_from_row(row, ("ROWS_PROCESSED",)) == 10

    def test_falls_through_to_second_key(self):
        from ops.bulk_api import int_from_row
        row = {"NUMBER_FAILURES": "5"}
        assert int_from_row(row, ("ROWS_PROCESSED", "NUMBER_FAILURES")) == 5

    def test_skips_blank_string(self):
        from ops.bulk_api import int_from_row
        row = {"K1": "   ", "K2": "7"}
        assert int_from_row(row, ("K1", "K2")) == 7

    def test_skips_none_value(self):
        from ops.bulk_api import int_from_row
        row = {"K1": None, "K2": "3"}
        assert int_from_row(row, ("K1", "K2")) == 3

    def test_returns_zero_when_no_key_matches(self):
        from ops.bulk_api import int_from_row
        row = {"OTHER": "99"}
        assert int_from_row(row, ("ROWS_PROCESSED",)) == 0


class TestIsValidEntity:
    def test_valid_entity(self):
        from ops.bulk_api import is_valid_entity
        assert is_valid_entity({"ENTITY_TYPE": "Account"}) is True

    def test_none_entity(self):
        from ops.bulk_api import is_valid_entity
        assert not is_valid_entity({"ENTITY_TYPE": None})

    def test_empty_entity(self):
        from ops.bulk_api import is_valid_entity
        assert not is_valid_entity({"ENTITY_TYPE": ""})

    def test_none_string_entity(self):
        from ops.bulk_api import is_valid_entity
        assert not is_valid_entity({"ENTITY_TYPE": "none"})

    def test_none_string_case_insensitive(self):
        from ops.bulk_api import is_valid_entity
        assert not is_valid_entity({"ENTITY_TYPE": "NONE"})

    def test_missing_entity_key(self):
        from ops.bulk_api import is_valid_entity
        assert not is_valid_entity({})


class TestNormalizeElfHeader:
    def test_uppercase(self):
        from ops.bulk_api import _normalize_elf_header
        assert _normalize_elf_header("rows_processed") == "ROWS_PROCESSED"

    def test_strips_bom(self):
        from ops.bulk_api import _normalize_elf_header
        assert _normalize_elf_header("﻿FIELD") == "FIELD"

    def test_replaces_spaces(self):
        from ops.bulk_api import _normalize_elf_header
        assert _normalize_elf_header("rows processed") == "ROWS_PROCESSED"

    def test_empty_string(self):
        from ops.bulk_api import _normalize_elf_header
        assert _normalize_elf_header("") == ""

    def test_none(self):
        from ops.bulk_api import _normalize_elf_header
        assert _normalize_elf_header(None) == ""


class TestResolveElfColumn:
    def test_finds_exact_match(self):
        from ops.bulk_api import _resolve_elf_column
        result = _resolve_elf_column(["ROWS_PROCESSED", "NUMBER_FAILURES"], ("ROWS_PROCESSED",))
        assert result == "ROWS_PROCESSED"

    def test_returns_first_candidate(self):
        from ops.bulk_api import _resolve_elf_column
        result = _resolve_elf_column(["RECORDS_FAILED", "NUMBER_FAILURES"], ("RECORDS_FAILED", "NUMBER_FAILURES"))
        assert result == "RECORDS_FAILED"

    def test_returns_none_when_no_match(self):
        from ops.bulk_api import _resolve_elf_column
        result = _resolve_elf_column(["OTHER_FIELD"], ("ROWS_PROCESSED",))
        assert result is None

    def test_empty_fieldnames(self):
        from ops.bulk_api import _resolve_elf_column
        result = _resolve_elf_column([], ("ROWS_PROCESSED",))
        assert result is None

    def test_none_fieldnames(self):
        from ops.bulk_api import _resolve_elf_column
        result = _resolve_elf_column(None, ("ROWS_PROCESSED",))
        assert result is None


class TestResolveElfColumnFuzzy:
    def test_finds_substring_match(self):
        from ops.bulk_api import _resolve_elf_column_fuzzy
        result = _resolve_elf_column_fuzzy(["TOTAL_ROWS_COUNT"], ("ROWS",))
        assert result == "TOTAL_ROWS_COUNT"

    def test_returns_none_when_no_match(self):
        from ops.bulk_api import _resolve_elf_column_fuzzy
        result = _resolve_elf_column_fuzzy(["ENTITY_TYPE"], ("ROWS",))
        assert result is None

    def test_empty_fieldnames(self):
        from ops.bulk_api import _resolve_elf_column_fuzzy
        result = _resolve_elf_column_fuzzy([], ("ROWS",))
        assert result is None


class TestReportBatchCounts:
    def test_calls_metric_per_key(self):
        from ops.bulk_api import report_batch_counts
        batch_counts = {("job1", "user1", "Account"): 3}
        failed = defaultdict(int, {("job1", "user1", "Account"): 1})
        processed = defaultdict(int, {("job1", "user1", "Account"): 100})
        mock_metric = MagicMock()
        report_batch_counts(batch_counts, failed, processed, mock_metric)
        mock_metric.labels.assert_called_once_with(
            job_id="job1", user_id="user1", entity_type="Account",
            total_records_failed=1, total_records_processed=100,
        )
        mock_metric.labels().set.assert_called_once_with(3)

    def test_empty_counts(self):
        from ops.bulk_api import report_batch_counts
        mock_metric = MagicMock()
        report_batch_counts({}, defaultdict(int), defaultdict(int), mock_metric)
        mock_metric.labels.assert_not_called()


class TestReportEntityCounts:
    def test_calls_metric_per_key(self):
        from ops.bulk_api import report_entity_counts
        entity_counts = {("user1", "insert", "Contact"): 5}
        mock_metric = MagicMock()
        report_entity_counts(entity_counts, mock_metric)
        mock_metric.labels.assert_called_once_with(
            user_id="user1", operation_type="insert", entity_type="Contact"
        )
        mock_metric.labels().set.assert_called_once_with(5)

    def test_empty_counts(self):
        from ops.bulk_api import report_entity_counts
        mock_metric = MagicMock()
        report_entity_counts({}, mock_metric)
        mock_metric.labels.assert_not_called()


class TestProcessBulkApiLogs:
    def _make_bulk1_reader(self):
        headers = ["JOB_ID", "USER_ID", "ENTITY_TYPE", "OPERATION_TYPE",
                   "ROWS_PROCESSED", "NUMBER_FAILURES"]
        rows = [
            {"JOB_ID": "j1", "USER_ID": "u1", "ENTITY_TYPE": "Account",
             "OPERATION_TYPE": "insert", "ROWS_PROCESSED": "100", "NUMBER_FAILURES": "0"},
            {"JOB_ID": "j1", "USER_ID": "u1", "ENTITY_TYPE": "Account",
             "OPERATION_TYPE": "insert", "ROWS_PROCESSED": "50", "NUMBER_FAILURES": "2"},
        ]
        return make_csv_reader(headers, rows)

    def test_processes_bulk_api1_logs(self):
        from ops.bulk_api import process_bulk_api_logs
        reader = self._make_bulk1_reader()
        mock_batch = MagicMock()
        mock_entity = MagicMock()
        process_bulk_api_logs(
            reader, mock_batch, mock_entity,
            event_type="BulkAPI",
            processed_keys=("ROWS_PROCESSED",),
            failed_keys=("NUMBER_FAILURES",),
        )
        mock_batch.labels.assert_called_once()
        mock_entity.labels.assert_called_once()

    def test_handles_none_logs(self):
        from ops.bulk_api import process_bulk_api_logs
        mock_batch = MagicMock()
        mock_entity = MagicMock()
        process_bulk_api_logs(None, mock_batch, mock_entity)
        mock_batch.clear.assert_not_called()

    def test_skips_invalid_entity(self):
        from ops.bulk_api import process_bulk_api_logs
        headers = ["JOB_ID", "USER_ID", "ENTITY_TYPE", "OPERATION_TYPE",
                   "ROWS_PROCESSED", "NUMBER_FAILURES"]
        rows = [
            {"JOB_ID": "j1", "USER_ID": "u1", "ENTITY_TYPE": "none",
             "OPERATION_TYPE": "insert", "ROWS_PROCESSED": "10", "NUMBER_FAILURES": "0"},
        ]
        reader = make_csv_reader(headers, rows)
        mock_batch = MagicMock()
        mock_entity = MagicMock()
        process_bulk_api_logs(reader, mock_batch, mock_entity, event_type="BulkAPI")
        mock_batch.labels.assert_not_called()


class TestRunBulkLogAnalysis:
    def test_returns_early_when_no_rows(self, mock_sf):
        from ops.bulk_api import _run_bulk_log_analysis
        mock_batch = MagicMock()
        mock_entity = MagicMock()
        with patch("ops.bulk_api.query_records_all", return_value=[]), \
             patch("ops.bulk_api.fetch_event_log_csv_reader") as m_fetch:
            _run_bulk_log_analysis(
                mock_sf, "BulkAPI", "Hourly", mock_batch, mock_entity, "Bulk API 1.0"
            )
        m_fetch.assert_not_called()

    def test_processes_rows_when_found(self, mock_sf):
        from ops.bulk_api import _run_bulk_log_analysis
        rows = [{"Id": "elf01", "LogFileFieldNames": "JOB_ID,USER_ID"}]
        headers = ["JOB_ID", "USER_ID", "ENTITY_TYPE", "OPERATION_TYPE",
                   "ROWS_PROCESSED", "NUMBER_FAILURES"]
        data = [{"JOB_ID": "j1", "USER_ID": "u1", "ENTITY_TYPE": "Account",
                 "OPERATION_TYPE": "insert", "ROWS_PROCESSED": "10", "NUMBER_FAILURES": "0"}]
        reader = make_csv_reader(headers, data)
        mock_batch = MagicMock()
        mock_entity = MagicMock()
        with patch("ops.bulk_api.query_records_all", return_value=rows), \
             patch("ops.bulk_api.fetch_event_log_csv_reader", return_value=reader), \
             patch("ops.bulk_api.process_bulk_api_logs") as m_process:
            _run_bulk_log_analysis(
                mock_sf, "BulkAPI", "Hourly", mock_batch, mock_entity, "Bulk API 1.0"
            )
        m_process.assert_called_once()

    def test_handles_exception(self, mock_sf):
        from ops.bulk_api import _run_bulk_log_analysis
        mock_batch = MagicMock()
        mock_entity = MagicMock()
        with patch("ops.bulk_api.query_records_all", side_effect=RuntimeError("fail")):
            _run_bulk_log_analysis(
                mock_sf, "BulkAPI", "Hourly", mock_batch, mock_entity, "Bulk API 1.0"
            )  # Should not raise


class TestDailyAndHourlyAnalyseBulkApi:
    def test_daily_calls_run_twice(self, mock_sf):
        from ops.bulk_api import daily_analyse_bulk_api
        with patch("ops.bulk_api._run_bulk_log_analysis") as m_run:
            daily_analyse_bulk_api(mock_sf)
        assert m_run.call_count == 2

    def test_hourly_calls_run_twice(self, mock_sf):
        from ops.bulk_api import hourly_analyse_bulk_api
        with patch("ops.bulk_api._run_bulk_log_analysis") as m_run:
            hourly_analyse_bulk_api(mock_sf)
        assert m_run.call_count == 2


class TestProcessBulkApi2Logs:
    def _make_bulk2_reader(self):
        headers = ["JOB_ID", "USER_ID", "ENTITY_TYPE", "OPERATION_TYPE",
                   "RECORDS_PROCESSED", "RECORDS_FAILED"]
        rows = [
            {"JOB_ID": "j1", "USER_ID": "u1", "ENTITY_TYPE": "Contact",
             "OPERATION_TYPE": "insert", "RECORDS_PROCESSED": "200", "RECORDS_FAILED": "0"},
        ]
        return make_csv_reader(headers, rows)

    def test_processes_bulk_api2_logs(self):
        from ops.bulk_api import process_bulk_api_logs
        reader = self._make_bulk2_reader()
        mock_batch = MagicMock()
        mock_entity = MagicMock()
        process_bulk_api_logs(
            reader, mock_batch, mock_entity,
            event_type="BulkAPI2",
            processed_keys=(),
            failed_keys=(),
        )
        mock_batch.labels.assert_called_once()

    def test_bulk_api2_logs_unknown_headers_infers_column(self):
        from ops.bulk_api import process_bulk_api_logs
        headers = ["JOB_ID", "USER_ID", "ENTITY_TYPE", "OPERATION_TYPE",
                   "MY_ROW_COUNT", "MY_FAIL_COUNT"]
        rows = [
            {"JOB_ID": "j1", "USER_ID": "u1", "ENTITY_TYPE": "Lead",
             "OPERATION_TYPE": "update", "MY_ROW_COUNT": "50", "MY_FAIL_COUNT": "5"},
        ]
        reader = make_csv_reader(headers, rows)
        mock_batch = MagicMock()
        mock_entity = MagicMock()
        # Should not crash even with unknown headers
        process_bulk_api_logs(
            reader, mock_batch, mock_entity,
            event_type="BulkAPI2",
            processed_keys=(),
            failed_keys=(),
        )
