"""
Prometheus Metrics Definitions Module

This module defines all Prometheus Gauge metrics for the monitoring service.
These gauges expose comprehensive Salesforce org health, performance, compliance, and
operational metrics that are scraped by Prometheus and visualized in Grafana dashboards.

Metric Categories:
    1. API and Limits: API usage percentages, org limits
    2. Licenses: User licenses, permission set licenses, usage-based entitlements
    3. Incidents & Maintenance: Salesforce Trust API status
    4. Bulk API: Daily/hourly batch and entity type metrics
    5. Deployments: Deployment and validation timing/status
    6. Performance: EPT, APT metrics
    7. Apex Jobs: Job status, execution time, exceptions, concurrent errors
    8. Apex Flex Queue: Jobs in holding status
    9. User Activity: Login counts, geolocation analysis
    10. Compliance: Large queries, suspicious audit trail changes, org-wide sharing, forbidden profiles
    11. Report Exports: User report export activity
    12. Tech Debt - Permissions: Permission sets and profiles
    13. Tech Debt - Code Quality: API versions, workflow rules
    14. Tech Debt - Security: Health check scores and risks
    15. Tech Debt - Users: Dormant users
    16. Tech Debt - Queues & Groups: Queue and group management
    17. Tech Debt - Dashboards: Dashboards with inactive users
    18. Tech Debt - Scheduled Jobs: Scheduled Apex jobs

Constants:
    - TOTAL_LICENSES: Description for total license metrics
    - USED_LICENSES: Description for used license metrics
    - USED_LICENSES_PERCENTAGE: Description for license usage percentage

Note: All gauges follow consistent labeling patterns for filtering and aggregation
in Grafana dashboards.
"""
from prometheus_client import Gauge

# =============================================================================
# Constants
# =============================================================================
TOTAL_LICENSES = 'Total Salesforce licenses'
USED_LICENSES = 'Used Salesforce licenses'
USED_LICENSES_PERCENTAGE = 'Percentage of Salesforce licenses used'

# =============================================================================
# 1. API and Limits
# =============================================================================
api_usage_percentage_gauge = Gauge(
    'salesforce_api_usage_percentage',
    'Salesforce API Usage Percentage',
    ['limit_name', 'limit_description', 'limit_utilized', 'max_limit']
)

# =============================================================================
# 2. Licenses - User Licenses
# =============================================================================
total_user_licenses_gauge = Gauge(
    'salesforce_total_user_licenses',
    TOTAL_LICENSES,
    ['license_name', 'status']
)
used_user_licenses_gauge = Gauge(
    'salesforce_used_user_licenses',
    USED_LICENSES,
    ['license_name', 'status']
)
percent_user_licenses_used_gauge = Gauge(
    'salesforce_user_licenses_usage_percentage',
    USED_LICENSES_PERCENTAGE,
    ['license_name', 'status', 'used_licenses', 'total_licenses']
)

# =============================================================================
# 2. Licenses - Permission Set Licenses
# =============================================================================
total_permissionset_licenses_gauge = Gauge(
    'salesforce_total_permissionset_licenses',
    TOTAL_LICENSES,
    ['license_name', 'status']
)
used_permissionset_licenses_gauge = Gauge(
    'salesforce_used_permissionset_licenses',
    USED_LICENSES,
    ['license_name', 'status']
)
percent_permissionset_used_gauge = Gauge(
    'salesforce_permissionset_license_usage_percentage',
    USED_LICENSES_PERCENTAGE,
    ['license_name', 'status', 'used_licenses', 'total_licenses', 'expiration_date']
)

# =============================================================================
# 2. Licenses - Usage-Based Entitlements
# =============================================================================
total_usage_based_entitlements_licenses_gauge = Gauge(
    'salesforce_total_licenses_usage_based_entitlements',
    TOTAL_LICENSES,
    ['license_name']
)
used_usage_based_entitlements_licenses_gauge = Gauge(
    'salesforce_used_licenses_usage_based_entitlements',
    USED_LICENSES,
    ['license_name']
)
percent_usage_based_entitlements_used_gauge = Gauge(
    'salesforce_percent_used_usage_based_entitlements',
    USED_LICENSES_PERCENTAGE,
    ['license_name', 'used_licenses', 'total_licenses', 'expiration_date']
)

# =============================================================================
# 3. Incidents & Maintenance
# =============================================================================
incident_gauge = Gauge(
    'salesforce_incidents',
    'Number of active Salesforce incidents',
    ['environment', 'pod', 'severity', 'incident_id']
)
maintenance_gauge = Gauge(
    'salesforce_maintenance',
    'Ongoing or Planned Salesforce Maintenance',
    ['environment', 'maintenance_id', 'status', 'planned_start_time', 'planned_end_time']
)

