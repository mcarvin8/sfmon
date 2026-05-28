"""Unit tests for core/overall_sf_org.py – SF and requests are mocked."""

import pytest
import responses as responses_lib
from unittest.mock import MagicMock, patch


TRUST_API = "https://api.status.salesforce.com"


class TestMonitorSalesforceLimits:
    def test_sets_gauge_for_each_limit(self, mock_sf):
        from core.overall_sf_org import monitor_salesforce_limits
        mock_sf.limits.return_value = {
            "DailyApiRequests": {"Max": 15000, "Remaining": 14000},
            "DataStorageMB": {"Max": 5120, "Remaining": 4096},
        }
        mock_gauge = MagicMock()
        with patch("core.overall_sf_org.api_usage_percentage_gauge", mock_gauge):
            monitor_salesforce_limits(mock_sf)
        assert mock_gauge.labels.call_count == 2

    def test_skips_zero_max_limit(self, mock_sf):
        from core.overall_sf_org import monitor_salesforce_limits
        mock_sf.limits.return_value = {
            "ZeroLimit": {"Max": 0, "Remaining": 0},
        }
        mock_gauge = MagicMock()
        with patch("core.overall_sf_org.api_usage_percentage_gauge", mock_gauge):
            monitor_salesforce_limits(mock_sf)
        mock_gauge.labels.assert_not_called()

    def test_handles_exception_gracefully(self, mock_sf):
        from core.overall_sf_org import monitor_salesforce_limits
        mock_sf.limits.side_effect = RuntimeError("API down")
        mock_gauge = MagicMock()
        with patch("core.overall_sf_org.api_usage_percentage_gauge", mock_gauge):
            monitor_salesforce_limits(mock_sf)  # Should not raise

    def test_usage_percentage_calculation(self, mock_sf):
        from core.overall_sf_org import monitor_salesforce_limits
        mock_sf.limits.return_value = {
            "DailyApiRequests": {"Max": 1000, "Remaining": 750},
        }
        captured = {}
        mock_gauge = MagicMock()
        mock_gauge.labels.return_value.set.side_effect = lambda v: captured.update({"pct": v})
        with patch("core.overall_sf_org.api_usage_percentage_gauge", mock_gauge):
            monitor_salesforce_limits(mock_sf)
        assert captured["pct"] == pytest.approx(25.0)


class TestGetSalesforceLicenses:
    def test_user_licenses_processed(self, mock_sf):
        from core.overall_sf_org import get_salesforce_licenses
        user_lic = [{"Name": "Salesforce", "Status": "Active", "TotalLicenses": 100, "UsedLicenses": 40}]
        perm_lic = []
        usage_lic = []

        with patch("core.overall_sf_org.query_records_all", side_effect=[user_lic, perm_lic, usage_lic]), \
             patch("core.overall_sf_org.total_user_licenses_gauge") as m_total, \
             patch("core.overall_sf_org.used_user_licenses_gauge") as m_used, \
             patch("core.overall_sf_org.percent_user_licenses_used_gauge") as m_pct, \
             patch("core.overall_sf_org.total_permissionset_licenses_gauge"), \
             patch("core.overall_sf_org.used_permissionset_licenses_gauge"), \
             patch("core.overall_sf_org.percent_permissionset_used_gauge"), \
             patch("core.overall_sf_org.total_usage_based_entitlements_licenses_gauge"), \
             patch("core.overall_sf_org.used_usage_based_entitlements_licenses_gauge"), \
             patch("core.overall_sf_org.percent_usage_based_entitlements_used_gauge"):
            get_salesforce_licenses(mock_sf)

        m_total.labels.assert_called_once()
        m_used.labels.assert_called_once()
        m_pct.labels.assert_called_once()

    def test_zero_total_licenses_skips_percent(self, mock_sf):
        from core.overall_sf_org import get_salesforce_licenses
        user_lic = [{"Name": "Chatter", "Status": "Active", "TotalLicenses": 0, "UsedLicenses": 0}]

        with patch("core.overall_sf_org.query_records_all", side_effect=[user_lic, [], []]), \
             patch("core.overall_sf_org.total_user_licenses_gauge"), \
             patch("core.overall_sf_org.used_user_licenses_gauge"), \
             patch("core.overall_sf_org.percent_user_licenses_used_gauge") as m_pct, \
             patch("core.overall_sf_org.total_permissionset_licenses_gauge"), \
             patch("core.overall_sf_org.used_permissionset_licenses_gauge"), \
             patch("core.overall_sf_org.percent_permissionset_used_gauge"), \
             patch("core.overall_sf_org.total_usage_based_entitlements_licenses_gauge"), \
             patch("core.overall_sf_org.used_usage_based_entitlements_licenses_gauge"), \
             patch("core.overall_sf_org.percent_usage_based_entitlements_used_gauge"):
            get_salesforce_licenses(mock_sf)

        m_pct.labels.assert_not_called()


