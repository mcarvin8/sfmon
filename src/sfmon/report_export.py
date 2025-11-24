"""
Report Export Monitoring Module

This module monitors Salesforce report export activity by analyzing ReportExport
EventLogFile records. It tracks which users are exporting reports, what types of
reports are being exported, and when exports occur. This is useful for compliance,
data security, and usage pattern analysis.

Monitoring Focus:
    - User-level report export activity
    - Report types being exported
    - Export frequency and timing patterns
    - Sensitive report identification

Functions:
    - hourly_report_export_records: Processes last hour's report export logs

Process Flow:
    1. Query hourly ReportExport EventLogFile
    2. Parse log CSV to extract export events
    3. Extract report ID from URI field
    4. Query Report object for report details (name, type)
    5. Expose metrics with user and report context

Metrics Exposed:
    - user_name: User who exported the report
    - timestamp: When the export occurred
    - report_name: Friendly name of the exported report
    - report_type_api_name: Report type for categorization

Use Cases:
    - Compliance auditing for data exports
    - Identifying frequently exported reports
    - Detecting unusual export patterns
    - Monitoring access to sensitive reports
    - Tracking report usage for optimization

Alert Triggers:
    - High-frequency exports by single user
    - Exports of sensitive report types
    - Exports outside business hours
    - Unusual export patterns
"""
from logger import logger
from log_parser import parse_logs
from gauges import hourly_report_export_metric
from compliance import get_user_name
from query import query_records_all

def hourly_report_export_records(sf):
    '''
    Query and expose report export details 
    '''
    logger.info("Getting report export records...")

    try:
        hourly_report_export_metric.clear()
        log_query = (
            "SELECT Id FROM EventLogFile WHERE EventType = 'ReportExport' and Interval = 'Hourly' ORDER BY LogDate DESC LIMIT 1")

        api_log_records = parse_logs(sf, log_query)

        for row in api_log_records:
            user_name = get_user_name(sf, row['USER_ID'])
            timestamp = row['TIMESTAMP_DERIVED']

            modified_id = row['URI'][1:] if row['URI'].startswith("/") else row['URI']

            # Add validation for the report ID format
            if not modified_id or len(modified_id) < 15:  # Salesforce IDs are typically 15 or 18 characters
                logger.warning("Invalid report ID format: %s", modified_id)
                continue

            report_detail_query = f"SELECT Id, Name, ReportTypeApiName FROM Report WHERE Id = '{modified_id}'"
            result = query_records_all(sf, report_detail_query)

            hourly_report_export_metric.labels(
                user_name=user_name if user_name else None,
                timestamp=timestamp,
                report_name=result[0].get('Name') if result and len(result) > 0 else None,
                report_type_api_name=result[0].get('ReportTypeApiName') if result and len(result) > 0 else None
            ).set(1)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("An error occurred in report_export_records : %s", e)
