"""
    EPT/APT function/
"""
from collections import defaultdict
import csv
import io

import requests

from cloudwatch_logging import logger
from constants import REQUESTS_TIMEOUT_SECONDS
from gauges import ept_metric, apt_metric


def get_salesforce_ept_and_apt(sf):
    """
    Get EPT and APT data from the org.
    """
    logger.info("Monitoring Salesforce EPT and APT data...")
    # Query the Event Log Files for EPT data
    query = """SELECT EventType, LogDate, Id FROM EventLogFile WHERE Interval='Hourly' and EventType = 'LightningPageView' ORDER BY LogDate DESC LIMIT 1"""
    result = sf.query(query)

    # Process the result to extract relevant EPT data
    for record in result['records']:
        log_data_url = sf.base_url + f"/sobjects/EventLogFile/{record['Id']}/LogFile"
        response = requests.get(log_data_url, headers={"Authorization": f"Bearer {sf.session_id}"},
                                timeout=REQUESTS_TIMEOUT_SECONDS)

        if response.status_code == 200:
            log_data = response.text
            csv_data = csv.DictReader(io.StringIO(log_data))

            page_time_data = defaultdict(lambda: {'total_time': 0, 'count': 0, 'sessions': {}})

            for row in csv_data:

                page_name = row['PAGE_APP_NAME'] if row['PAGE_APP_NAME'] else 'Unknown_Page'
                page_duration = float(row['DURATION'])/1000 if row['DURATION'] else 0
                page_time_data[page_name]['total_time'] += page_duration
                page_time_data[page_name]['count'] += 1

                average_page_time = {page: {'avg_time': data['total_time'] / data['count'],'count': data['count']}
                                     for page, data in page_time_data.items()}

                if row['EFFECTIVE_PAGE_TIME_DEVIATION']:
                    ept = float(row['EFFECTIVE_PAGE_TIME'])/1000 if row['EFFECTIVE_PAGE_TIME'] else 0

                    ept_metric.labels(EFFECTIVE_PAGE_TIME_DEVIATION_REASON=row['EFFECTIVE_PAGE_TIME_DEVIATION_REASON'],
                                      EFFECTIVE_PAGE_TIME_DEVIATION_ERROR_TYPE=row['EFFECTIVE_PAGE_TIME_DEVIATION_ERROR_TYPE'],
                                      PREVPAGE_ENTITY_TYPE=row['PREVPAGE_ENTITY_TYPE'],
                                      PREVPAGE_APP_NAME=row['PREVPAGE_APP_NAME'],
                                      PAGE_ENTITY_TYPE=row['PAGE_ENTITY_TYPE'],
                                      PAGE_APP_NAME=row['PAGE_APP_NAME'],
                                      BROWSER_NAME=row['BROWSER_NAME']).set(ept)

            for page_name, page_details in average_page_time.items():
                apt_metric.labels(Page_name=page_name).set(page_details['avg_time'])