# =============================================================================
# 4. Bulk API - Daily Metrics
# =============================================================================
daily_batch_count_metric = Gauge(
    'daily_bulk_api_batch_count',
    'Count of batches by job_id, user_id, and entity_type',
    ['job_id', 'user_id', 'entity_type', 'total_records_failed', 'total_records_processed']
)
daily_entity_type_count_metric = Gauge(
    'daily_entity_type_count',
    'Counts of ENTITY_TYPE by user_id and OPERATION_TYPE',
    ['user_id', 'operation_type', 'entity_type']
)

# =============================================================================
# 4. Bulk API - Hourly Metrics
# =============================================================================
hourly_batch_count_metric = Gauge(
    'hourly_bulk_api_batch_count',
    'Count of batches by job_id, user_id, and entity_type',
    ['job_id', 'user_id', 'entity_type', 'total_records_failed', 'total_records_processed']
)
hourly_entity_type_count_metric = Gauge(
    'hourly_entity_type_count',
    'Counts of ENTITY_TYPE by user_id and OPERATION_TYPE',
    ['user_id', 'operation_type', 'entity_type']
)

# =============================================================================
# 5. Deployments
# =============================================================================
deployment_details_gauge = Gauge(
    'deployment_details',
    'Salesforce Deployment details',
    ['pending_time', 'deployment_time', 'deployed_by', 'status', 'deployment_id']
)
pending_time_gauge = Gauge(
    'deployment_pending_time',
    'Pending time before starting the deployment',
    ['deployment_id', 'deployed_by', 'status']
)
deployment_time_gauge = Gauge(
    'deployment_time',
    'Time taken for the deployment',
    ['deployment_id', 'deployed_by', 'status']
)

# =============================================================================
# 5. Validations
# =============================================================================
validation_details_gauge = Gauge(
    'validation_details',
    'Salesforce Validation Deployment details',
    ['pending_time', 'deployment_time', 'deployed_by', 'status', 'deployment_id']
)
validation_pending_time_gauge = Gauge(
    'validation_pending_time',
    'Pending time before starting the validation',
    ['deployment_id', 'deployed_by', 'status']
)
validation_time_gauge = Gauge(
    'validation_time',
    'Time taken for the validation',
    ['deployment_id', 'deployed_by', 'status']
)

# =============================================================================
# 6. Performance - Page Times (EPT/APT)
# =============================================================================
ept_metric = Gauge(
    'salesforce_experienced_page_time',
    'Experienced Page Time (EPT) in seconds',
    ['EFFECTIVE_PAGE_TIME_DEVIATION_REASON', 'EFFECTIVE_PAGE_TIME_DEVIATION_ERROR_TYPE',
     'PREVPAGE_ENTITY_TYPE', 'PREVPAGE_APP_NAME', 'PAGE_ENTITY_TYPE',
     'PAGE_APP_NAME', 'BROWSER_NAME']
)
apt_metric = Gauge(
    'salesforce_average_page_time',
    'Average Page Time (APT) in seconds',
    ['Page_name']
)

# =============================================================================
# 7. Apex Jobs - Async Job Status
# =============================================================================
async_job_status_gauge = Gauge(
    'salesforce_async_job_status_count',
    'Total count of Salesforce Async Jobs by Status',
    ['status', 'method', 'job_type', 'number_of_errors']
)

# =============================================================================
# 7. Apex Jobs - Execution Time Metrics
# =============================================================================
run_time_metric = Gauge(
    'salesforce_apex_run_time_seconds',
    'Total Apex execution time',
    ['entry_point', 'quiddity']
)
cpu_time_metric = Gauge(
    'salesforce_apex_cpu_time_seconds',
    'CPU time used by Apex execution',
    ['entry_point', 'quiddity']
)
exec_time_metric = Gauge(
    'salesforce_apex_execution_time_seconds',
    'Total execution time',
    ['entry_point', 'quiddity']
)
db_total_time_metric = Gauge(
    'salesforce_apex_db_total_time_seconds',
    'Total database execution time',
    ['entry_point', 'quiddity']
)
callout_time_metric = Gauge(
    'salesforce_apex_callout_time_seconds',
    'Total callout time',
    ['entry_point', 'quiddity']
)

