"""Prometheus metric definitions for always-on core monitoring."""

from ..org_gauge import OrgAwareGauge

TOTAL_LICENSES = "Total Salesforce licenses"
USED_LICENSES = "Used Salesforce licenses"
USED_LICENSES_PERCENTAGE = "Percentage of Salesforce licenses used"

# API and Limits
api_usage_percentage_gauge = OrgAwareGauge(
    "sfmon_org_limit_usage_percent",
    "Salesforce API Usage Percentage",
    ["limit_name", "limit_description", "limit_utilized", "max_limit"],
)

# Licenses - User Licenses
total_user_licenses_gauge = OrgAwareGauge(
    "sfmon_user_license_seats", TOTAL_LICENSES, ["license_name", "status"]
)
used_user_licenses_gauge = OrgAwareGauge(
    "sfmon_user_license_seats_used", USED_LICENSES, ["license_name", "status"]
)
percent_user_licenses_used_gauge = OrgAwareGauge(
    "sfmon_user_license_usage_percent",
    USED_LICENSES_PERCENTAGE,
    ["license_name", "status", "used_licenses", "total_licenses"],
)

# Licenses - Permission Set Licenses
total_permissionset_licenses_gauge = OrgAwareGauge(
    "sfmon_permission_set_license_seats",
    TOTAL_LICENSES,
    ["license_name", "status"],
)
used_permissionset_licenses_gauge = OrgAwareGauge(
    "sfmon_permission_set_license_seats_used", USED_LICENSES, ["license_name", "status"]
)
percent_permissionset_used_gauge = OrgAwareGauge(
    "sfmon_permission_set_license_usage_percent",
    USED_LICENSES_PERCENTAGE,
    ["license_name", "status", "used_licenses", "total_licenses", "expiration_date"],
)

# Licenses - Usage-Based Entitlements
total_usage_based_entitlements_licenses_gauge = OrgAwareGauge(
    "sfmon_usage_based_entitlement_seats",
    TOTAL_LICENSES,
    ["license_name"],
)
used_usage_based_entitlements_licenses_gauge = OrgAwareGauge(
    "sfmon_usage_based_entitlement_seats_used", USED_LICENSES, ["license_name"]
)
percent_usage_based_entitlements_used_gauge = OrgAwareGauge(
    "sfmon_usage_based_entitlement_usage_percent",
    USED_LICENSES_PERCENTAGE,
    ["license_name", "used_licenses", "total_licenses", "expiration_date"],
)

# Incidents & Maintenance
incident_gauge = OrgAwareGauge(
    "sfmon_trust_incidents",
    "Number of active Salesforce incidents",
    ["environment", "pod", "severity", "incident_id"],
)
maintenance_gauge = OrgAwareGauge(
    "sfmon_trust_maintenance",
    "Ongoing or Planned Salesforce Maintenance",
    [
        "environment",
        "maintenance_id",
        "status",
        "planned_start_time",
        "planned_end_time",
    ],
)
