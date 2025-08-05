"""
EPT/APT function.
"""
from collections import defaultdict
import csv
import io

import requests

from cloudwatch_logging import logger
from constants import REQUESTS_TIMEOUT_SECONDS
from gauges import ept_metric, apt_metric
from query import query_records_all


def get_salesforce_ept_and_apt(sf):
    """
    Retrieve and report Salesforce Effective Page Time (EPT) and Average Page Time (APT) metrics.

    This function fetches the latest LightningPageView event log file,
    calculates average page times, extracts EPT metrics, and sends them to CloudWatch gauges.
    """
    logger.info("Monitoring Salesforce EPT and APT data...")
    try:
        record = fetch_latest_lightning_pageview_log(sf)
        if not record:
            logger.warning("No LightningPageView event log found.")
            return

        log_data = download_log_file(sf, record['Id'])
        if not log_data:
            logger.warning("No log data found.")
            return

        page_time_data, ept_rows = parse_log_data(log_data)

        report_apt_metrics(page_time_data)
        report_ept_metrics(ept_rows)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Failed to retrieve Salesforce EPT and APT data: %s", e)


def fetch_latest_lightning_pageview_log(sf):
    """
    Fetch the most recent LightningPageView event log record.

    Args:
        sf: Salesforce client/session object.

    Returns:
        dict: A single EventLogFile record, or None if not found.
    """
    query = """
        SELECT EventType, LogDate, Id 
        FROM EventLogFile 
        WHERE Interval='Hourly' 
          AND EventType = 'LightningPageView' 
        ORDER BY LogDate DESC 
        LIMIT 1
    """
    result = query_records_all(sf, query)
    return result[0] if result else None


def download_log_file(sf, log_id):
    """
    Download the content of a specific EventLogFile.

    Args:
        sf: Salesforce client/session object.
        log_id (str): ID of the EventLogFile to download.

    Returns:
        str: The raw CSV log data as a string, or None if the request failed.
    """
    url = sf.base_url + f"/sobjects/EventLogFile/{log_id}/LogFile"
    response = requests.get(url,
                            headers={"Authorization": f"Bearer {sf.session_id}"},
                            timeout=REQUESTS_TIMEOUT_SECONDS)
    if response.status_code == 200:
        return response.text
    return None


def parse_log_data(log_data):
    """
    Parse the log CSV data into page time summaries and EPT rows.

    Args:
        log_data (str): Raw CSV text of the log file.

    Returns:
        tuple: (page_time_data, ept_rows)
            page_time_data (defaultdict): Mapping of page names to total time and count.
            ept_rows (list): List of rows with EPT deviation information.
    """
    page_time_data = defaultdict(lambda: {'total_time': 0, 'count': 0})
    ept_rows = []
    csv_data = csv.DictReader(io.StringIO(log_data))

    for row in csv_data:
        update_page_time_data(page_time_data, row)
        if row.get('EFFECTIVE_PAGE_TIME_DEVIATION'):
            ept_rows.append(row)

    return page_time_data, ept_rows


def update_page_time_data(page_time_data, row):
    """
    Update page time statistics with a row from the log data.

    Args:
        page_time_data (defaultdict): Mapping of page names to accumulated time and count.
        row (dict): A single row from the parsed CSV log data.
    """
    page_name = row['PAGE_APP_NAME'] or 'Unknown_Page'
    duration = float(row['DURATION']) / 1000 if row.get('DURATION') else 0
    page_time_data[page_name]['total_time'] += duration
    page_time_data[page_name]['count'] += 1


def report_apt_metrics(page_time_data):
    """
    Report Average Page Time (APT) metrics to CloudWatch.

    Args:
        page_time_data (defaultdict): Mapping of page names to total time and count.
    """
    for page, data in page_time_data.items():
        if data['count'] > 0:
            avg_time = data['total_time'] / data['count']
            apt_metric.labels(Page_name=page).set(avg_time)


def report_ept_metrics(ept_rows):
    """
    Report Effective Page Time (EPT) metrics to CloudWatch.

    Args:
        ept_rows (list): List of rows containing EPT deviation data.
    """
    for row in ept_rows:
        ept_value = float(row['EFFECTIVE_PAGE_TIME']) / 1000 if row.get('EFFECTIVE_PAGE_TIME') else 0
        ept_metric.labels(
            EFFECTIVE_PAGE_TIME_DEVIATION_REASON=row.get('EFFECTIVE_PAGE_TIME_DEVIATION_REASON', ''),
            EFFECTIVE_PAGE_TIME_DEVIATION_ERROR_TYPE=row.get('EFFECTIVE_PAGE_TIME_DEVIATION_ERROR_TYPE', ''),
            PREVPAGE_ENTITY_TYPE=row.get('PREVPAGE_ENTITY_TYPE', ''),
            PREVPAGE_APP_NAME=row.get('PREVPAGE_APP_NAME', ''),
            PAGE_ENTITY_TYPE=row.get('PAGE_ENTITY_TYPE', ''),
            PAGE_APP_NAME=row.get('PAGE_APP_NAME', ''),
            BROWSER_NAME=row.get('BROWSER_NAME', '')
        ).set(ept_value)
