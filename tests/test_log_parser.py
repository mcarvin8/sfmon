"""Unit tests for log_parser.py"""

import csv
import io
import pytest
import requests
from unittest.mock import MagicMock, patch


class TestFetchEventLogCsvReader:
    def _make_sf(self, base_url="https://org.my.salesforce.com/services/data/v59.0", session_id="TOKEN"):
        sf = MagicMock()
        sf.base_url = base_url
        sf.session_id = session_id
        return sf

    def test_returns_dict_reader_on_success(self):
        from log_parser import fetch_event_log_csv_reader
        csv_content = "FIELD1,FIELD2\nval1,val2\n"
        mock_resp = MagicMock()
        mock_resp.text = csv_content
        with patch("log_parser.requests.get", return_value=mock_resp):
            result = fetch_event_log_csv_reader(self._make_sf(), "logId123")
        assert result is not None
        assert "FIELD1" in result.fieldnames

    def test_returns_none_for_empty_content(self):
        from log_parser import fetch_event_log_csv_reader
        mock_resp = MagicMock()
        mock_resp.text = ""
        with patch("log_parser.requests.get", return_value=mock_resp):
            result = fetch_event_log_csv_reader(self._make_sf(), "logId123")
        assert result is None

    def test_strips_bom_from_fieldnames(self):
        from log_parser import fetch_event_log_csv_reader
        csv_content = "﻿FIELD1,FIELD2\nval1,val2\n"
        mock_resp = MagicMock()
        mock_resp.text = csv_content
        with patch("log_parser.requests.get", return_value=mock_resp):
            result = fetch_event_log_csv_reader(self._make_sf(), "logId123")
        assert "FIELD1" in result.fieldnames
        assert "﻿FIELD1" not in result.fieldnames

    def test_raises_on_http_error(self):
        from log_parser import fetch_event_log_csv_reader
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("404")
        with patch("log_parser.requests.get", return_value=mock_resp):
            with pytest.raises(requests.HTTPError):
                fetch_event_log_csv_reader(self._make_sf(), "logId123")


class TestParseLogs:
    def _make_sf(self):
        sf = MagicMock()
        sf.base_url = "https://org.salesforce.com"
        sf.session_id = "TOKEN"
        return sf

    def test_returns_none_when_no_records(self):
        from log_parser import parse_logs
        with patch("log_parser.query_records_all", return_value=[]):
            result = parse_logs(self._make_sf(), "SELECT Id FROM EventLogFile")
        assert result is None

    def test_returns_reader_when_records_found(self):
        from log_parser import parse_logs
        records = [{"Id": "elf001"}]
        mock_reader = MagicMock()
        with patch("log_parser.query_records_all", return_value=records), \
             patch("log_parser.fetch_event_log_csv_reader", return_value=mock_reader):
            result = parse_logs(self._make_sf(), "SELECT Id FROM EventLogFile")
        assert result is mock_reader

    def test_returns_none_on_request_exception(self):
        from log_parser import parse_logs
        with patch("log_parser.query_records_all", side_effect=requests.ConnectionError("fail")):
            result = parse_logs(self._make_sf(), "SELECT Id FROM EventLogFile")
        assert result is None

    def test_returns_none_on_generic_exception(self):
        from log_parser import parse_logs
        with patch("log_parser.query_records_all", side_effect=RuntimeError("unexpected")):
            result = parse_logs(self._make_sf(), "SELECT Id FROM EventLogFile")
        assert result is None
