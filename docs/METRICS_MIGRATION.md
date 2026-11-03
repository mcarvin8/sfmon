# Metric names in v4

v4 renames every metric to start with `sfmon_` and makes every label snake_case. **Metric values are unchanged** — a v3 metric and its v4 name report the same number for the same org.

Units in the new names describe what SFMon already stores. In particular, the v3 `salesforce_apex_*_seconds` gauges held Salesforce's raw millisecond values, so their v4 names end in `_milliseconds`, and deployment/validation times are in minutes. `sfmon_apex_db_total_time` has no unit suffix because Salesforce's `DB_TOTAL_TIME` unit is not documented consistently across event types.

Job ids in `config.json` (for example `dormant_salesforce_users`) are **not** renamed.

## Migrating

1. Update dashboards and alert rules to the new names below. The Grafana dashboards in [`grafana/`](../grafana/) already use them.
2. Optional, to keep existing v3 queries working during the switch: load [`prometheus/sfmon-v3-compat.rules.yml`](../prometheus/sfmon-v3-compat.rules.yml) into Prometheus. It records each old name from its new one, with the old label names restored. Remove it once nothing queries the old names.
3. Not ready to migrate? Stay on v3: pin the Docker image to an exact v3 tag (for example `mcarvin8/sfmon:v3.17.0` — `latest` moves to v4), `pip install "sfmon<4"`, or keep the GitHub Action on `mcarvin8/sfmon@v3`.

## Renamed metrics

