"""
Salesforce EventLogFile Parser Module

This module provides utility functions for fetching and parsing Salesforce EventLogFile
records. It handles the complete workflow of querying for log files, downloading their
CSV content, and parsing them into structured data for analysis.

EventLogFile Types Supported:
    - ApexExecution: Apex code execution logs
    - ApexUnexpectedException: Apex exception logs
    - API: API usage and large query logs
    - BulkAPI: Bulk API operation logs
    - LightningPageView: Lightning page performance logs
    - ReportExport: Report export activity
    - ConcurrentLongRunningApexLimit: Concurrent Apex limit violations

Functions:
    - parse_logs: Main function that orchestrates log fetching and parsing

Process Flow:
    1. Execute SOQL query to find EventLogFile record
    2. Download CSV log file content via REST API
    3. Parse CSV into dictionary reader for iteration
    4. Return CSV reader for processing by calling modules

Error Handling:
    - Handles network request failures gracefully
    - Manages CSV parsing errors
    - Logs detailed error information for debugging
    - Returns None on any failure to allow calling code to handle gracefully

Requirements:
    - Valid Salesforce connection with API access
    - EventLogFile object read permissions
    - Sufficient API calls for log downloads
"""
import csv
from io import StringIO
import requests

from constants import REQUESTS_TIMEOUT_SECONDS
from logger import logger
from query import query_records_all


def parse_logs(sf, log_query):
    """
    Fetch and parse logs from given query
    """
    try:
        event_log_records = query_records_all(sf, log_query)
        if not event_log_records:
            return None

        log_id = event_log_records[0]['Id']
        log_file_url = f"{sf.base_url}/sobjects/EventLogFile/{log_id}/LogFile"
        log_file_response = requests.get(log_file_url,
                                         headers={"Authorization": f"Bearer {sf.session_id}"},
                                         timeout=REQUESTS_TIMEOUT_SECONDS)
        log_file_response.raise_for_status()

        log_content = log_file_response.text
        if not log_content:
            return None

        return csv.DictReader(StringIO(log_content))

    except requests.RequestException as req_err:
        logger.error("Request error occurred in parse_logs : %s", req_err)
    except csv.Error as csv_err:
        logger.error("CSV processing error: %s", csv_err)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("An unexpected error occurred in parse_logs : %s", e)
