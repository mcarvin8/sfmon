"""Unit tests for query.py – all Salesforce calls are mocked."""

import pytest
from unittest.mock import MagicMock, patch
from simple_salesforce.exceptions import SalesforceExpiredSession, SalesforceMalformedRequest
import requests as requests_lib


@pytest.fixture(autouse=True)
def _import_query():
    """Ensure query module is importable."""
    import query  # noqa: F401


class TestQueryRecordsAll:
    def test_returns_records_on_success(self, mock_sf):
        from query import query_records_all
        records = [{"Id": "001", "Name": "Test"}]
        mock_sf.query_all.return_value = {"records": records, "done": True}
        result = query_records_all(mock_sf, "SELECT Id FROM Account")
        assert result == records

    def test_returns_empty_when_no_records_key(self, mock_sf):
        from query import query_records_all
        mock_sf.query_all.return_value = {"done": True}
        result = query_records_all(mock_sf, "SELECT Id FROM Account")
        assert result == []

    def test_returns_empty_on_timeout(self, mock_sf):
        from query import query_records_all
        mock_sf.query_all.side_effect = requests_lib.exceptions.Timeout()
        result = query_records_all(mock_sf, "SELECT Id FROM Account")
        assert result == []

    def test_returns_empty_on_malformed_request(self, mock_sf):
        from query import query_records_all
        mock_sf.query_all.side_effect = SalesforceMalformedRequest(
            "https://example.com", 400, "Bad", "MALFORMED"
        )
        result = query_records_all(mock_sf, "SELECT Id FROM Account")
        assert result == []

    def test_returns_empty_on_generic_exception(self, mock_sf):
        from query import query_records_all
        mock_sf.query_all.side_effect = RuntimeError("boom")
        result = query_records_all(mock_sf, "SELECT Id FROM Account")
        assert result == []

    def test_expired_session_retries_and_succeeds(self, mock_sf):
        from query import query_records_all
        recovered_sf = MagicMock()
        records = [{"Id": "002"}]
        recovered_sf.query_all.return_value = {"records": records}

        mock_sf.query_all.side_effect = SalesforceExpiredSession(
            "https://example.com", 401, "Expired", "EXPIRED"
        )

        mock_module = MagicMock()
        mock_module.reauthenticate_connections = MagicMock()
        mock_module.sf_connection = recovered_sf

        with patch.dict("sys.modules", {"salesforce_monitoring": mock_module}):
            result = query_records_all(mock_sf, "SELECT Id FROM Account")

        assert result == records

    def test_expired_session_retry_also_fails(self, mock_sf):
        from query import query_records_all
        mock_sf.query_all.side_effect = SalesforceExpiredSession(
            "https://example.com", 401, "Expired", "EXPIRED"
        )

        mock_module = MagicMock()
        mock_module.reauthenticate_connections.side_effect = RuntimeError("reauth failed")
        mock_module.sf_connection = None

        with patch.dict("sys.modules", {"salesforce_monitoring": mock_module}):
            result = query_records_all(mock_sf, "SELECT Id FROM Account")

        assert result == []


class TestToolingQueryRecordsAll:
    def test_returns_records_on_success(self, mock_sf):
        from query import tooling_query_records_all
        records = [{"Id": "001", "Name": "MyClass"}]
        mock_sf.toolingexecute.return_value = {"records": records}
        result = tooling_query_records_all(mock_sf, "SELECT Id FROM ApexClass")
        assert result == records
        mock_sf.toolingexecute.assert_called_once()

    def test_returns_empty_when_no_records_key(self, mock_sf):
        from query import tooling_query_records_all
        mock_sf.toolingexecute.return_value = {}
        result = tooling_query_records_all(mock_sf, "SELECT Id FROM ApexClass")
        assert result == []

    def test_returns_empty_on_timeout(self, mock_sf):
        from query import tooling_query_records_all
        mock_sf.toolingexecute.side_effect = requests_lib.exceptions.Timeout()
        result = tooling_query_records_all(mock_sf, "SELECT Id FROM ApexClass")
        assert result == []

    def test_returns_empty_on_malformed_request(self, mock_sf):
        from query import tooling_query_records_all
        mock_sf.toolingexecute.side_effect = SalesforceMalformedRequest(
            "https://example.com", 400, "Bad", "MALFORMED"
        )
        result = tooling_query_records_all(mock_sf, "SELECT Id FROM ApexClass")
        assert result == []

    def test_returns_empty_on_generic_exception(self, mock_sf):
        from query import tooling_query_records_all
        mock_sf.toolingexecute.side_effect = RuntimeError("boom")
        result = tooling_query_records_all(mock_sf, "SELECT Id FROM ApexClass")
        assert result == []

    def test_expired_session_retries_and_succeeds(self, mock_sf):
        from query import tooling_query_records_all
        recovered_sf = MagicMock()
        records = [{"Id": "003"}]
        recovered_sf.toolingexecute.return_value = {"records": records}

        mock_sf.toolingexecute.side_effect = SalesforceExpiredSession(
            "https://example.com", 401, "Expired", "EXPIRED"
        )

        mock_module = MagicMock()
        mock_module.reauthenticate_connections = MagicMock()
        mock_module.sf_connection = recovered_sf

        with patch.dict("sys.modules", {"salesforce_monitoring": mock_module}):
            result = tooling_query_records_all(mock_sf, "SELECT Id FROM ApexClass")

        assert result == records

    def test_expired_session_retry_also_fails(self, mock_sf):
        from query import tooling_query_records_all
        mock_sf.toolingexecute.side_effect = SalesforceExpiredSession(
            "https://example.com", 401, "Expired", "EXPIRED"
        )

        mock_module = MagicMock()
        mock_module.reauthenticate_connections.side_effect = RuntimeError("reauth failed")
        mock_module.sf_connection = None

        with patch.dict("sys.modules", {"salesforce_monitoring": mock_module}):
            result = tooling_query_records_all(mock_sf, "SELECT Id FROM ApexClass")

        assert result == []
