"""
    Bulk API functions.
"""
from collections import defaultdict

from cloudwatch_logging import logger
from gauges import daily_batch_count_metric, daily_entity_type_count_metric, hourly_batch_count_metric, hourly_entity_type_count_metric
from log_parser import parse_logs


def daily_analyse_bulk_api(sf):
    """
    Analyse Bulk API usage with respect to user_id, entity_type, operation_type, number of rows processed, number of failures.
    """

    logger.info("Getting Daily Bulk API details...")
    try:
        log_query = (
            "SELECT Id FROM EventLogFile WHERE EventType = 'BulkAPI' and Interval = 'Daily' "
            "ORDER BY LogDate DESC LIMIT 1")

        bulk_api_logs = parse_logs(sf, log_query)

        batch_counts = defaultdict(int)
        total_records_failed = defaultdict(int)
        total_records_processed = defaultdict(int)
        entity_type_counts = defaultdict(int)

        for row in bulk_api_logs:
            job_id = row['JOB_ID'] if row['JOB_ID'] else None
            user_id = row['USER_ID']
            entity_type = row['ENTITY_TYPE'] if row['ENTITY_TYPE'] else None
            operation_type = row['OPERATION_TYPE'] if row['OPERATION_TYPE'] else None
            rows_processed = int(row['ROWS_PROCESSED']) if row['ROWS_PROCESSED'].isdigit() else 0
            number_failures = int(row['NUMBER_FAILURES']) if row['NUMBER_FAILURES'].isdigit() else 0

            if not entity_type or entity_type.lower() == 'none':
                continue

            batch_counts[(job_id, user_id, entity_type)] += 1
            total_records_failed[(job_id, user_id, entity_type)] += number_failures
            total_records_processed[(job_id, user_id, entity_type)] += rows_processed
            entity_type_counts[(user_id, operation_type, entity_type)] += 1

        for key, count in batch_counts.items():
            job_id, user_id, entity_type = key
            daily_batch_count_metric.labels(
                job_id=job_id, user_id=user_id, entity_type=entity_type,
                total_records_failed=total_records_failed[key],
                total_records_processed=total_records_processed[key]).set(count)

        for (user_id, operation_type, entity_type), count in entity_type_counts.items():
            daily_entity_type_count_metric.labels(user_id=user_id, operation_type=operation_type, entity_type=entity_type).set(count)

    except Exception as e:
        logger.error("An unexpected error occurred in daily_analyse_bulk_api : %s", e)


def hourly_analyse_bulk_api(sf):
    """
    Analyse Bulk API usage with respect to user_id, entity_type, operation_type, number of rows processed, number of failures.
    """

    logger.info("Getting Hourly based Bulk API details...")
    try:
        log_query = (
            "SELECT Id FROM EventLogFile WHERE EventType = 'BulkAPI' and Interval = 'Hourly' "
            "ORDER BY LogDate DESC LIMIT 1")

        bulk_api_logs = parse_logs(sf, log_query)

        batch_counts = defaultdict(int)
        total_records_failed = defaultdict(int)
        total_records_processed = defaultdict(int)
        entity_type_counts = defaultdict(int)

        for row in bulk_api_logs:
            job_id = row['JOB_ID'] if row['JOB_ID'] else None
            user_id = row['USER_ID']
            entity_type = row['ENTITY_TYPE'] if row['ENTITY_TYPE'] else None
            operation_type = row['OPERATION_TYPE'] if row['OPERATION_TYPE'] else None
            rows_processed = int(row['ROWS_PROCESSED']) if row['ROWS_PROCESSED'].isdigit() else 0
            number_failures = int(row['NUMBER_FAILURES']) if row['NUMBER_FAILURES'].isdigit() else 0

            if not entity_type or entity_type.lower() == 'none':
                continue

            batch_counts[(job_id, user_id, entity_type)] += 1
            total_records_failed[(job_id, user_id, entity_type)] += number_failures
            total_records_processed[(job_id, user_id, entity_type)] += rows_processed
            entity_type_counts[(user_id, operation_type, entity_type)] += 1

        for key, count in batch_counts.items():
            job_id, user_id, entity_type = key
            hourly_batch_count_metric.labels(
                job_id=job_id, user_id=user_id, entity_type=entity_type,
                total_records_failed=total_records_failed[key],
                total_records_processed=total_records_processed[key]).set(count)

        for (user_id, operation_type, entity_type), count in entity_type_counts.items():
            hourly_entity_type_count_metric.labels(user_id=user_id, operation_type=operation_type, entity_type=entity_type).set(count)

    except Exception as e:
        logger.error("An unexpected error occurred hourly_analyse_bulk_api : %s", e)