class TestFetchPod:
    def test_returns_instance_name(self, mock_sf):
        from core.overall_sf_org import fetch_pod
        records = [{"InstanceName": "NA1"}]
        with patch("core.overall_sf_org.query_records_all", return_value=records):
            result = fetch_pod(mock_sf)
        assert result == "NA1"


class TestGetSalesforceIncidents:
    @responses_lib.activate
    def test_no_incidents_sets_ok_gauge(self):
        from core.overall_sf_org import get_salesforce_incidents
        responses_lib.add(
            responses_lib.GET,
            f"{TRUST_API}/v1/incidents/active",
            json=[],
            status=200,
        )
        mock_gauge = MagicMock()
        with patch("core.overall_sf_org.incident_gauge", mock_gauge):
            get_salesforce_incidents("Production", "NA1")
        mock_gauge.labels.assert_called_once_with(
            environment="Production", pod="NA1", severity="ok", incident_id=None
        )
        mock_gauge.labels().set.assert_called_once_with(0)

    @responses_lib.activate
    def test_matching_incident_sets_gauge_to_one(self):
        from core.overall_sf_org import get_salesforce_incidents
        incidents = [
            {
                "id": "INC-001",
                "instanceKeys": ["NA1", "NA2"],
                "IncidentImpacts": [{"severity": "major"}],
            }
        ]
        responses_lib.add(
            responses_lib.GET,
            f"{TRUST_API}/v1/incidents/active",
            json=incidents,
            status=200,
        )
        mock_gauge = MagicMock()
        with patch("core.overall_sf_org.incident_gauge", mock_gauge):
            get_salesforce_incidents("Production", "NA1")
        mock_gauge.labels.assert_called_once_with(
            environment="Production", pod="NA1", severity="major", incident_id="INC-001"
        )
        mock_gauge.labels().set.assert_called_once_with(1)

    @responses_lib.activate
    def test_non_matching_pod_sets_ok(self):
        from core.overall_sf_org import get_salesforce_incidents
        incidents = [
            {
                "id": "INC-002",
                "instanceKeys": ["EU1"],
                "IncidentImpacts": [{"severity": "minor"}],
            }
        ]
        responses_lib.add(
            responses_lib.GET,
            f"{TRUST_API}/v1/incidents/active",
            json=incidents,
            status=200,
        )
        mock_gauge = MagicMock()
        with patch("core.overall_sf_org.incident_gauge", mock_gauge):
            get_salesforce_incidents("Production", "NA1")
        mock_gauge.labels.assert_called_with(
            environment="Production", pod="NA1", severity="ok", incident_id=None
        )

    @responses_lib.activate
    def test_handles_request_error(self):
        from core.overall_sf_org import get_salesforce_incidents
        import requests as req_lib
        responses_lib.add(
            responses_lib.GET,
            f"{TRUST_API}/v1/incidents/active",
            body=req_lib.exceptions.ConnectionError("network error"),
        )
        mock_gauge = MagicMock()
        with patch("core.overall_sf_org.incident_gauge", mock_gauge):
            get_salesforce_incidents("Production", "NA1")  # Should not raise


