"""Prometheus metric definitions for operations monitoring."""

from ..org_gauge import OrgAwareGauge

# Bulk API 1.0
daily_batch_count_metric = OrgAwareGauge(
    "sfmon_bulk_api_daily_batches",
    "Count of batches by job_id, user_id, and entity_type",
    [
        "job_id",
        "user_id",
        "entity_type",
        "total_records_failed",
        "total_records_processed",
    ],
)
daily_entity_type_count_metric = OrgAwareGauge(
    "sfmon_bulk_api_daily_entity_operations",
    "Counts of ENTITY_TYPE by user_id and OPERATION_TYPE",
    ["user_id", "operation_type", "entity_type"],
)
hourly_batch_count_metric = OrgAwareGauge(
    "sfmon_bulk_api_hourly_batches",
    "Count of batches by job_id, user_id, and entity_type",
    [
        "job_id",
        "user_id",
        "entity_type",
        "total_records_failed",
        "total_records_processed",
    ],
)
hourly_entity_type_count_metric = OrgAwareGauge(
    "sfmon_bulk_api_hourly_entity_operations",
    "Counts of ENTITY_TYPE by user_id and OPERATION_TYPE",
    ["user_id", "operation_type", "entity_type"],
)

# Bulk API 2.0
daily_bulk_api2_batch_count_metric = OrgAwareGauge(
    "sfmon_bulk_api2_daily_batches",
    "Count of Bulk API 2.0 batches by job_id, user_id, and entity_type",
    [
        "job_id",
        "user_id",
        "entity_type",
        "total_records_failed",
        "total_records_processed",
    ],
)
daily_bulk_api2_entity_type_count_metric = OrgAwareGauge(
    "sfmon_bulk_api2_daily_entity_operations",
    "Bulk API 2.0 counts of ENTITY_TYPE by user_id and OPERATION_TYPE",
    ["user_id", "operation_type", "entity_type"],
)
hourly_bulk_api2_batch_count_metric = OrgAwareGauge(
    "sfmon_bulk_api2_hourly_batches",
    "Count of Bulk API 2.0 batches by job_id, user_id, and entity_type",
    [
        "job_id",
        "user_id",
        "entity_type",
        "total_records_failed",
        "total_records_processed",
    ],
)
hourly_bulk_api2_entity_type_count_metric = OrgAwareGauge(
    "sfmon_bulk_api2_hourly_entity_operations",
    "Bulk API 2.0 counts of ENTITY_TYPE by user_id and OPERATION_TYPE",
    ["user_id", "operation_type", "entity_type"],
)

# Performance - EPT/APT
ept_metric = OrgAwareGauge(
    "sfmon_experienced_page_time_seconds",
    "Experienced Page Time (EPT) in seconds",
    [
        "effective_page_time_deviation_reason",
        "effective_page_time_deviation_error_type",
        "prevpage_entity_type",
        "prevpage_app_name",
        "page_entity_type",
        "page_app_name",
        "browser_name",
    ],
)
apt_metric = OrgAwareGauge(
    "sfmon_average_page_time_seconds", "Average Page Time (APT) in seconds", ["page_name"]
)

# Apex Jobs - Async Job Status
async_job_status_gauge = OrgAwareGauge(
    "sfmon_async_apex_jobs",
    "Total count of Salesforce Async Jobs by Status",
    ["status", "method", "job_type", "number_of_errors"],
)

# Apex Jobs - Execution Time
run_time_metric = OrgAwareGauge(
    "sfmon_apex_run_time_milliseconds",
    "Apex request run time in milliseconds (RUN_TIME)",
    ["entry_point", "quiddity"],
)
cpu_time_metric = OrgAwareGauge(
    "sfmon_apex_cpu_time_milliseconds",
    "Apex CPU time in milliseconds (CPU_TIME)",
    ["entry_point", "quiddity"],
)
exec_time_metric = OrgAwareGauge(
    "sfmon_apex_exec_time_milliseconds",
    "Apex execution time in milliseconds (EXEC_TIME)",
    ["entry_point", "quiddity"],
)
db_total_time_metric = OrgAwareGauge(
    "sfmon_apex_db_total_time",
    "Apex database time as reported by Salesforce (DB_TOTAL_TIME)",
    ["entry_point", "quiddity"],
)
callout_time_metric = OrgAwareGauge(
    "sfmon_apex_callout_time_milliseconds",
    "Apex callout time in milliseconds (CALLOUT_TIME)",
    ["entry_point", "quiddity"],
)

