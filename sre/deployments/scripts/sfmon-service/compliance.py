"""
    Compliance functions.
"""
from datetime import datetime, timedelta
import re

import pytz

from constants import QUERY_TIMEOUT_SECONDS, EXCLUDE_USERS, ALLOWED_SECTIONS_ACTIONS
from cloudwatch_logging import logger
from log_parser import parse_logs
from gauges import (hourly_large_query_metric, suspicious_records_gauge,
                    dev_email_deliverability_change_gauge,
                    fullqa_email_deliverability_change_gauge,
                    fullqab_email_deliverability_change_gauge)


def get_user_name(sf, user_id):
    """
    Helper function to fetch user name by user ID.
    """
    try:
        query = f"SELECT Name FROM User WHERE Id = '{user_id}'"
        result = sf.query(query, timeout=QUERY_TIMEOUT_SECONDS)
        return result['records'][0]['Name'] if result['records'] else 'Unknown User'
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
        result = sf.query(audittrail_query, timeout=QUERY_TIMEOUT_SECONDS)

        process_suspicious_records(result.get('records', []))
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("An unexpected error occurred during monitoring suspicious records: %s", e)


def get_time_threshold(minutes):
    '''Returns a formatted string of the time threshold
    for the last specified number of minutes in PST timezone.'''
    pst_timezone = pytz.timezone('US/Pacific')
    current_time = datetime.now(pst_timezone)
    time_threshold = current_time - timedelta(minutes=minutes)

    return time_threshold.strftime("%Y-%m-%dT%H:%M:%S%z")


def process_env_records(sf_instance, email_deliverability_change_query, gauge, environment):
    """Process records for a specific Salesforce environment."""
    records = sf_instance.query(email_deliverability_change_query, timeout=QUERY_TIMEOUT_SECONDS)

    if records['records']:
        for record in records['records']:
            display_value = record.get('Display', '')
            # Filter records based on specific display values
            # if display_value.strip().lower() in [
            #     "changed access to send email level from no access to all email".lower(),
            #     "changed access to send email level from no access to system email only".lower()
            # ]:
            if re.match(r"Changed Access to Send Email level from No access to (All email|System email only)", display_value):
                record_data = extract_record_data(record)
                expose_record_metric(gauge, record_data)
            else:
                logger.info("Skipping record in %s due to unmatched display value: %s",
                            environment, display_value)
    else:
        logger.info("No email deliverability change found in %s.", environment)
        gauge.labels(
            action='N/A',
            section='N/A',
            user='N/A',
            created_date='N/A',
            display='N/A',
            delegate_user='N/A'
        ).set(0)


def track_email_deliverability_change(sf_dev, sf_fqa, sf_fqab, minutes):
    '''
    monitor email deliverability change
    '''
    logger.info("Track Email Deliverability Change...")

    time_threshold_str = get_time_threshold(minutes)

    try:
        dev_email_deliverability_change_gauge.clear()
        fullqa_email_deliverability_change_gauge.clear()
        fullqab_email_deliverability_change_gauge.clear()

        email_deliverability_change_query = (
                f"SELECT Action, Section, CreatedById, CreatedBy.Name, CreatedDate, Display, DelegateUser "
                f"FROM SetupAuditTrail WHERE Action='sendEmailAccessControl' AND CreatedDate > {time_threshold_str} "
                f"ORDER BY CreatedDate DESC"
            )

        process_env_records(sf_dev,
                            email_deliverability_change_query,
                            dev_email_deliverability_change_gauge,
                            "Dev")
        process_env_records(sf_fqa,
                            email_deliverability_change_query,
                            fullqa_email_deliverability_change_gauge,
                            "FullQA")
        process_env_records(sf_fqab,
                            email_deliverability_change_query,
                            fullqab_email_deliverability_change_gauge,
                            "FullQAB")
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("An error occurred in track_email_deliverability_change : %s", e)