# =============================================================================
# 7. Apex Jobs - Execution Summary Metrics
# =============================================================================
apex_entry_point_count = Gauge(
    'apex_entry_point_count',
    'Count of apex executions by entry point',
    ['entry_point', 'quiddity']
)
apex_avg_runtime = Gauge(
    'apex_avg_runtime',
    'Average runtime by entry point',
    ['entry_point', 'quiddity']
)
apex_max_runtime = Gauge(
    'apex_max_runtime',
    'Maximum runtime by entry point',
    ['entry_point', 'quiddity']
)
apex_total_runtime = Gauge(
    'apex_total_runtime',
    'Total runtime by entry point',
    ['entry_point', 'quiddity']
)
apex_avg_cputime = Gauge(
    'apex_avg_cputime',
    'Average CPU time by entry point',
    ['entry_point', 'quiddity']
)
apex_max_cputime = Gauge(
    'apex_max_cputime',
    'Maximum CPU time by entry point',
    ['entry_point', 'quiddity']
)
apex_runtime_gt_5s_count = Gauge(
    'apex_runtime_gt_5s_count',
    'Count of apex executions with runtime > threshold (configurable via LONG_RUNNING_APEX_MS)',
    ['entry_point', 'quiddity']
)
apex_runtime_gt_10s_count = Gauge(
    'apex_runtime_gt_10s_count',
    'Count of apex executions with runtime > threshold (configurable via VERY_LONG_RUNNING_APEX_MS)',
    ['entry_point', 'quiddity']
)
apex_runtime_gt_5s_percentage = Gauge(
    'apex_runtime_gt_5s_percentage',
    'Percentage of apex executions with runtime > threshold',
    ['entry_point', 'quiddity']
)

# =============================================================================
# 7. Apex Jobs - Concurrent Errors
# =============================================================================
top_apex_concurrent_errors_sorted_by_avg_runtime = Gauge(
    'most_apex_concurrent_errors_sorted_by_runtime',
    'Top Long Running Requests by Average Runtime with Runtime > threshold',
    ['entry_point', 'count', 'avg_exec_time', 'avg_db_time']
)
top_apex_concurrent_errors_sorted_by_count = Gauge(
    'most_apex_concurrent_errors_sorted_by_count',
    'Top Long Running Requests by Count with Runtime > threshold',
    ['entry_point', 'avg_run_time', 'avg_exec_time', 'avg_db_time']
)
concurrent_errors_count_gauge = Gauge(
    'concurrent_request_error_count',
    'Count of non-blank REQUEST_ID entries in CSV file',
    ['event_type']
)

# =============================================================================
# 7. Apex Jobs - Exceptions
# =============================================================================
apex_exception_details_gauge = Gauge(
    'apex_exception_details',
    'Details of each Apex exception',
    ['request_id', 'exception_category', 'timestamp',
     'exception_type', 'exception_message', 'stack_trace']
)
apex_exception_category_count_gauge = Gauge(
    'apex_exception_category_count',
    'Total count of Apex exceptions by category',
    ['exception_category']
)

# =============================================================================
# 8. Apex Flex Queue
# =============================================================================
apex_flex_queue = Gauge(
    'apex_flex_queue',
    'Jobs in holding status flex queue',
    ['id', 'ApexClassId']
)

# =============================================================================
# 9. User Activity - Login Metrics
# =============================================================================
login_success_gauge = Gauge(
    'salesforce_login_success_total',
    'Total number of successful Salesforce logins'
)
login_failure_gauge = Gauge(
    'salesforce_login_failure_total',
    'Total number of failed Salesforce logins'
)
unique_login_attempts_gauge = Gauge(
    'unique_login_count_total',
    'Total number of Unique Salesforce logins'
)

# =============================================================================
# 9. User Activity - Geolocation
# =============================================================================
geolocation_gauge = Gauge(
    'user_location',
    'Longitude and Latitude of user location',
    ['user', 'longitude', 'latitude', 'browser', 'status']
)

# =============================================================================
# 10. Compliance - Large Queries
# =============================================================================
hourly_large_query_metric = Gauge(
    'hourly_user_querying_large_records',
    'Number of large queries by user (threshold configurable via LARGE_QUERY_THRESHOLD)',
    ['user_id', 'user_name', 'method', 'entity_name']
)

# =============================================================================
# 10. Compliance - Audit Trail
# =============================================================================
suspicious_records_gauge = Gauge(
    'suspicious_records',
    'Suspicious records from Audit Trail logs',
    ['action', 'section', 'user', 'user_group', 'created_date', 'display', 'delegate_user']
)

# =============================================================================
# 10. Compliance - Org-Wide Sharing Settings
# =============================================================================
org_wide_sharing__setting_changes = Gauge(
    'org_wide_sharing_changes',
    'Track changes in Org-Wide Sharing Settings',
    ['date', 'user', 'user_group', 'action', 'display']
)

# =============================================================================
# 10. Compliance - Forbidden Profiles
# =============================================================================
forbidden_profile_users_gauge = Gauge(
    'forbidden_profile_users',
    'Active users with forbidden profile assignments',
    ['user_id', 'user_name', 'username', 'profile_name']
)