# Apex Jobs - Execution Summary
apex_entry_point_count = OrgAwareGauge(
    "sfmon_apex_executions",
    "Count of apex executions by entry point",
    ["entry_point", "quiddity"],
)
apex_avg_runtime = OrgAwareGauge(
    "sfmon_apex_avg_run_time_milliseconds", "Average runtime by entry point", ["entry_point", "quiddity"]
)
apex_max_runtime = OrgAwareGauge(
    "sfmon_apex_max_run_time_milliseconds", "Maximum runtime by entry point", ["entry_point", "quiddity"]
)
apex_total_runtime = OrgAwareGauge(
    "sfmon_apex_total_run_time_milliseconds", "Total runtime by entry point", ["entry_point", "quiddity"]
)
apex_avg_cputime = OrgAwareGauge(
    "sfmon_apex_avg_cpu_time_milliseconds", "Average CPU time by entry point", ["entry_point", "quiddity"]
)
apex_max_cputime = OrgAwareGauge(
    "sfmon_apex_max_cpu_time_milliseconds", "Maximum CPU time by entry point", ["entry_point", "quiddity"]
)
apex_runtime_gt_5s_count = OrgAwareGauge(
    "sfmon_apex_long_running_executions",
    "Count of apex executions with runtime > threshold (configurable via LONG_RUNNING_APEX_MS)",
    ["entry_point", "quiddity"],
)
apex_runtime_gt_10s_count = OrgAwareGauge(
    "sfmon_apex_very_long_running_executions",
    "Count of apex executions with runtime > threshold (configurable via VERY_LONG_RUNNING_APEX_MS)",
    ["entry_point", "quiddity"],
)
apex_runtime_gt_5s_percentage = OrgAwareGauge(
    "sfmon_apex_long_running_executions_percent",
    "Percentage of apex executions with runtime > threshold",
    ["entry_point", "quiddity"],
)

# Apex Jobs - Concurrent Errors
top_apex_concurrent_errors_sorted_by_avg_runtime = OrgAwareGauge(
    "sfmon_apex_top_long_running_by_avg_run_time",
    "Top Long Running Requests by Average Runtime with Runtime > threshold",
    ["entry_point", "count", "avg_exec_time", "avg_db_time"],
)
top_apex_concurrent_errors_sorted_by_count = OrgAwareGauge(
    "sfmon_apex_top_long_running_by_count",
    "Top Long Running Requests by Count with Runtime > threshold",
    ["entry_point", "avg_run_time", "avg_exec_time", "avg_db_time"],
)
concurrent_errors_count_gauge = OrgAwareGauge(
    "sfmon_apex_concurrent_long_running_errors",
    "Count of non-blank REQUEST_ID entries in CSV file",
    ["event_type"],
)

# Apex Jobs - Exceptions
apex_exception_details_gauge = OrgAwareGauge(
    "sfmon_apex_exception_details",
    "Details of each Apex exception",
    [
        "request_id",
        "exception_category",
        "timestamp",
        "exception_type",
        "exception_message",
        "stack_trace",
    ],
)
apex_exception_category_count_gauge = OrgAwareGauge(
    "sfmon_apex_exceptions_by_category",
    "Total count of Apex exceptions by category",
    ["exception_category"],
)

# Apex Flex Queue
apex_flex_queue = OrgAwareGauge(
    "sfmon_apex_flex_queue_jobs", "Jobs in holding status flex queue", ["id", "apex_class_id"]
)
