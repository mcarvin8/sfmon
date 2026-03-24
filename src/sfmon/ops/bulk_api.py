"""
Bulk API Monitoring Module

This module monitors Salesforce Bulk API 1.0 and Bulk API 2.0 usage patterns by analyzing
BulkAPI and BulkAPI2 EventLogFile records. It tracks batch operations, entity types, and
success/failure rates for both daily and hourly intervals to identify bulk data processing
patterns and potential issues.

Key Metrics:
    - Batch counts per job, user, and entity type
    - Total records processed and failed per batch
    - Entity type operation counts (insert, update, delete, etc.)
    - User-level bulk API activity tracking

Functions:
    - daily_analyse_bulk_api: Analyzes daily Bulk API logs
    - hourly_analyse_bulk_api: Analyzes hourly Bulk API logs
    - process_bulk_api_logs: Common processing logic for log analysis
    - is_valid_entity: Validates entity type in log records
    - safe_int / int_from_row: Parse numeric CSV fields (supports Bulk 1.0 vs 2.0 columns)
    - report_batch_counts: Reports batch-level metrics to Prometheus
    - report_entity_counts: Reports entity-level metrics to Prometheus

Use Cases:
    - Identifying heavy Bulk API users
    - Tracking batch failure rates
    - Monitoring specific entity type operations
    - Detecting unusual bulk data processing patterns
"""

from collections import defaultdict

from logger import logger
from gauges import (
    daily_batch_count_metric,
    daily_bulk_api2_batch_count_metric,
    daily_bulk_api2_entity_type_count_metric,
    daily_entity_type_count_metric,
    hourly_batch_count_metric,
    hourly_bulk_api2_batch_count_metric,
    hourly_bulk_api2_entity_type_count_metric,
    hourly_entity_type_count_metric,
)
from log_parser import fetch_event_log_csv_reader
from query import query_records_all

# BulkAPI (1.0) CSV uses ROWS_PROCESSED / NUMBER_FAILURES. BulkAPI2 column names vary by
# release and operation (ingest vs query); some orgs use names that match the Bulk 2.0
# REST job fields, others only populate ROWS_* style fields. We resolve the active column
# once from the CSV header (see _resolve_elf_column).
_PROCESSED_FIELD_KEYS = {
    "BulkAPI": ("ROWS_PROCESSED",),
    "BulkAPI2": (),
}
_FAILED_FIELD_KEYS = {
    "BulkAPI": ("NUMBER_FAILURES",),
    "BulkAPI2": (),
}

# Ordered lists: first header present in the log file (after normalization) wins.
# Standard BulkAPI2 EventLogFile CSVs use RECORDS_PROCESSED / RECORDS_FAILED; other names
# remain for older or variant org exports (ROWS_*, NUMBER_*).
_BULK_API2_PROCESSED_HEADER_CANDIDATES = (
    "RECORDS_PROCESSED",
    "NUMBER_RECORDS_PROCESSED",
    "ROWS_PROCESSED",
    "ROWS_READ",
    "ROWS_WRITTEN",
    "ROWS_LOADED",
    "ROWS_INSERTED",
    "ROWS_UPDATED",
    "ROWS_DELETED",
    "ROWS_UPSERTED",
    "TOTAL_ROWS",
    "ROW_COUNT",
    "RECORD_COUNT",
    "BATCH_SIZE",
    "RECORDS_IN_BATCH",
)
_BULK_API2_FAILED_HEADER_CANDIDATES = (
    "RECORDS_FAILED",
    "NUMBER_RECORDS_FAILED",
    "NUMBER_FAILURES",
    "ROWS_FAILED",
    "FAILED_RECORDS",
    "NUMBER_ERRORS",
    "NUM_ERRORS",
    "ROWS_WITH_ERRORS",
    "RECORDS_WITH_ERRORS",
)


