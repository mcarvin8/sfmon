"""
Bulk API functions.
"""
from collections import defaultdict

from cloudwatch_logging import logger
from gauges import (
    daily_batch_count_metric, daily_entity_type_count_metric,
    hourly_batch_count_metric, hourly_entity_type_count_metric
)
from log_parser import parse_logs


def daily_analyse_bulk_api(sf):
    """
    Analyse Daily Bulk API usage and report metrics.
    """
    logger.info("Getting Daily Bulk API details...")
    try:
        log_query = """
            SELECT Id FROM EventLogFile 
            WHERE EventType = 'BulkAPI' AND Interval = 'Daily' 
            ORDER BY LogDate DESC LIMIT 1
        """
        bulk_api_logs = parse_logs(sf, log_query)

        process_bulk_api_logs(
            bulk_api_logs,
            batch_metric=daily_batch_count_metric,
            entity_metric=daily_entity_type_count_metric
        )
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("An unexpected error occurred in daily_analyse_bulk_api: %s", e)


def hourly_analyse_bulk_api(sf):
    """
    Analyse Hourly Bulk API usage and report metrics.
    """
    logger.info("Getting Hourly Bulk API details...")
    try:
        log_query = """
            SELECT Id FROM EventLogFile 
            WHERE EventType = 'BulkAPI' AND Interval = 'Hourly' 
            ORDER BY LogDate DESC LIMIT 1
        """
        bulk_api_logs = parse_logs(sf, log_query)

        process_bulk_api_logs(
            bulk_api_logs,
            batch_metric=hourly_batch_count_metric,
            entity_metric=hourly_entity_type_count_metric
        )
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("An unexpected error occurred in hourly_analyse_bulk_api: %s", e)


def process_bulk_api_logs(bulk_api_logs, batch_metric, entity_metric):
    """
    Common logic to process bulk API logs and update CloudWatch metrics.

    Args:
        bulk_api_logs (list): List of parsed bulk API logs.
        batch_metric: Prometheus gauge metric for batch counts.
        entity_metric: Prometheus gauge metric for entity counts.
    """
    batch_counts = defaultdict(int)
    total_records_failed = defaultdict(int)
    total_records_processed = defaultdict(int)
    entity_type_counts = defaultdict(int)

    for row in bulk_api_logs:
        if not is_valid_entity(row):
            continue

        job_id = row.get('JOB_ID')
        user_id = row.get('USER_ID')
        entity_type = row.get('ENTITY_TYPE')
        operation_type = row.get('OPERATION_TYPE')
        rows_processed = safe_int(row.get('ROWS_PROCESSED'))
        number_failures = safe_int(row.get('NUMBER_FAILURES'))

        batch_counts[(job_id, user_id, entity_type)] += 1
        total_records_failed[(job_id, user_id, entity_type)] += number_failures
        total_records_processed[(job_id, user_id, entity_type)] += rows_processed
        entity_type_counts[(user_id, operation_type, entity_type)] += 1

    report_batch_counts(batch_counts, total_records_failed, total_records_processed, batch_metric)
    report_entity_counts(entity_type_counts, entity_metric)


def is_valid_entity(row):
    """
    Check if entity type is valid (not empty or 'none').

    Args:
        row (dict): A single log record.

    Returns:
        bool: True if entity type is valid, else False.
    """
    entity_type = row.get('ENTITY_TYPE')
    return entity_type and entity_type.lower() != 'none'


def safe_int(value):
    """
    Safely convert a value to integer, return 0 if invalid.

    Args:
        value (str): String to convert.

    Returns:
        int: Converted integer or 0.
    """
    return int(value) if value and str(value).isdigit() else 0


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
            total_records_processed=processed_counts[key]
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
            user_id=user_id,
            operation_type=operation_type,
            entity_type=entity_type
        ).set(count)
