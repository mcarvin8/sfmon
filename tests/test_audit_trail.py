"""Unit tests for audit/audit_trail.py – Salesforce calls are mocked."""

import pytest
from unittest.mock import MagicMock, patch, call


class TestBuildAuditTrailQuery:
    def test_query_contains_setup_audit_trail(self):
        from audit.audit_trail import build_audit_trail_query
        query = build_audit_trail_query()
        assert "SetupAuditTrail" in query
        assert "YESTERDAY" in query
        assert "CreatedDate" in query


class TestExtractRecordData:
    def test_extracts_all_fields(self):
        from audit.audit_trail import extract_record_data
        record = {
            "Action": "activateduser",
            "Section": "Manage Users",
            "CreatedBy": {"Name": "John Doe"},
            "CreatedDate": "2024-01-15T10:00:00.000Z",
            "Display": "Activated user Jane",
            "DelegateUser": None,
        }
        result = extract_record_data(record)
        assert result["action"] == "activateduser"
        assert result["section"] == "Manage Users"
        assert result["user"] == "John Doe"
        assert result["user_group"] in ("Integration User", "Other")
        assert result["created_date"] == "2024-01-15T10:00:00.000Z"
        assert result["display"] == "Activated user Jane"

    def test_handles_missing_created_by(self):
        from audit.audit_trail import extract_record_data
        record = {
            "Action": "someAction",
            "Section": "Unknown",
            "CreatedDate": "2024-01-15",
        }
        result = extract_record_data(record)
        assert result["user"] == "Unknown"

    def test_handles_non_dict_created_by(self):
        from audit.audit_trail import extract_record_data
        record = {
            "Action": "someAction",
            "Section": "Unknown",
            "CreatedBy": "just a string",
        }
        result = extract_record_data(record)
        assert result["user"] == "Unknown"

    def test_missing_optional_fields_use_defaults(self):
        from audit.audit_trail import extract_record_data
        result = extract_record_data({})
        assert result["action"] == "Unknown"
        assert result["section"] == "Unknown"
        assert result["display"] == "Unknown"
        assert result["delegate_user"] == "Unknown"


class TestIsAllowedAction:
    def test_allowed_action_returns_true(self):
        from audit.audit_trail import is_allowed_action
        record = {"Action": "activateduser", "Section": "Manage Users"}
        assert is_allowed_action(record) is True

    def test_allowed_action_case_insensitive(self):
        from audit.audit_trail import is_allowed_action
        record = {"Action": "ACTIVATEDUSER", "Section": "Manage Users"}
        assert is_allowed_action(record) is True

    def test_unknown_action_returns_false(self):
        from audit.audit_trail import is_allowed_action
        record = {"Action": "deletedEverything", "Section": "Manage Users"}
        assert is_allowed_action(record) is False

    def test_unknown_section_returns_false(self):
        from audit.audit_trail import is_allowed_action
        record = {"Action": "anyAction", "Section": "UnknownSection"}
        assert is_allowed_action(record) is False

    def test_empty_section_allowed_action(self):
        from audit.audit_trail import is_allowed_action
        record = {"Action": "createScratchOrg", "Section": ""}
        assert is_allowed_action(record) is True

    def test_empty_section_disallowed_action(self):
        from audit.audit_trail import is_allowed_action
        record = {"Action": "maliciousAction", "Section": ""}
        assert is_allowed_action(record) is False

    def test_perm_set_assign_is_allowed(self):
        from audit.audit_trail import is_allowed_action
        record = {"Action": "PermSetAssign", "Section": "Manage Users"}
        assert is_allowed_action(record) is True


class TestProcessSuspiciousRecords:
    def test_no_records_sets_zero_metric(self):
        from audit.audit_trail import process_suspicious_records
        mock_gauge = MagicMock()
        with patch("audit.audit_trail.suspicious_records_gauge", mock_gauge):
            process_suspicious_records([])
        mock_gauge.labels.assert_called_once()
        mock_gauge.labels().set.assert_called_once_with(0)

    def test_allowed_record_does_not_trigger_metric(self):
        from audit.audit_trail import process_suspicious_records
        records = [{"Action": "activateduser", "Section": "Manage Users"}]
        mock_gauge = MagicMock()
        with patch("audit.audit_trail.suspicious_records_gauge", mock_gauge):
            process_suspicious_records(records)
        # Only the "no suspicious records" default label call should happen
        mock_gauge.labels.assert_called_once()
        mock_gauge.labels().set.assert_called_once_with(0)

    def test_suspicious_record_sets_metric_to_one(self):
        from audit.audit_trail import process_suspicious_records
        records = [
            {
                "Action": "dangerousChange",
                "Section": "SomeSection",
                "CreatedBy": {"Name": "Hacker"},
                "CreatedDate": "2024-01-15",
                "Display": "Bad stuff",
                "DelegateUser": None,
            }
        ]
        mock_gauge = MagicMock()
        with patch("audit.audit_trail.suspicious_records_gauge", mock_gauge):
            process_suspicious_records(records)
        mock_gauge.labels.assert_called_once()
        mock_gauge.labels().set.assert_called_once_with(1)


class TestExposeSuspiciousRecords:
    def test_calls_query_and_processes(self, mock_sf):
        from audit.audit_trail import expose_suspicious_records
        mock_records = [{"Action": "activateduser", "Section": "Manage Users"}]
        mock_gauge = MagicMock()

        with patch("audit.audit_trail.query_records_all", return_value=mock_records), \
             patch("audit.audit_trail.suspicious_records_gauge", mock_gauge):
            expose_suspicious_records(mock_sf)

        mock_gauge.clear.assert_called_once()

    def test_handles_exception_gracefully(self, mock_sf):
        from audit.audit_trail import expose_suspicious_records
        mock_gauge = MagicMock()

        with patch("audit.audit_trail.query_records_all", side_effect=RuntimeError("fail")), \
             patch("audit.audit_trail.suspicious_records_gauge", mock_gauge):
            # Should not raise
            expose_suspicious_records(mock_sf)
