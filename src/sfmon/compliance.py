"""
Compliance and Audit Trail Monitoring Module

This module monitors compliance-related activities in the production Salesforce org
by analyzing API EventLogFiles and SetupAuditTrail records. It identifies potentially
risky activities such as large-scale data queries and unauthorized configuration changes.

Key Compliance Checks:
    1. Large Query Monitoring: Tracks users querying > 10,000 records per hour
    2. Suspicious Setup Changes: Monitors audit trail for non-approved actions
    3. Configuration Change Tracking: Audits system modifications against allowed lists

Compliance Rules:
    - Predefined ALLOWED_SECTIONS_ACTIONS for legitimate changes
    - EXCLUDE_USERS list for admin/integration accounts
    - Automatic flagging of deviations from approved patterns

Functions:
    - get_user_name: Resolves user ID to name for reporting
    - hourly_observe_user_querying_large_records: Monitors API log for large queries
    - collect_large_queries: Aggregates query volume by user and entity
    - is_large_query: Checks if query exceeds 10k records threshold
    - report_large_queries: Exposes large query metrics
    - expose_suspicious_records: Monitors SetupAuditTrail for non-compliant changes
    - build_audit_trail_query: Constructs filtered audit trail SOQL
    - extract_record_data: Normalizes audit trail record data
    - expose_record_metric: Exposes compliance violations to Prometheus
    - process_suspicious_records: Processes and flags suspicious changes
    - is_allowed_action: Validates if action is in allowed list

Alert Triggers:
    - API queries processing > 10,000 records
    - Setup changes not in ALLOWED_SECTIONS_ACTIONS whitelist
    - Configuration modifications by non-excluded users
    - Critical section changes (e.g., Sharing Defaults, Security)
"""
from constants import EXCLUDE_USERS, ALLOWED_SECTIONS_ACTIONS
from logger import logger
from log_parser import parse_logs
from gauges import (hourly_large_query_metric, suspicious_records_gauge)
from query import query_records_all

def get_user_name(sf, user_id):
    """
    Helper function to fetch user name by user ID.
    """
    try:
        query = f"SELECT Name FROM User WHERE Id = '{user_id}'"
        result = query_records_all(sf, query)
        return result[0]['Name'] if result else 'Unknown User'
    except Exception as e: # pylint: disable=broad-except
        logger.error("Error fetching user name for ID %s: %s", user_id, e)
        return 'Unknown User'


def hourly_observe_user_querying_large_records(sf):
    """
    Observe and record users who query more than 10,000 records hourly.

    Args:
        sf: Salesforce connection object.
    """
    logger.info("Getting Compliance data - User details querying large records...")

    try:
        large_query_counts = collect_large_queries(sf)
        report_large_queries(large_query_counts)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("An error occurred in hourly_observe_user_querying_large_records: %s", e)


def collect_large_queries(sf):
    """
    Collect queries processing more than 10k records.

    Args:
        sf: Salesforce connection object.

    Returns:
        dict: Keys are (user_id, user_name, method, entity_name, rows_processed), values are counts.
    """
    log_query = (
        "SELECT Id FROM EventLogFile WHERE EventType = 'API' and Interval = 'Hourly' "
        "ORDER BY LogDate DESC LIMIT 1"
    )

    api_log_records = parse_logs(sf, log_query)
    large_query_counts = {}

    for row in api_log_records:
        if not is_large_query(row):
            continue

        user_id = row.get('USER_ID')
        if not user_id:
            continue

        user_name = get_user_name(sf, user_id)
        key = (
            user_id,
            user_name,
            row.get('METHOD_NAME'),
            row.get('ENTITY_NAME'),
            int(row.get('ROWS_PROCESSED', 0))
        )
        large_query_counts[key] = large_query_counts.get(key, 0) + 1

    return large_query_counts


def is_large_query(row):
    """
    Check if a log record processes more than 10k rows.

    Args:
        row (dict): Parsed log row.

    Returns:
        bool: True if rows_processed > 10,000.
    """
    rows_processed = row.get('ROWS_PROCESSED', '')
    return rows_processed.isdigit() and int(rows_processed) > 10000


def report_large_queries(large_query_counts):
    """
    Report large query counts to CloudWatch gauge.

    Args:
        large_query_counts (dict): Aggregated large query counts.
    """
    hourly_large_query_metric.clear()
    for (user_id, user_name, method, entity_name, rows_processed), count in large_query_counts.items():
        hourly_large_query_metric.labels(
            user_id=user_id,
            user_name=user_name,
            method=method,
            entity_name=entity_name,
            rows_processed=rows_processed
        ).set(count)


def build_audit_trail_query(excluded_user_list):
    """Build the Salesforce audit trail query string."""

    base_query = """
        SELECT Action, Section, CreatedById, CreatedBy.Name, 
               CreatedDate, Display, DelegateUser 
        FROM SetupAuditTrail 
        WHERE CreatedDate=YESTERDAY
    """

    if excluded_user_list:
        excluded_users = "', '".join(excluded_user_list)
        base_query += f" AND CreatedBy.Name NOT IN ('{excluded_users}')"

    return f"{base_query} ORDER BY CreatedDate DESC"


def extract_record_data(record):
    """Extract and normalize record data."""
    return {
        'action': record.get('Action', 'Unknown'),
        'section': record.get('Section', 'Unknown'),
        'user': (record.get('CreatedBy', {}).get('Name', 'Unknown') 
                if isinstance(record.get('CreatedBy'), dict) else 'Unknown'),
        'created_date': record.get('CreatedDate', 'Unknown'),
        'display': record.get('Display', 'Unknown'),
        'delegate_user': record.get('DelegateUser', 'Unknown')
    }


def expose_record_metric(gauge, record_data):
    """Expose the record data as a metric."""
    gauge.labels(**record_data).set(1)


def process_suspicious_records(records):
    """Process records of audit trail logs."""
    for record in records:
        if not is_allowed_action(record):
            record_data = extract_record_data(record)
            expose_record_metric(suspicious_records_gauge, record_data)


def is_allowed_action(record):
    """Determines if particular action is allowed based on predefined allowed actions"""

    action = record.get('Action', 'Unknown')
    section = record.get('Section', 'Unknown')
    user = record.get('CreatedBy', {}).get('Name', 'Unknown') if isinstance(record.get('CreatedBy'), dict) else 'Unknown'

    if user in EXCLUDE_USERS:
        return True

    allowed_actions = ALLOWED_SECTIONS_ACTIONS.get(section, [])
    return action.lower() in [a.lower() for a in allowed_actions]


def expose_suspicious_records(sf):
    '''
    monitor Audit Trail logs and expose non-compliant change record
    '''

    logger.info("Getting Audit Trail logs...")

    try:
        suspicious_records_gauge.clear()
        audittrail_query = build_audit_trail_query(EXCLUDE_USERS)
        result = query_records_all(sf, audittrail_query)

        process_suspicious_records(result)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("An unexpected error occurred during monitoring suspicious records: %s", e)
