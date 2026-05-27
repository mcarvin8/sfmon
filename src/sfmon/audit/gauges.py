"""Prometheus metric definitions for audit and compliance monitoring."""

from org_gauge import OrgAwareGauge

# Deployments
deployment_details_gauge = OrgAwareGauge(
    "deployment_details",
    "Salesforce Deployment details",
    [
        "pending_time",
        "deployment_time",
        "deployed_by",
        "status",
        "deployment_id",
        "start_date",
        "completed_date",
    ],
)
pending_time_gauge = OrgAwareGauge(
    "deployment_pending_time",
    "Pending time before starting the deployment",
    ["deployment_id", "deployed_by", "status", "start_date", "completed_date"],
)
deployment_time_gauge = OrgAwareGauge(
    "deployment_time",
    "Time taken for the deployment",
    ["deployment_id", "deployed_by", "status", "start_date", "completed_date"],
)
validation_details_gauge = OrgAwareGauge(
    "validation_details",
    "Salesforce Validation Deployment details",
    [
        "pending_time",
        "deployment_time",
        "deployed_by",
        "status",
        "deployment_id",
        "start_date",
        "completed_date",
    ],
)
validation_pending_time_gauge = OrgAwareGauge(
    "validation_pending_time",
    "Pending time before starting the validation",
    ["deployment_id", "deployed_by", "status", "start_date", "completed_date"],
)
validation_time_gauge = OrgAwareGauge(
    "validation_time",
    "Time taken for the validation",
    ["deployment_id", "deployed_by", "status", "start_date", "completed_date"],
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
geolocation_gauge = OrgAwareGauge(
    "user_location",
    "Longitude and Latitude of user location",
    ["user", "longitude", "latitude", "browser", "status"],
)

# Compliance - Large Queries
hourly_large_query_metric = OrgAwareGauge(
    "hourly_user_querying_large_records",
    "Number of large queries by user (threshold configurable via LARGE_QUERY_THRESHOLD)",
    ["user_id", "user_name", "method", "entity_name"],
)

# Compliance - Audit Trail
suspicious_records_gauge = OrgAwareGauge(
    "suspicious_records",
    "Suspicious records from Audit Trail logs",
    [
        "action",
        "section",
        "user",
        "user_group",
        "created_date",
        "display",
        "delegate_user",
    ],
)

# Compliance - Org-Wide Sharing Settings
org_wide_sharing__setting_changes = OrgAwareGauge(
    "org_wide_sharing_changes",
    "Track changes in Org-Wide Sharing Settings",
    ["date", "user", "user_group", "action", "display"],
)

# Compliance - Forbidden Profiles
forbidden_profile_users_gauge = OrgAwareGauge(
    "forbidden_profile_users",
    "Active users with forbidden profile assignments",
    ["user_id", "user_name", "username", "profile_name"],
)

# Report Exports
hourly_report_export_metric = OrgAwareGauge(
    "hourly_report_export",
    "Report export details",
    ["user_name", "timestamp", "report_name", "report_type_api_name"],
)