# =============================================================================
# 11. Report Exports
# =============================================================================
hourly_report_export_metric = Gauge(
    'hourly_report_export',
    'Report export details',
    ['user_name', 'timestamp', 'report_name', 'report_type_api_name']
)

# =============================================================================
# 12. Tech Debt - Permission Sets
# =============================================================================
unused_permissionsets = Gauge(
    'unused_permissionsets',
    'Permission sets not assigned to any users or groups',
    ['name', 'id']
)
limited_permissionsets = Gauge(
    'limited_permissionsets',
    'Permission sets assigned to limited active users (threshold configurable via PERMSET_LIMITED_USERS_THRESHOLD)',
    ['name', 'id']
)

# =============================================================================
# 12. Tech Debt - Profiles
# =============================================================================
five_or_less_profile_assignees = Gauge(
    'five_or_less_profile_assignees',
    'Profiles with limited assignees (threshold configurable via PROFILE_UNDER_USERS_THRESHOLD)',
    ['profileId', 'profileName']
)
unassigned_profiles = Gauge(
    'unassigned_profiles',
    'Profiles with no active users',
    ['profileId', 'profileName']
)

# =============================================================================
# 13. Tech Debt - Code Quality (API Versions)
# =============================================================================
deprecated_apex_class_gauge = Gauge(
    'deprecated_apex_classes',
    'Apex classes running on deprecated API versions (threshold configurable via DEPRECATED_API_VERSION)',
    ['id', 'name']
)
deprecated_apex_trigger_gauge = Gauge(
    'deprecated_apex_triggers',
    'Apex triggers running on deprecated API versions (threshold configurable via DEPRECATED_API_VERSION)',
    ['id', 'name']
)

# =============================================================================
# 13. Tech Debt - Code Quality (Workflow Rules)
# =============================================================================
workflow_rules_gauge = Gauge(
    'workflow_rules',
    'Workflow rules in the org',
    ['id', 'created_date', 'namespace_prefix']
)

# =============================================================================
# 14. Tech Debt - Security
# =============================================================================
security_health_check_gauge = Gauge(
    'security_health_check_score',
    'Salesforce Security Health Check Score',
    ['grade']
)
salesforce_health_risks_gauge = Gauge(
    'salesforce_health_risks',
    'Salesforce Security Health Check Risks',
    ['org_value', 'risk_type', 'setting', 'setting_group',
     'setting_risk_category', 'standard_value', 'compliance_status']
)

# =============================================================================
# 15. Tech Debt - Users
# =============================================================================
dormant_salesforce_users_gauge = Gauge(
    'dormant_salesforce_users',
    'Dormant Salesforce users (threshold configurable via DORMANT_USER_DAYS)',
    ['user_id', 'username', 'email', 'profile_name', 'created_date', 'last_login_date']
)
dormant_portal_users_gauge = Gauge(
    'dormant_portal_users',
    'Dormant Portal users (threshold configurable via DORMANT_USER_DAYS)',
    ['user_id', 'username', 'email', 'profile_name', 'created_date', 'last_login_date']
)

# =============================================================================
# 16. Tech Debt - Queues
# =============================================================================
total_queues_per_object_gauge = Gauge(
    'total_queues_per_object',
    'Total queues per Salesforce object',
    ['sobject_type']
)
queues_with_no_members_gauge = Gauge(
    'queues_with_no_members',
    'Queues with no members',
    ['queue_id', 'queue_name']
)
queues_with_zero_open_cases_gauge = Gauge(
    'queues_with_zero_open_cases',
    'Queues that can own Cases but have zero open Cases',
    ['queue_id', 'queue_name']
)

# =============================================================================
# 16. Tech Debt - Public Groups
# =============================================================================
public_groups_with_no_members_gauge = Gauge(
    'public_groups_with_no_members',
    'Public Groups with no members',
    ['group_id', 'group_name']
)

# =============================================================================
# 17. Tech Debt - Dashboards
# =============================================================================
dashboards_with_inactive_users_gauge = Gauge(
    'dashboards_with_inactive_users',
    'Dashboards with inactive running users',
    ['dashboard_id', 'dashboard_title', 'running_user_name', 'created_date', 'last_referenced_date']
)

# =============================================================================
# 18. Tech Debt - Scheduled Jobs
# =============================================================================
scheduled_apex_jobs_gauge = Gauge(
    'scheduled_apex_jobs',
    'Scheduled Apex jobs in the org',
    ['job_id', 'job_name', 'cron_expression', 'state',
     'next_fire_time', 'previous_fire_time', 'created_by', 'created_date']
)
