"""Prometheus metric definitions for operations monitoring."""

from org_gauge import OrgAwareGauge

# Bulk API 1.0
daily_batch_count_metric = OrgAwareGauge(
    "daily_bulk_api_batch_count",
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
    "daily_entity_type_count",
    "Counts of ENTITY_TYPE by user_id and OPERATION_TYPE",
    ["user_id", "operation_type", "entity_type"],
)
hourly_batch_count_metric = OrgAwareGauge(
    "hourly_bulk_api_batch_count",
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
    "hourly_entity_type_count",
    "Counts of ENTITY_TYPE by user_id and OPERATION_TYPE",
    ["user_id", "operation_type", "entity_type"],
)

# Bulk API 2.0
daily_bulk_api2_batch_count_metric = OrgAwareGauge(
    "daily_bulk_api2_batch_count",
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
    "daily_bulk_api2_entity_type_count",
    "Bulk API 2.0 counts of ENTITY_TYPE by user_id and OPERATION_TYPE",
    ["user_id", "operation_type", "entity_type"],
)
hourly_bulk_api2_batch_count_metric = OrgAwareGauge(
    "hourly_bulk_api2_batch_count",
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
    "hourly_bulk_api2_entity_type_count",
    "Bulk API 2.0 counts of ENTITY_TYPE by user_id and OPERATION_TYPE",
    ["user_id", "operation_type", "entity_type"],
)

# Performance - EPT/APT
ept_metric = OrgAwareGauge(
    "salesforce_experienced_page_time",
    "Experienced Page Time (EPT) in seconds",
    [
        "EFFECTIVE_PAGE_TIME_DEVIATION_REASON",
        "EFFECTIVE_PAGE_TIME_DEVIATION_ERROR_TYPE",
        "PREVPAGE_ENTITY_TYPE",
        "PREVPAGE_APP_NAME",
        "PAGE_ENTITY_TYPE",
        "PAGE_APP_NAME",
        "BROWSER_NAME",
    ],
)
apt_metric = OrgAwareGauge(
    "salesforce_average_page_time", "Average Page Time (APT) in seconds", ["Page_name"]
)

# Apex Jobs - Async Job Status
async_job_status_gauge = OrgAwareGauge(
    "salesforce_async_job_status_count",
    "Total count of Salesforce Async Jobs by Status",
    ["status", "method", "job_type", "number_of_errors"],
)

# Apex Jobs - Execution Time
run_time_metric = OrgAwareGauge(
    "salesforce_apex_run_time_seconds",
    "Total Apex execution time",
    ["entry_point", "quiddity"],
)
cpu_time_metric = OrgAwareGauge(
    "salesforce_apex_cpu_time_seconds",
    "CPU time used by Apex execution",
    ["entry_point", "quiddity"],
)
exec_time_metric = OrgAwareGauge(
    "salesforce_apex_execution_time_seconds",
    "Total execution time",
    ["entry_point", "quiddity"],
)
db_total_time_metric = OrgAwareGauge(
    "salesforce_apex_db_total_time_seconds",
    "Total database execution time",
    ["entry_point", "quiddity"],
)
callout_time_metric = OrgAwareGauge(
    "salesforce_apex_callout_time_seconds",
    "Total callout time",
    ["entry_point", "quiddity"],
)

# Apex Jobs - Execution Summary
apex_entry_point_count = OrgAwareGauge(
    "apex_entry_point_count",
    "Count of apex executions by entry point",
    ["entry_point", "quiddity"],
)
apex_avg_runtime = OrgAwareGauge(
    "apex_avg_runtime", "Average runtime by entry point", ["entry_point", "quiddity"]
)
apex_max_runtime = OrgAwareGauge(
    "apex_max_runtime", "Maximum runtime by entry point", ["entry_point", "quiddity"]
)
apex_total_runtime = OrgAwareGauge(
    "apex_total_runtime", "Total runtime by entry point", ["entry_point", "quiddity"]
)
apex_avg_cputime = OrgAwareGauge(
    "apex_avg_cputime", "Average CPU time by entry point", ["entry_point", "quiddity"]
)
apex_max_cputime = OrgAwareGauge(
    "apex_max_cputime", "Maximum CPU time by entry point", ["entry_point", "quiddity"]
)
apex_runtime_gt_5s_count = OrgAwareGauge(
    "apex_runtime_gt_5s_count",
    "Count of apex executions with runtime > threshold (configurable via LONG_RUNNING_APEX_MS)",
    ["entry_point", "quiddity"],
)
apex_runtime_gt_10s_count = OrgAwareGauge(
    "apex_runtime_gt_10s_count",
    "Count of apex executions with runtime > threshold (configurable via VERY_LONG_RUNNING_APEX_MS)",
    ["entry_point", "quiddity"],
)
apex_runtime_gt_5s_percentage = OrgAwareGauge(
    "apex_runtime_gt_5s_percentage",
    "Percentage of apex executions with runtime > threshold",
    ["entry_point", "quiddity"],
)

# Apex Jobs - Concurrent Errors
top_apex_concurrent_errors_sorted_by_avg_runtime = OrgAwareGauge(
    "most_apex_concurrent_errors_sorted_by_runtime",
    "Top Long Running Requests by Average Runtime with Runtime > threshold",
    ["entry_point", "count", "avg_exec_time", "avg_db_time"],
)
top_apex_concurrent_errors_sorted_by_count = OrgAwareGauge(
    "most_apex_concurrent_errors_sorted_by_count",
    "Top Long Running Requests by Count with Runtime > threshold",
    ["entry_point", "avg_run_time", "avg_exec_time", "avg_db_time"],
)
concurrent_errors_count_gauge = OrgAwareGauge(
    "concurrent_request_error_count",
    "Count of non-blank REQUEST_ID entries in CSV file",
    ["event_type"],
)

# Apex Jobs - Exceptions
apex_exception_details_gauge = OrgAwareGauge(
    "apex_exception_details",
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
    "apex_exception_category_count",
    "Total count of Apex exceptions by category",
    ["exception_category"],
)

# Apex Flex Queue
apex_flex_queue = OrgAwareGauge(
    "apex_flex_queue", "Jobs in holding status flex queue", ["id", "ApexClassId"]
)
