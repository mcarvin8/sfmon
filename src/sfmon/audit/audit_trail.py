"""
SetupAuditTrail Monitoring Module

This module monitors SetupAuditTrail records for suspicious or non-compliant
configuration changes. It identifies changes that are not in the predefined
allowed actions list and exposes them as Prometheus metrics.

Functions:
    - expose_suspicious_records: Main monitoring function
    - build_audit_trail_query: Constructs SOQL query
    - extract_record_data: Normalizes audit trail record data
    - expose_record_metric: Exposes record as Prometheus metric
    - process_suspicious_records: Processes and flags suspicious changes
    - is_allowed_action: Validates if action is in allowed list
    - query_setup_audit_trail: Fetches audit trail records
"""
from constants import ALLOWED_SECTIONS_ACTIONS
from .utils import categorize_user_group
from logger import logger
from gauges import suspicious_records_gauge
from query import query_records_all


def build_audit_trail_query():
    """Build the Salesforce audit trail query string.
    
    Note: No longer excludes users - all records are returned for filtering
    by user_group in Grafana dashboards.
    """
    return """
        SELECT Action, Section, CreatedById, CreatedBy.Name, 
               CreatedDate, Display, DelegateUser 
        FROM SetupAuditTrail 
        WHERE CreatedDate=YESTERDAY
        ORDER BY CreatedDate DESC
    """


def extract_record_data(record):
    """Extract and normalize record data with user group categorization."""
    user_name = (record.get('CreatedBy', {}).get('Name', 'Unknown') 
                if isinstance(record.get('CreatedBy'), dict) else 'Unknown')
    
    return {
        'action': record.get('Action', 'Unknown'),
        'section': record.get('Section', 'Unknown'),
        'user': user_name,
        'user_group': categorize_user_group(user_name),
        'created_date': record.get('CreatedDate', 'Unknown'),
        'display': record.get('Display', 'Unknown'),
        'delegate_user': record.get('DelegateUser', 'Unknown')
    }


def expose_record_metric(gauge, record_data):
    """Expose the record data as a metric."""
    gauge.labels(**record_data).set(1)


def process_suspicious_records(records):
    """Process records of audit trail logs."""
    has_suspicious_records = False
    if records:
        for record in records:
            if not is_allowed_action(record):
                record_data = extract_record_data(record)
                expose_record_metric(suspicious_records_gauge, record_data)
                has_suspicious_records = True
    
    # Ensure metric is visible even when there are no suspicious records
    if not has_suspicious_records:
        suspicious_records_gauge.labels(
            action='none',
            section='none',
            user='No Suspicious Records',
            user_group='Other',
            created_date='none',
            display='none',
            delegate_user='none'
        ).set(0)


def is_allowed_action(record):
    """Determines if particular action is allowed based on predefined allowed actions.
    
    Note: All actions are now tracked with user_group labels for filtering.
    This function only determines if an action is suspicious (not in allowed list).
    """
    action = record.get('Action', 'Unknown')
    section = record.get('Section', 'Unknown')

    allowed_actions = ALLOWED_SECTIONS_ACTIONS.get(section, [])
    return action.lower() in [a.lower() for a in allowed_actions]


def expose_suspicious_records(sf):
    '''
    Monitor Audit Trail logs and expose non-compliant change records.
    
    All records are now tracked with user_group labels, allowing filtering
    in Grafana dashboards to distinguish between admin groups and non-admins.
    '''
    logger.info("Getting Audit Trail logs...")

    try:
        suspicious_records_gauge.clear()
        audittrail_query = build_audit_trail_query()
        result = query_records_all(sf, audittrail_query)

        process_suspicious_records(result)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("An unexpected error occurred during monitoring suspicious records: %s", e)


def query_setup_audit_trail(sf):
    '''
    Fetch audit trail records from yesterday's date.
    '''
    soql_query = "SELECT Action, CreatedById, CreatedDate, Display, Section FROM SetupAuditTrail WHERE CreatedDate=YESTERDAY ORDER BY CreatedDate DESC"
    result = query_records_all(sf, soql_query)
    return result
