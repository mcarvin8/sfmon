"""Unit tests for query.py – all Salesforce calls are mocked."""

import pytest
from unittest.mock import MagicMock, patch
from simple_salesforce.exceptions import SalesforceExpiredSession, SalesforceMalformedRequest
import requests as requests_lib


@pytest.fixture(autouse=True)
def _import_query():
    """Ensure query module is importable."""
    from sfmon import query    # noqa: F401


class TestQueryRecordsAll:
    def test_returns_records_on_success(self, mock_sf):
        from sfmon.query import query_records_all
        records = [{"Id": "001", "Name": "Test"}]
        mock_sf.query_all.return_value = {"records": records, "done": True}
        result = query_records_all(mock_sf, "SELECT Id FROM Account")
        assert result == records

    def test_returns_empty_when_no_records_key(self, mock_sf):
        from sfmon.query import query_records_all
        mock_sf.query_all.return_value = {"done": True}
        result = query_records_all(mock_sf, "SELECT Id FROM Account")
        assert result == []

    def test_returns_empty_on_timeout(self, mock_sf):
        from sfmon.query import query_records_all
        mock_sf.query_all.side_effect = requests_lib.exceptions.Timeout()
        result = query_records_all(mock_sf, "SELECT Id FROM Account")
        assert result == []

    def test_returns_empty_on_malformed_request(self, mock_sf):
        from sfmon.query import query_records_all
        mock_sf.query_all.side_effect = SalesforceMalformedRequest(
            "https://example.com", 400, "Bad", "MALFORMED"
        )
        result = query_records_all(mock_sf, "SELECT Id FROM Account")
        assert result == []

    def test_returns_empty_on_generic_exception(self, mock_sf):
        from sfmon.query import query_records_all
        mock_sf.query_all.side_effect = RuntimeError("boom")
        result = query_records_all(mock_sf, "SELECT Id FROM Account")
        assert result == []

    def test_expired_session_retries_and_succeeds(self, mock_sf):
        from sfmon.query import query_records_all
        recovered_sf = MagicMock()
        records = [{"Id": "002"}]
        recovered_sf.query_all.return_value = {"records": records}

        mock_sf.query_all.side_effect = SalesforceExpiredSession(
            "https://example.com", 401, "Expired", "EXPIRED"
        )

        with patch("sfmon.query.get_current_org", return_value="prod"),              patch("sfmon.orgs.reconnect", return_value=recovered_sf) as mock_reconnect:
            result = query_records_all(mock_sf, "SELECT Id FROM Account")

        assert result == records
        mock_reconnect.assert_called_once_with("prod", stale=mock_sf)

    def test_expired_session_retry_also_fails(self, mock_sf):
        from sfmon.query import query_records_all
        mock_sf.query_all.side_effect = SalesforceExpiredSession(
            "https://example.com", 401, "Expired", "EXPIRED"
        )

        with patch("sfmon.orgs.reconnect", side_effect=RuntimeError("reauth failed")):
            result = query_records_all(mock_sf, "SELECT Id FROM Account")

        assert result == []

    def test_expired_session_query_fails_after_reconnect(self, mock_sf):
        from sfmon.query import query_records_all
        recovered_sf = MagicMock()
        recovered_sf.query_all.side_effect = RuntimeError("still broken")
        mock_sf.query_all.side_effect = SalesforceExpiredSession(
            "https://example.com", 401, "Expired", "EXPIRED"
        )

        with patch("sfmon.orgs.reconnect", return_value=recovered_sf):
            result = query_records_all(mock_sf, "SELECT Id FROM Account")

        assert result == []