| Area | v3 name | v4 name | Label renames |
|------|---------|---------|---------------|
| Core | `salesforce_api_usage_percentage` | `sfmon_org_limit_usage_percent` |  |
| Core | `salesforce_total_user_licenses` | `sfmon_user_license_seats` |  |
| Core | `salesforce_used_user_licenses` | `sfmon_user_license_seats_used` |  |
| Core | `salesforce_user_licenses_usage_percentage` | `sfmon_user_license_usage_percent` |  |
| Core | `salesforce_total_permissionset_licenses` | `sfmon_permission_set_license_seats` |  |
| Core | `salesforce_used_permissionset_licenses` | `sfmon_permission_set_license_seats_used` |  |
| Core | `salesforce_permissionset_license_usage_percentage` | `sfmon_permission_set_license_usage_percent` |  |
| Core | `salesforce_total_licenses_usage_based_entitlements` | `sfmon_usage_based_entitlement_seats` |  |
| Core | `salesforce_used_licenses_usage_based_entitlements` | `sfmon_usage_based_entitlement_seats_used` |  |
| Core | `salesforce_percent_used_usage_based_entitlements` | `sfmon_usage_based_entitlement_usage_percent` |  |
| Core | `salesforce_incidents` | `sfmon_trust_incidents` |  |
| Core | `salesforce_maintenance` | `sfmon_trust_maintenance` |  |
| Audit | `deployment_details` | `sfmon_deployment_status` |  |
| Audit | `deployment_pending_time` | `sfmon_deployment_pending_minutes` |  |
| Audit | `deployment_time` | `sfmon_deployment_duration_minutes` |  |
| Audit | `validation_details` | `sfmon_validation_status` |  |
| Audit | `validation_pending_time` | `sfmon_validation_pending_minutes` |  |
| Audit | `validation_time` | `sfmon_validation_duration_minutes` |  |
| Audit | `salesforce_login_success_total` | `sfmon_login_success_count` |  |
| Audit | `salesforce_login_failure_total` | `sfmon_login_failure_count` |  |
| Audit | `unique_login_count_total` | `sfmon_login_unique_count` |  |
| Audit | `user_location` | `sfmon_login_browser_count` |  |
| Audit | `hourly_user_querying_large_records` | `sfmon_hourly_large_queries` |  |
| Audit | `suspicious_records` | `sfmon_audit_trail_suspicious_records` |  |
| Audit | `org_wide_sharing_changes` | `sfmon_audit_trail_sharing_changes` |  |
| Audit | `forbidden_profile_users` | `sfmon_forbidden_profile_users` |  |
| Audit | `hourly_report_export` | `sfmon_hourly_report_exports` |  |
| Ops | `daily_bulk_api_batch_count` | `sfmon_bulk_api_daily_batches` |  |
| Ops | `daily_entity_type_count` | `sfmon_bulk_api_daily_entity_operations` |  |
| Ops | `hourly_bulk_api_batch_count` | `sfmon_bulk_api_hourly_batches` |  |
| Ops | `hourly_entity_type_count` | `sfmon_bulk_api_hourly_entity_operations` |  |
| Ops | `daily_bulk_api2_batch_count` | `sfmon_bulk_api2_daily_batches` |  |
| Ops | `daily_bulk_api2_entity_type_count` | `sfmon_bulk_api2_daily_entity_operations` |  |
| Ops | `hourly_bulk_api2_batch_count` | `sfmon_bulk_api2_hourly_batches` |  |
| Ops | `hourly_bulk_api2_entity_type_count` | `sfmon_bulk_api2_hourly_entity_operations` |  |
| Ops | `salesforce_experienced_page_time` | `sfmon_experienced_page_time_seconds` | `EFFECTIVE_PAGE_TIME_DEVIATION_REASON` → `effective_page_time_deviation_reason`, `EFFECTIVE_PAGE_TIME_DEVIATION_ERROR_TYPE` → `effective_page_time_deviation_error_type`, `PREVPAGE_ENTITY_TYPE` → `prevpage_entity_type`, `PREVPAGE_APP_NAME` → `prevpage_app_name`, `PAGE_ENTITY_TYPE` → `page_entity_type`, `PAGE_APP_NAME` → `page_app_name`, `BROWSER_NAME` → `browser_name` |
| Ops | `salesforce_average_page_time` | `sfmon_average_page_time_seconds` | `Page_name` → `page_name` |
| Ops | `salesforce_async_job_status_count` | `sfmon_async_apex_jobs` |  |
| Ops | `salesforce_apex_run_time_seconds` | `sfmon_apex_run_time_milliseconds` |  |
| Ops | `salesforce_apex_cpu_time_seconds` | `sfmon_apex_cpu_time_milliseconds` |  |
| Ops | `salesforce_apex_execution_time_seconds` | `sfmon_apex_exec_time_milliseconds` |  |
| Ops | `salesforce_apex_db_total_time_seconds` | `sfmon_apex_db_total_time` |  |
| Ops | `salesforce_apex_callout_time_seconds` | `sfmon_apex_callout_time_milliseconds` |  |
| Ops | `apex_entry_point_count` | `sfmon_apex_executions` |  |
| Ops | `apex_avg_runtime` | `sfmon_apex_avg_run_time_milliseconds` |  |
| Ops | `apex_max_runtime` | `sfmon_apex_max_run_time_milliseconds` |  |
| Ops | `apex_total_runtime` | `sfmon_apex_total_run_time_milliseconds` |  |
| Ops | `apex_avg_cputime` | `sfmon_apex_avg_cpu_time_milliseconds` |  |
| Ops | `apex_max_cputime` | `sfmon_apex_max_cpu_time_milliseconds` |  |
| Ops | `apex_runtime_gt_5s_count` | `sfmon_apex_long_running_executions` |  |
| Ops | `apex_runtime_gt_10s_count` | `sfmon_apex_very_long_running_executions` |  |
| Ops | `apex_runtime_gt_5s_percentage` | `sfmon_apex_long_running_executions_percent` |  |
| Ops | `most_apex_concurrent_errors_sorted_by_runtime` | `sfmon_apex_top_long_running_by_avg_run_time` |  |
| Ops | `most_apex_concurrent_errors_sorted_by_count` | `sfmon_apex_top_long_running_by_count` |  |
| Ops | `concurrent_request_error_count` | `sfmon_apex_concurrent_long_running_errors` |  |
| Ops | `apex_exception_details` | `sfmon_apex_exception_details` |  |
| Ops | `apex_exception_category_count` | `sfmon_apex_exceptions_by_category` |  |
| Ops | `apex_flex_queue` | `sfmon_apex_flex_queue_jobs` | `ApexClassId` → `apex_class_id` |
| Tech debt | `unused_permissionsets` | `sfmon_unassigned_permission_sets` |  |
| Tech debt | `limited_permissionsets` | `sfmon_limited_user_permission_sets` |  |
| Tech debt | `five_or_less_profile_assignees` | `sfmon_profiles_with_few_users` | `profileId` → `profile_id`, `profileName` → `profile_name` |
| Tech debt | `unassigned_profiles` | `sfmon_profiles_with_no_active_users` | `profileId` → `profile_id`, `profileName` → `profile_name` |
| Tech debt | `deprecated_apex_classes` | `sfmon_deprecated_api_apex_classes` |  |
| Tech debt | `deprecated_apex_triggers` | `sfmon_deprecated_api_apex_triggers` |  |
| Tech debt | `apex_class_length_without_comments` | `sfmon_apex_class_characters` |  |
| Tech debt | `apex_trigger_length_without_comments` | `sfmon_apex_trigger_characters` |  |
| Tech debt | `apex_character_limit_percentage` | `sfmon_apex_character_limit_usage_percent` |  |
| Tech debt | `workflow_rules` | `sfmon_workflow_rules` |  |
| Tech debt | `security_health_check_score` | `sfmon_security_health_check_score` |  |
| Tech debt | `salesforce_health_risks` | `sfmon_security_health_check_risks` |  |
| Tech debt | `dormant_salesforce_users` | `sfmon_dormant_users` |  |
| Tech debt | `dormant_portal_users` | `sfmon_dormant_portal_users` |  |
| Tech debt | `total_queues_per_object` | `sfmon_queues_per_object` |  |
| Tech debt | `queues_with_no_members` | `sfmon_queues_with_no_members` |  |
| Tech debt | `queues_with_zero_open_cases` | `sfmon_queues_with_zero_open_cases` |  |
| Tech debt | `public_groups_with_no_members` | `sfmon_public_groups_with_no_members` |  |
| Tech debt | `dashboards_with_inactive_users` | `sfmon_dashboards_with_inactive_running_users` |  |
| Tech debt | `scheduled_apex_jobs` | `sfmon_scheduled_apex_jobs` |  |
| Tech debt | `pmd_code_smells` | `sfmon_pmd_code_smells` |  |
| Tech debt | `pmd_apex_violations` | `sfmon_pmd_apex_violations` |  |
| Tech debt | `minimal_permission_sets` | `sfmon_minimal_permission_sets` |  |
| Tech debt | `minimal_permission_sets_percentage` | `sfmon_minimal_permission_sets_percent` |  |

Unchanged: `sfmon_job_success`, `sfmon_job_last_run_timestamp_seconds`, `sfmon_job_last_success_timestamp_seconds`, `sfmon_job_duration_seconds`, `sfmon_job_query_errors`.