def daily_analyse_bulk_api(sf):
    """
    Analyse Daily Bulk API 1.0 and 2.0 usage and report metrics.
    """
    _run_bulk_log_analysis(
        sf,
        event_type="BulkAPI",
        interval="Daily",
        batch_metric=daily_batch_count_metric,
        entity_metric=daily_entity_type_count_metric,
        log_label="Bulk API 1.0",
    )
    _run_bulk_log_analysis(
        sf,
        event_type="BulkAPI2",
        interval="Daily",
        batch_metric=daily_bulk_api2_batch_count_metric,
        entity_metric=daily_bulk_api2_entity_type_count_metric,
        log_label="Bulk API 2.0",
    )


def hourly_analyse_bulk_api(sf):
    """
    Analyse Hourly Bulk API 1.0 and 2.0 usage and report metrics.
    """
    _run_bulk_log_analysis(
        sf,
        event_type="BulkAPI",
        interval="Hourly",
        batch_metric=hourly_batch_count_metric,
        entity_metric=hourly_entity_type_count_metric,
        log_label="Bulk API 1.0",
    )
    _run_bulk_log_analysis(
        sf,
        event_type="BulkAPI2",
        interval="Hourly",
        batch_metric=hourly_bulk_api2_batch_count_metric,
        entity_metric=hourly_bulk_api2_entity_type_count_metric,
        log_label="Bulk API 2.0",
    )


def _run_bulk_log_analysis(
    sf, event_type, interval, batch_metric, entity_metric, log_label
):
    """
    Fetch the latest EventLogFile for an event type and interval, then emit metrics.
    """
    logger.info("Getting %s %s details...", interval, log_label)
    # pylint: disable=broad-except
    try:
        log_query = f"""
            SELECT Id, LogFileFieldNames FROM EventLogFile
            WHERE EventType = '{event_type}' AND Interval = '{interval}'
            ORDER BY LogDate DESC LIMIT 1
        """
        rows = query_records_all(sf, log_query)
        if not rows:
            return
        log_row = rows[0]
        bulk_api_logs = fetch_event_log_csv_reader(sf, log_row["Id"])
        declared_fields = log_row.get("LogFileFieldNames")

        process_bulk_api_logs(
            bulk_api_logs,
            batch_metric=batch_metric,
            entity_metric=entity_metric,
            event_type=event_type,
            processed_keys=_PROCESSED_FIELD_KEYS[event_type],
            failed_keys=_FAILED_FIELD_KEYS[event_type],
            declared_log_field_names=declared_fields,
        )
    except Exception as e:
        logger.error(
            "An unexpected error occurred in %s %s analysis: %s",
            interval.lower(),
            log_label,
            e,
        )


