"""
Large Query Monitoring Module

This module monitors users who query more than a configurable threshold of records per hour
by analyzing API EventLogFile records. It identifies potentially risky
data extraction activities for compliance monitoring.

Environment Variables:
    - LARGE_QUERY_THRESHOLD: Number of rows that constitutes a "large query" (default: 10000)

Functions:
    - hourly_observe_user_querying_large_records: Main monitoring function
    - collect_large_queries: Collects queries exceeding threshold
    - is_large_query: Checks if query exceeds threshold
    - report_large_queries: Exposes metrics to Prometheus
"""
import os

from .utils import get_user_name
from logger import logger
from log_parser import parse_logs
from gauges import hourly_large_query_metric

# Number of rows that constitutes a "large query"
LARGE_QUERY_THRESHOLD = int(os.getenv('LARGE_QUERY_THRESHOLD', 10000))


def hourly_observe_user_querying_large_records(sf):
    """
    Observe and record users who query more than the configured threshold of records hourly.
    The threshold is configurable via LARGE_QUERY_THRESHOLD environment variable.

    Args:
        sf: Salesforce connection object.
    """
    logger.info("Getting Compliance data - User details querying large records (>%d rows)...", LARGE_QUERY_THRESHOLD)

    try:
        large_queries = collect_large_queries(sf)
        report_large_queries(large_queries)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("An error occurred in hourly_observe_user_querying_large_records: %s", e)


def collect_large_queries(sf):
    """
    Collect queries processing more than the configured threshold of records.
    The threshold is configurable via LARGE_QUERY_THRESHOLD environment variable.

    Args:
        sf: Salesforce connection object.

    Returns:
        set: Tuples of (user_id, user_name, method, entity_name, rows_processed).
    """
    log_query = (
        "SELECT Id FROM EventLogFile WHERE EventType = 'API' and Interval = 'Hourly' "
        "ORDER BY LogDate DESC LIMIT 1"
    )

    api_log_records = parse_logs(sf, log_query)
    large_queries = set()

    if api_log_records:
        for row in api_log_records:
            if not is_large_query(row):
                continue

            user_id = row.get('USER_ID')
            if not user_id:
                continue

            user_name = get_user_name(sf, user_id)
            large_queries.add((
                user_id,
                user_name,
                row.get('METHOD_NAME'),
                row.get('ENTITY_NAME'),
                int(row.get('ROWS_PROCESSED', 0))
            ))

    return large_queries


def is_large_query(row):
    """
    Check if a log record processes more than the configured threshold of rows.
    The threshold is configurable via LARGE_QUERY_THRESHOLD environment variable.

    Args:
        row (dict): Parsed log row.

    Returns:
        bool: True if rows_processed exceeds LARGE_QUERY_THRESHOLD.
    """
    rows_processed = row.get('ROWS_PROCESSED', '')
    return rows_processed.isdigit() and int(rows_processed) > LARGE_QUERY_THRESHOLD


def report_large_queries(large_queries):
    """
    Report large queries to Prometheus gauge.

    Args:
        large_queries (set): Set of large query tuples.
    """
    hourly_large_query_metric.clear()
    if large_queries:
        for user_id, user_name, method, entity_name, rows_processed in large_queries:
            hourly_large_query_metric.labels(
                user_id=user_id,
                user_name=user_name,
                method=method,
                entity_name=entity_name
            ).set(rows_processed)
    else:
        # Ensure metric is visible even when there are no large queries
        hourly_large_query_metric.labels(
            user_id='none',
            user_name='No Large Queries',
            method='none',
            entity_name='none'
        ).set(0)
