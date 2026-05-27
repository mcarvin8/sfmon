"""Unit tests for tech_debt/security.py"""

import pytest
from unittest.mock import MagicMock, patch


class TestSecurityHealthCheck:
    def _make_record(self, score):
        return {"Id": "hc01", "Score": str(score)}

    def test_excellent_grade(self, mock_sf):
        from tech_debt.security import security_health_check
        mock_gauge = MagicMock()
        with patch("tech_debt.security.tooling_query_records_all", return_value=[self._make_record(95)]), \
             patch("tech_debt.security.security_health_check_gauge", mock_gauge):
            security_health_check(mock_sf)
        mock_gauge.labels.assert_called_once_with(grade="Excellent")
        mock_gauge.labels().set.assert_called_once_with(95)

    def test_very_good_grade(self, mock_sf):
        from tech_debt.security import security_health_check
        mock_gauge = MagicMock()
        with patch("tech_debt.security.tooling_query_records_all", return_value=[self._make_record(85)]), \
             patch("tech_debt.security.security_health_check_gauge", mock_gauge):
            security_health_check(mock_sf)
        mock_gauge.labels.assert_called_once_with(grade="Very Good")

    def test_good_grade(self, mock_sf):
        from tech_debt.security import security_health_check
        mock_gauge = MagicMock()
        with patch("tech_debt.security.tooling_query_records_all", return_value=[self._make_record(75)]), \
             patch("tech_debt.security.security_health_check_gauge", mock_gauge):
            security_health_check(mock_sf)
        mock_gauge.labels.assert_called_once_with(grade="Good")

    def test_poor_grade(self, mock_sf):
        from tech_debt.security import security_health_check
        mock_gauge = MagicMock()
        with patch("tech_debt.security.tooling_query_records_all", return_value=[self._make_record(60)]), \
             patch("tech_debt.security.security_health_check_gauge", mock_gauge):
            security_health_check(mock_sf)
        mock_gauge.labels.assert_called_once_with(grade="Poor")

    def test_very_poor_grade(self, mock_sf):
        from tech_debt.security import security_health_check
        mock_gauge = MagicMock()
        with patch("tech_debt.security.tooling_query_records_all", return_value=[self._make_record(40)]), \
             patch("tech_debt.security.security_health_check_gauge", mock_gauge):
            security_health_check(mock_sf)
        mock_gauge.labels.assert_called_once_with(grade="Very Poor")

    def test_empty_results(self, mock_sf):
        from tech_debt.security import security_health_check
        mock_gauge = MagicMock()
        with patch("tech_debt.security.tooling_query_records_all", return_value=[]), \
             patch("tech_debt.security.security_health_check_gauge", mock_gauge):
            security_health_check(mock_sf)
        mock_gauge.labels.assert_not_called()

    def test_handles_exception(self, mock_sf):
        from tech_debt.security import security_health_check
        with patch("tech_debt.security.tooling_query_records_all", side_effect=RuntimeError("fail")):
            security_health_check(mock_sf)  # Should not raise


class TestSalesforceHealthRisks:
    def _make_risk(self, org_value="enabled", standard_value="disabled"):
        return {
            "Id": "risk01",
            "OrgValue": org_value,
            "RiskType": "CRITICAL",
            "Setting": "PasswordComplexity",
            "SettingGroup": "Password Policies",
            "SettingRiskCategory": "HIGH_RISK",
            "StandardValue": standard_value,
            "StandardValueRaw": standard_value,
        }

    def test_sets_mismatch_status(self, mock_sf):
        from tech_debt.security import salesforce_health_risks
        records = [self._make_risk("enabled", "disabled")]
        mock_gauge = MagicMock()
        with patch("tech_debt.security.tooling_query_records_all", return_value=records), \
             patch("tech_debt.security.salesforce_health_risks_gauge", mock_gauge):
            salesforce_health_risks(mock_sf)
        call_kwargs = mock_gauge.labels.call_args.kwargs
        assert call_kwargs["compliance_status"] == "mismatch"

    def test_sets_match_status(self, mock_sf):
        from tech_debt.security import salesforce_health_risks
        records = [self._make_risk("enabled", "enabled")]
        mock_gauge = MagicMock()
        with patch("tech_debt.security.tooling_query_records_all", return_value=records), \
             patch("tech_debt.security.salesforce_health_risks_gauge", mock_gauge):
            salesforce_health_risks(mock_sf)
        call_kwargs = mock_gauge.labels.call_args.kwargs
        assert call_kwargs["compliance_status"] == "match"

    def test_handles_exception(self, mock_sf):
        from tech_debt.security import salesforce_health_risks
        with patch("tech_debt.security.tooling_query_records_all", side_effect=RuntimeError("fail")):
            salesforce_health_risks(mock_sf)  # Should not raise
