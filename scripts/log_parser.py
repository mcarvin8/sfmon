"""
    Helper function to parse salesforce logs.
"""
import csv
from io import StringIO
import requests

from constants import REQUESTS_TIMEOUT_SECONDS
from cloudwatch_logging import logger
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