def process_bulk_api_logs(
    bulk_api_logs,
    batch_metric,
    entity_metric,
    event_type="BulkAPI",
    processed_keys=("ROWS_PROCESSED",),
    failed_keys=("NUMBER_FAILURES",),
    declared_log_field_names=None,
):
    """
    Common logic to process bulk API logs and update CloudWatch metrics.

    Args:
        bulk_api_logs (list): List of parsed bulk API logs.
        batch_metric: Prometheus gauge metric for batch counts.
        entity_metric: Prometheus gauge metric for entity counts.
        event_type: BulkAPI or BulkAPI2; drives how count columns are resolved from headers.
        processed_keys: CSV column names to try in order for successful row counts (BulkAPI).
        failed_keys: CSV column names to try in order for failure counts (BulkAPI).
        declared_log_field_names: EventLogFile.LogFileFieldNames (for diagnostics).
    """
    if bulk_api_logs is None:
        return

    batch_counts = defaultdict(int)
    total_records_failed = defaultdict(int)
    total_records_processed = defaultdict(int)
    entity_type_counts = defaultdict(int)

    batch_metric.clear()
    entity_metric.clear()

    processed_col = None
    failed_col = None
    fieldnames = list(bulk_api_logs.fieldnames or [])
    if event_type == "BulkAPI2":
        materialized = [r for r in bulk_api_logs if is_valid_entity(r)]
        processed_col = _resolve_elf_column(
            fieldnames, _BULK_API2_PROCESSED_HEADER_CANDIDATES
        ) or _resolve_elf_column_fuzzy(
            fieldnames,
            (
                "RECORDS_PROCESSED",
                "NUMBER_RECORDS_PROCESSED",
                "ROWS_PROCESSED",
                "ROWS_READ",
                "ROWS_WRITTEN",
                "ROWS_LOADED",
                "TOTAL_ROWS",
            ),
        )
        failed_col = _resolve_elf_column(
            fieldnames, _BULK_API2_FAILED_HEADER_CANDIDATES
        ) or _resolve_elf_column_fuzzy(
            fieldnames,
            (
                "RECORDS_FAILED",
                "NUMBER_RECORDS_FAILED",
                "NUMBER_FAILURES",
                "ROWS_FAILED",
                "RECORDS_WITH_ERRORS",
            ),
        )
        if materialized:
            pre_processed = (
                sum(safe_int(r.get(processed_col)) for r in materialized)
                if processed_col
                else 0
            )
            if pre_processed == 0:
                inferred = _infer_numeric_count_column(
                    materialized, fieldnames, failures=False
                )
                if inferred:
                    processed_col = inferred
            pre_failed = (
                sum(safe_int(r.get(failed_col)) for r in materialized) if failed_col else 0
            )
            if pre_failed == 0:
                inferred_f = _infer_numeric_count_column(
                    materialized, fieldnames, failures=True
                )
                if inferred_f:
                    failed_col = inferred_f
        row_iter = materialized
    else:
        row_iter = bulk_api_logs

    for row in row_iter:
        if event_type != "BulkAPI2" and not is_valid_entity(row):
            continue

        job_id = row.get("JOB_ID")
        user_id = row.get("USER_ID")
        entity_type = row.get("ENTITY_TYPE")
        operation_type = row.get("OPERATION_TYPE")
        if event_type == "BulkAPI2":
            rows_processed = safe_int(row.get(processed_col)) if processed_col else 0
            number_failures = safe_int(row.get(failed_col)) if failed_col else 0
        else:
            rows_processed = int_from_row(row, processed_keys)
            number_failures = int_from_row(row, failed_keys)

        batch_counts[(job_id, user_id, entity_type)] += 1
        total_records_failed[(job_id, user_id, entity_type)] += number_failures
        total_records_processed[(job_id, user_id, entity_type)] += rows_processed
        entity_type_counts[(user_id, operation_type, entity_type)] += 1

    if (
        event_type == "BulkAPI2"
        and batch_counts
        and not any(total_records_processed.values())
        and not any(total_records_failed.values())
    ):
        logger.warning(
            "BulkAPI2 log has batch rows but zero summed record counts "
            "(resolved processed=%r failed=%r; csv_headers=%s; "
            "LogFileFieldNames=%r)",
            processed_col,
            failed_col,
            fieldnames,
            declared_log_field_names,
        )

    report_batch_counts(
        batch_counts, total_records_failed, total_records_processed, batch_metric
    )
    report_entity_counts(entity_type_counts, entity_metric)


def is_valid_entity(row):
    """
    Check if entity type is valid (not empty or 'none').

    Args:
        row (dict): A single log record.

    Returns:
        bool: True if entity type is valid, else False.
    """
    entity_type = row.get("ENTITY_TYPE")
    return entity_type and entity_type.lower() != "none"


def _normalize_elf_header(name):
    """Event log CSV headers: trim, strip BOM, spaces → underscores, uppercase."""
    if not name:
        return ""
    return (name or "").lstrip("\ufeff").strip().replace(" ", "_").upper()


def _resolve_elf_column(fieldnames, candidates):
    """
    Pick the first candidate that matches a column in fieldnames (case/space insensitive).
    """
    if not fieldnames:
        return None
    by_norm = {}
    for fn in fieldnames:
        if not fn:
            continue
        norm = _normalize_elf_header(fn)
        if norm:
            by_norm[norm] = fn
    for cand in candidates:
        orig = by_norm.get(cand)
        if orig:
            return orig
    return None


