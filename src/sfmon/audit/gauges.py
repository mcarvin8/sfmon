"""Prometheus metric definitions for audit and compliance monitoring."""

from ..org_gauge import OrgAwareGauge

# Deployments
# Per-deployment detail (deployment_id, start/completed timestamps) is unbounded
# over the org's history and does not belong in a label; it's logged as a
# structured event by audit/deployments.py instead. Labels here stay bounded
# by (deployer, status).
deployment_details_gauge = OrgAwareGauge(
    "deployment_details",
    "Salesforce Deployment details",
    ["deployed_by", "status"],
)
pending_time_gauge = OrgAwareGauge(
    "deployment_pending_time",
    "Pending time before starting the deployment",
    ["deployed_by", "status"],
)
deployment_time_gauge = OrgAwareGauge(
    "deployment_time",
    "Time taken for the deployment",
    ["deployed_by", "status"],
)
validation_details_gauge = OrgAwareGauge(
    "validation_details",
    "Salesforce Validation Deployment details",
    ["deployed_by", "status"],
)
validation_pending_time_gauge = OrgAwareGauge(
    "validation_pending_time",
    "Pending time before starting the validation",
    ["deployed_by", "status"],
)
validation_time_gauge = OrgAwareGauge(
    "validation_time",
    "Time taken for the validation",
    ["deployed_by", "status"],
)

# User Activity - Login Metrics
login_success_gauge = OrgAwareGauge(
    "salesforce_login_success_total", "Total number of successful Salesforce logins"
)
login_failure_gauge = OrgAwareGauge(
    "salesforce_login_failure_total", "Total number of failed Salesforce logins"
)
unique_login_attempts_gauge = OrgAwareGauge(
    "unique_login_count_total", "Total number of Unique Salesforce logins"
)

# User Activity - Geolocation
# Per-user lat/long is unbounded (grows with every distinct login location);
# it's logged as a structured event by audit/user_login.py. Labels here count
# logins by (browser, status) within the lookback window instead.
geolocation_gauge = OrgAwareGauge(
    "user_location",
    "Count of user logins by browser and status in the lookback window",
    ["browser", "status"],
)

# Compliance - Large Queries
hourly_large_query_metric = OrgAwareGauge(
    "hourly_user_querying_large_records",
    "Number of large queries by user (threshold configurable via LARGE_QUERY_THRESHOLD)",
    ["user_id", "user_name", "method", "entity_name"],
)

# Compliance - Audit Trail
# Per-record detail (user, created_date, display, delegate_user) is unbounded
# over time; it's logged as a structured event by audit/audit_trail.py. Labels
# here stay bounded by (action, section, user_group).
suspicious_records_gauge = OrgAwareGauge(
    "suspicious_records",
    "Suspicious records from Audit Trail logs",
    ["action", "section", "user_group"],
)

# Compliance - Org-Wide Sharing Settings
# Per-change detail (date, user, display) is unbounded over time; it's logged
# as a structured event by audit/sharing_settings.py.
org_wide_sharing__setting_changes = OrgAwareGauge(
    "org_wide_sharing_changes",
    "Track changes in Org-Wide Sharing Settings",
    ["action", "user_group"],
)

# Compliance - Forbidden Profiles
forbidden_profile_users_gauge = OrgAwareGauge(
    "forbidden_profile_users",
    "Active users with forbidden profile assignments",
    ["user_id", "user_name", "username", "profile_name"],
)

# Report Exports
# Per-export detail (user, timestamp, report name) is unbounded over time;
# it's logged as a structured event by audit/report_export.py. Labels here
# count exports by report type within the hour.
hourly_report_export_metric = OrgAwareGauge(
    "hourly_report_export",
    "Count of report exports by report type in the hour",
    ["report_type_api_name"],
)
