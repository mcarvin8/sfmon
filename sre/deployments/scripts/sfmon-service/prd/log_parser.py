"""
    Helper function to parse salesforce logs.
"""
import csv
import json
from io import StringIO
import subprocess
import requests

from constants import REQUESTS_TIMEOUT_SECONDS
from cloudwatch_logging import logger
from query import run_sf_cli_query


def get_salesforce_base_url(alias: str) -> str:
    """
    Construct base URL and return access token for advanced queries.
    """
    try:
        # Run the sf org display command with JSON output
        login_cmd = f'sf org display --target-org {alias} --json'
        result = subprocess.run(
            login_cmd,
            capture_output=True,
            check=True,
            text=True,
            shell=True
        )
        
        # Parse JSON output
        data = json.loads(result.stdout)
        instance_url = data["result"]["instanceUrl"]
        api_version = data["result"]["apiVersion"]
        access_token = data["result"]["accessToken"]

        # Construct the full base URL for REST API
        base_url = f"{instance_url}/services/data/v{api_version}/"
        return base_url, access_token

    except subprocess.CalledProcessError as e:
        logger.error("Error retrieving Salesforce base URL: %s", e)
        raise
    except KeyError as e:
        logger.error("Missing expected key in Salesforce CLI output for base URL: %s", e)
        raise

def parse_logs(sf, log_query):
    """
    Fetch and parse logs from given query
    """
    try:
        event_log_records = run_sf_cli_query(query=log_query, alias=sf)
        if not event_log_records:
            return None

        log_id = event_log_records[0]['Id']
        (base_url, access_token) = get_salesforce_base_url(sf)
        log_file_url = f"{base_url}/sobjects/EventLogFile/{log_id}/LogFile"
        log_file_response = requests.get(log_file_url,
                                         headers={"Authorization": f"Bearer {access_token}"},
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