def _resolve_elf_column_fuzzy(fieldnames, substrings_in_order):
    """
    First column whose normalized header contains one of the substrings (in order).
    """
    if not fieldnames:
        return None
    normalized = [
        (_normalize_elf_header(f), f) for f in fieldnames if f and _normalize_elf_header(f)
    ]
    for sub in substrings_in_order:
        subu = sub.upper()
        for hdr_u, orig in normalized:
            if subu in hdr_u:
                return orig
    return None


# Columns never used for inferred volume totals (IDs, timestamps, enums as strings, etc.).
_BULK_API2_SKIP_INFER_HEADERS = frozenset(
    {
        "ADDITIONAL_INFO",
        "API_TYPE",
        "APP_NAME",
        "CLIENT_IP",
        "ENTITY_TYPE",
        "EVENT_TYPE",
        "JOB_ID",
        "LOGIN_KEY",
        "OPERATION_TYPE",
        "ORGANIZATION_ID",
        "REQUEST_ID",
        "RESULT_SIZE_MB",
        "REQUEST_STATUS",
        "SESSION_KEY",
        "THREAD_ID",
        "TIMESTAMP",
        "URI",
        "USER_AGENT",
        "USER_ID",
    }
)


def _infer_numeric_count_column(rows, fieldnames, failures):
    """
    When headers are unknown, pick the column whose integer values sum highest on materialized rows.
    """
    if not rows or not fieldnames:
        return None
    best_col = None
    best_total = -1
    for fn in fieldnames:
        if not fn:
            continue
        nu = _normalize_elf_header(fn)
        if not nu or nu in _BULK_API2_SKIP_INFER_HEADERS:
            continue
        if failures:
            if not any(t in nu for t in ("FAIL", "ERROR")):
                continue
        else:
            if any(t in nu for t in ("FAIL", "ERROR")):
                continue
            if not any(
                t in nu
                for t in (
                    "ROW",
                    "RECORD",
                    "COUNT",
                    "NUMBER",
                    "BATCH",
                    "READ",
                    "LOAD",
                    "WRITE",
                    "SIZE",
                )
            ):
                continue
        total = sum(safe_int(r.get(fn)) for r in rows)
        if total > best_total:
            best_total = total
            best_col = fn
    return best_col if best_total > 0 else None


def safe_int(value):
    """
    Safely convert a value to integer, return 0 if invalid.

    Args:
        value (str): String to convert.

    Returns:
        int: Converted integer or 0.
    """
    if value is None:
        return 0
    s = str(value).strip().replace(",", "")
    if not s:
        return 0
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return 0


def int_from_row(row, keys):
    """First non-blank value among keys, parsed as int (see safe_int)."""
    for key in keys:
        if key not in row:
            continue
        raw = row[key]
        if raw is None:
            continue
        if isinstance(raw, str) and not raw.strip():
            continue
        return safe_int(raw)
    return 0


def report_batch_counts(batch_counts, failed_counts, processed_counts, metric):
    """
    Report batch-level bulk API metrics.

    Args:
        batch_counts (dict): Batch counts per (job_id, user_id, entity_type).
        failed_counts (dict): Total failures per batch key.
        processed_counts (dict): Total records processed per batch key.
        metric: Prometheus gauge metric to update.
    """
    for key, count in batch_counts.items():
        job_id, user_id, entity_type = key
        metric.labels(
            job_id=job_id,
            user_id=user_id,
            entity_type=entity_type,
            total_records_failed=failed_counts[key],
            total_records_processed=processed_counts[key],
        ).set(count)


def report_entity_counts(entity_type_counts, metric):
    """
    Report entity-type level bulk API metrics.

    Args:
        entity_type_counts (dict): Entity type counts per (user_id, operation_type, entity_type).
        metric: Prometheus gauge metric to update.
    """
    for (user_id, operation_type, entity_type), count in entity_type_counts.items():
        metric.labels(
            user_id=user_id, operation_type=operation_type, entity_type=entity_type
        ).set(count)
