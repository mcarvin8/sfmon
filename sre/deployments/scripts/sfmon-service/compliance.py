"""
    Compliance functions.
"""
from constants import QUERY_TIMEOUT_SECONDS, EXCLUDE_USERS, ALLOWED_SECTIONS_ACTIONS
from cloudwatch_logging import logger
from log_parser import parse_logs
from gauges import hourly_large_query_metric, suspicious_records_gauge


def get_user_name(sf, user_id):
    """
    Helper function to fetch user name by user ID.
    """
    try:
        query = f"SELECT Name FROM User WHERE Id = '{user_id}'"
        result = sf.query(query, timeout=QUERY_TIMEOUT_SECONDS)
        return result['records'][0]['Name'] if result['records'] else 'Unknown User'
    except Exception as e:
        logger.error("Error fetching user name for ID %s: %s", user_id, e)
        return 'Unknown User'


def hourly_observe_user_querying_large_records(sf):
    '''
    Observe user activity who querries more than 10k records
    '''
    logger.info("Getting Compliance data - User details querying large records...")

    try:
        log_query = (
            "SELECT Id FROM EventLogFile WHERE EventType = 'API' and Interval = 'Hourly' "
            "ORDER BY LogDate DESC LIMIT 1")

        api_log_records = parse_logs(sf, log_query)
        large_query_counts = {}

        hourly_large_query_metric.clear()

        for row in api_log_records:
            rows_processed = int(row['ROWS_PROCESSED']) if row['ROWS_PROCESSED'].isdigit() else 0

            if rows_processed > 10000:
                user_id = row['USER_ID'] if row['USER_ID'] else None
                method = row['METHOD_NAME'] if row['METHOD_NAME'] else None
                entity_name = row['ENTITY_NAME'] if row['ENTITY_NAME'] else None

                if not user_id:
                    continue

                user_name = get_user_name(sf, user_id)

                key = (user_id, user_name, method, entity_name, rows_processed)
                large_query_counts[key] = large_query_counts.get(key, 0) + 1

        for (user_id, user_name, method, entity_name, rows_processed), count in large_query_counts.items():
            hourly_large_query_metric.labels(
                user_id=user_id,user_name=user_name,
                method=method,entity_name=entity_name,
                rows_processed=rows_processed
            ).set(count)

    except Exception as e:
        logger.error("An error occurred in hourly_observe_user_querying_large_records : %s", e)


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


def expose_record_metric(record_data):
    """Expose the record data as a metric."""
    suspicious_records_gauge.labels(**record_data).set(1)


def process_suspicious_records(records):
    """Process records of audit trail logs."""
    for record in records:
        if not is_allowed_action(record):
            record_data = extract_record_data(record)
            expose_record_metric(record_data)


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

    except Exception as e:
        logger.error("An unexpected error occurred during monitoring suspicious records: %s", e)