class TestGetSalesforceMaintenances:
    @responses_lib.activate
    def test_scheduled_maintenance_sets_gauge(self):
        from core.overall_sf_org import get_salesforce_maintenances
        maintenance_data = [
            {
                "id": "MAINT-001",
                "instanceKeys": ["NA1"],
                "message": {"eventStatus": "Scheduled"},
                "plannedStartTime": "2024-02-01T02:00:00Z",
                "plannedEndTime": "2024-02-01T04:00:00Z",
            }
        ]
        responses_lib.add(
            responses_lib.GET,
            f"{TRUST_API}/v1/maintenances",
            json=maintenance_data,
            status=200,
        )
        mock_gauge = MagicMock()
        with patch("core.overall_sf_org.maintenance_gauge", mock_gauge):
            get_salesforce_maintenances({"Production": "NA1"})
        mock_gauge.labels.assert_called_once()
        mock_gauge.labels().set.assert_called_once_with(1)

    @responses_lib.activate
    def test_completed_maintenance_skipped(self):
        from core.overall_sf_org import get_salesforce_maintenances
        maintenance_data = [
            {
                "id": "MAINT-002",
                "instanceKeys": ["NA1"],
                "message": {"eventStatus": "Completed"},
                "plannedStartTime": "2024-01-01T02:00:00Z",
                "plannedEndTime": "2024-01-01T04:00:00Z",
            }
        ]
        responses_lib.add(
            responses_lib.GET,
            f"{TRUST_API}/v1/maintenances",
            json=maintenance_data,
            status=200,
        )
        mock_gauge = MagicMock()
        with patch("core.overall_sf_org.maintenance_gauge", mock_gauge):
            get_salesforce_maintenances({"Production": "NA1"})
        mock_gauge.labels.assert_not_called()

    @responses_lib.activate
    def test_non_matching_pod_skipped(self):
        from core.overall_sf_org import get_salesforce_maintenances
        maintenance_data = [
            {
                "id": "MAINT-003",
                "instanceKeys": ["EU1"],
                "message": {"eventStatus": "Scheduled"},
            }
        ]
        responses_lib.add(
            responses_lib.GET,
            f"{TRUST_API}/v1/maintenances",
            json=maintenance_data,
            status=200,
        )
        mock_gauge = MagicMock()
        with patch("core.overall_sf_org.maintenance_gauge", mock_gauge):
            get_salesforce_maintenances({"Production": "NA1"})
        mock_gauge.labels.assert_not_called()


class TestGetSalesforcePermSetAndUsageEntitlements:
    def test_perm_set_licenses_processed(self, mock_sf):
        from core.overall_sf_org import get_salesforce_licenses
        user_lic = []
        perm_lic = [{"MasterLabel": "Sales Cloud", "Status": "Active",
                     "TotalLicenses": 50, "UsedLicenses": 20, "ExpirationDate": "2025-01-01"}]
        usage_lic = []
        with patch("core.overall_sf_org.query_records_all", side_effect=[user_lic, perm_lic, usage_lic]), \
             patch("core.overall_sf_org.total_user_licenses_gauge"), \
             patch("core.overall_sf_org.used_user_licenses_gauge"), \
             patch("core.overall_sf_org.percent_user_licenses_used_gauge"), \
             patch("core.overall_sf_org.total_permissionset_licenses_gauge") as m_total_ps, \
             patch("core.overall_sf_org.used_permissionset_licenses_gauge") as m_used_ps, \
             patch("core.overall_sf_org.percent_permissionset_used_gauge") as m_pct_ps, \
             patch("core.overall_sf_org.total_usage_based_entitlements_licenses_gauge"), \
             patch("core.overall_sf_org.used_usage_based_entitlements_licenses_gauge"), \
             patch("core.overall_sf_org.percent_usage_based_entitlements_used_gauge"):
            get_salesforce_licenses(mock_sf)
        m_total_ps.labels.assert_called_once()
        m_used_ps.labels.assert_called_once()
        m_pct_ps.labels.assert_called_once()

    def test_usage_based_entitlements_processed(self, mock_sf):
        from core.overall_sf_org import get_salesforce_licenses
        usage_lic = [{"MasterLabel": "API Calls", "CurrentAmountAllowed": 1000,
                      "AmountUsed": 300, "EndDate": "2025-12-31"}]
        with patch("core.overall_sf_org.query_records_all", side_effect=[[], [], usage_lic]), \
             patch("core.overall_sf_org.total_user_licenses_gauge"), \
             patch("core.overall_sf_org.used_user_licenses_gauge"), \
             patch("core.overall_sf_org.percent_user_licenses_used_gauge"), \
             patch("core.overall_sf_org.total_permissionset_licenses_gauge"), \
             patch("core.overall_sf_org.used_permissionset_licenses_gauge"), \
             patch("core.overall_sf_org.percent_permissionset_used_gauge"), \
             patch("core.overall_sf_org.total_usage_based_entitlements_licenses_gauge") as m_total_ube, \
             patch("core.overall_sf_org.used_usage_based_entitlements_licenses_gauge") as m_used_ube, \
             patch("core.overall_sf_org.percent_usage_based_entitlements_used_gauge") as m_pct_ube:
            get_salesforce_licenses(mock_sf)
        m_total_ube.labels.assert_called_once()
        m_used_ube.labels.assert_called_once()
        m_pct_ube.labels.assert_called_once()

    def test_zero_usage_entitlement_skips_percent(self, mock_sf):
        from core.overall_sf_org import get_salesforce_licenses
        usage_lic = [{"MasterLabel": "API Calls", "CurrentAmountAllowed": 0,
                      "AmountUsed": None, "EndDate": "2025-12-31"}]
        with patch("core.overall_sf_org.query_records_all", side_effect=[[], [], usage_lic]), \
             patch("core.overall_sf_org.total_user_licenses_gauge"), \
             patch("core.overall_sf_org.used_user_licenses_gauge"), \
             patch("core.overall_sf_org.percent_user_licenses_used_gauge"), \
             patch("core.overall_sf_org.total_permissionset_licenses_gauge"), \
             patch("core.overall_sf_org.used_permissionset_licenses_gauge"), \
             patch("core.overall_sf_org.percent_permissionset_used_gauge"), \
             patch("core.overall_sf_org.total_usage_based_entitlements_licenses_gauge"), \
             patch("core.overall_sf_org.used_usage_based_entitlements_licenses_gauge"), \
             patch("core.overall_sf_org.percent_usage_based_entitlements_used_gauge") as m_pct_ube:
            get_salesforce_licenses(mock_sf)
        m_pct_ube.labels.assert_not_called()