class TestToolingQueryRecordsAll:
    def test_returns_records_on_success(self, mock_sf):
        from sfmon.query import tooling_query_records_all
        records = [{"Id": "001", "Name": "MyClass"}]
        mock_sf.toolingexecute.return_value = {"records": records}
        result = tooling_query_records_all(mock_sf, "SELECT Id FROM ApexClass")
        assert result == records
        mock_sf.toolingexecute.assert_called_once()

    def test_returns_empty_when_no_records_key(self, mock_sf):
        from sfmon.query import tooling_query_records_all
        mock_sf.toolingexecute.return_value = {}
        result = tooling_query_records_all(mock_sf, "SELECT Id FROM ApexClass")
        assert result == []

    def test_returns_empty_on_timeout(self, mock_sf):
        from sfmon.query import tooling_query_records_all
        mock_sf.toolingexecute.side_effect = requests_lib.exceptions.Timeout()
        result = tooling_query_records_all(mock_sf, "SELECT Id FROM ApexClass")
        assert result == []

    def test_returns_empty_on_malformed_request(self, mock_sf):
        from sfmon.query import tooling_query_records_all
        mock_sf.toolingexecute.side_effect = SalesforceMalformedRequest(
            "https://example.com", 400, "Bad", "MALFORMED"
        )
        result = tooling_query_records_all(mock_sf, "SELECT Id FROM ApexClass")
        assert result == []

    def test_returns_empty_on_generic_exception(self, mock_sf):
        from sfmon.query import tooling_query_records_all
        mock_sf.toolingexecute.side_effect = RuntimeError("boom")
        result = tooling_query_records_all(mock_sf, "SELECT Id FROM ApexClass")
        assert result == []

    def test_expired_session_retries_and_succeeds(self, mock_sf):
        from sfmon.query import tooling_query_records_all
        recovered_sf = MagicMock()
        records = [{"Id": "003"}]
        recovered_sf.toolingexecute.return_value = {"records": records}

        mock_sf.toolingexecute.side_effect = SalesforceExpiredSession(
            "https://example.com", 401, "Expired", "EXPIRED"
        )

        with patch("sfmon.query.get_current_org", return_value="prod"),              patch("sfmon.orgs.reconnect", return_value=recovered_sf) as mock_reconnect:
            result = tooling_query_records_all(mock_sf, "SELECT Id FROM ApexClass")

        assert result == records
        mock_reconnect.assert_called_once_with("prod", stale=mock_sf)

    def test_expired_session_retry_also_fails(self, mock_sf):
        from sfmon.query import tooling_query_records_all
        mock_sf.toolingexecute.side_effect = SalesforceExpiredSession(
            "https://example.com", 401, "Expired", "EXPIRED"
        )

        with patch("sfmon.orgs.reconnect", side_effect=RuntimeError("reauth failed")):
            result = tooling_query_records_all(mock_sf, "SELECT Id FROM ApexClass")

        assert result == []

    def test_expired_session_query_fails_after_reconnect(self, mock_sf):
        from sfmon.query import tooling_query_records_all
        recovered_sf = MagicMock()
        recovered_sf.toolingexecute.side_effect = RuntimeError("still broken")
        mock_sf.toolingexecute.side_effect = SalesforceExpiredSession(
            "https://example.com", 401, "Expired", "EXPIRED"
        )

        with patch("sfmon.orgs.reconnect", return_value=recovered_sf):
            result = tooling_query_records_all(mock_sf, "SELECT Id FROM ApexClass")

        assert result == []


class TestGetEventLogFile:
    def _make_sf(self, session_id="OLD"):
        sf = MagicMock()
        sf.base_url = "https://org.my.salesforce.com/services/data/v62.0"
        sf.session_id = session_id
        return sf

    def _resp(self, status_code, text=""):
        resp = MagicMock()
        resp.status_code = status_code
        resp.text = text
        return resp

    def test_downloads_log_file_with_session_token(self):
        from sfmon.query import get_event_log_file
        sf = self._make_sf()
        ok = self._resp(200, "A,B\n1,2")
        with patch("sfmon.query.requests.get", return_value=ok) as mock_get, \
             patch("sfmon.orgs.reconnect") as mock_reconnect:
            result = get_event_log_file(sf, "0AT1")

        assert result is ok
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert args[0] == f"{sf.base_url}/sobjects/EventLogFile/0AT1/LogFile"
        assert kwargs["headers"] == {"Authorization": "Bearer OLD"}
        mock_reconnect.assert_not_called()

    def test_401_reconnects_current_org_and_retries(self):
        from sfmon.query import get_event_log_file
        sf, new_sf = self._make_sf("OLD"), self._make_sf("NEW")
        ok = self._resp(200, "A,B\n1,2")
        with patch("sfmon.query.requests.get", side_effect=[self._resp(401), ok]) as mock_get, \
             patch("sfmon.query.get_current_org", return_value="prod"), \
             patch("sfmon.orgs.reconnect", return_value=new_sf) as mock_reconnect:
            result = get_event_log_file(sf, "0AT1")

        assert result is ok
        mock_reconnect.assert_called_once_with("prod", stale=sf)
        assert mock_get.call_args_list[1].kwargs["headers"] == {"Authorization": "Bearer NEW"}

    def test_401_returns_original_response_when_reconnect_fails(self):
        from sfmon.query import get_event_log_file
        unauthorized = self._resp(401)
        with patch("sfmon.query.requests.get", return_value=unauthorized) as mock_get, \
             patch("sfmon.orgs.reconnect", side_effect=RuntimeError("bad token")):
            result = get_event_log_file(self._make_sf(), "0AT1")

        assert result is unauthorized
        mock_get.assert_called_once()

    def test_non_401_error_is_returned_without_reconnecting(self):
        from sfmon.query import get_event_log_file
        not_found = self._resp(404)
        with patch("sfmon.query.requests.get", return_value=not_found), \
             patch("sfmon.orgs.reconnect") as mock_reconnect:
            result = get_event_log_file(self._make_sf(), "0AT1")

        assert result is not_found
        mock_reconnect.assert_not_called()
