'''
    Report export functins.
'''
from constants import QUERY_TIMEOUT_SECONDS
from cloudwatch_logging import logger
from log_parser import parse_logs
from gauges import hourly_report_export_metric
from compliance import get_user_name

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
            result = sf.query(report_detail_query, timeout=QUERY_TIMEOUT_SECONDS)

            hourly_report_export_metric.labels(
                user_name=user_name if user_name else None,
                timestamp=timestamp,
                report_name=result.get('records', [])[0].get('Name') if result.get('records') else None,
                report_type_api_name = result.get('records', [])[0].get('ReportTypeApiName') if result.get('records') else None
            ).set(1)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("An error occurred in report_export_records : %s", e)