class TestGetSalesforceInstance:
    def test_successful_instance_fetch(self, mock_sf):
        from core.overall_sf_org import get_salesforce_instance
        with patch("core.overall_sf_org.fetch_pod", return_value="NA1") as m_pod, \
             patch("core.overall_sf_org.get_salesforce_incidents") as m_inc, \
             patch("core.overall_sf_org.get_salesforce_maintenances") as m_maint:
            get_salesforce_instance(mock_sf)
        m_pod.assert_called_once_with(mock_sf)
        m_inc.assert_called_once_with("Production", "NA1")
        m_maint.assert_called_once_with({"Production": "NA1"})

    def test_handles_exception(self, mock_sf):
        from core.overall_sf_org import get_salesforce_instance
        with patch("core.overall_sf_org.fetch_pod", side_effect=RuntimeError("fail")):
            get_salesforce_instance(mock_sf)  # Should not raise

    def test_handles_requests_exception(self, mock_sf):
        import requests
        from core.overall_sf_org import get_salesforce_instance
        with patch("core.overall_sf_org.fetch_pod", side_effect=requests.RequestException("conn error")):
            get_salesforce_instance(mock_sf)  # Should not raise


class TestGetSalesforceIncidentsEdgeCases:
    @responses_lib.activate
    def test_malformed_incident_element_skipped(self):
        from core.overall_sf_org import get_salesforce_incidents
        # Element missing IncidentImpacts → KeyError → logged and skipped
        incidents = [{"id": "INC-BAD", "instanceKeys": ["NA1"]}]
        responses_lib.add(
            responses_lib.GET,
            f"{TRUST_API}/v1/incidents/active",
            json=incidents,
            status=200,
        )
        mock_gauge = MagicMock()
        with patch("core.overall_sf_org.incident_gauge", mock_gauge):
            get_salesforce_incidents("Production", "NA1")  # Should not raise
        # Falls through to ok gauge since incident_cnt == 0
        mock_gauge.labels.assert_called_with(
            environment="Production", pod="NA1", severity="ok", incident_id=None
        )


class TestGetSalesforceMaintenancesRequestError:
    @responses_lib.activate
    def test_handles_request_error(self):
        from core.overall_sf_org import get_salesforce_maintenances
        import requests as req_lib
        responses_lib.add(
            responses_lib.GET,
            f"{TRUST_API}/v1/maintenances",
            body=req_lib.exceptions.ConnectionError("down"),
        )
        with patch("core.overall_sf_org.maintenance_gauge"):
            get_salesforce_maintenances({"Production": "NA1"})  # Should not raise
