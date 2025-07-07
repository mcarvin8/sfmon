"""
    User login functions.
"""
import csv
from datetime import datetime, timedelta, timezone
from io import StringIO
import requests
import pandas as pd

from cloudwatch_logging import logger
from constants import REQUESTS_TIMEOUT_SECONDS
from gauges import (login_failure_gauge, login_success_gauge,
                    geolocation_gauge, unique_login_attempts_guage)
from query import run_sf_cli_query
from log_parser import get_salesforce_base_url

def monitor_login_events(sf):
    """
    Get login events from the org.
    """
    reset_login_gauges()
    logger.info("Monitoring login events...")

    try:
        log_data = fetch_latest_login_log(sf)
        if log_data:
            process_login_log(log_data)
    # pylint: disable=broad-except
    except Exception:
        logger.exception("Failed to monitor login events")


def reset_login_gauges():
    '''
        Reset gauges before querying.
    '''
    login_success_gauge.set(0)
    login_failure_gauge.set(0)
    unique_login_attempts_guage.set(0)


def fetch_latest_login_log(sf):
    '''
        Query log file for events.
    '''
    query = "SELECT Id, LogDate, Interval FROM EventLogFile WHERE EventType = 'Login' and Interval = 'Hourly' ORDER BY LogDate DESC"
    event_log_file = run_sf_cli_query(query=query, alias=sf)
    if not event_log_file:
        return None

    log_id = event_log_file[0]['Id']
    (base_url, access_token) = get_salesforce_base_url(sf)
    log_data_url = base_url + f"/sobjects/EventLogFile/{log_id}/LogFile"
    response = requests.get(log_data_url,
                            headers={"Authorization": f"Bearer {access_token}"},
                            timeout=REQUESTS_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.text if response.text else None


def process_login_log(log_text):
    '''
        Process login log for successes and failures.
    '''
    success_count = 0
    failure_count = 0
    csv_reader = csv.DictReader(StringIO(log_text))

    for row in csv_reader:
        status = row.get('LOGIN_STATUS')
        if status == 'LOGIN_NO_ERROR':
            success_count += 1
        else:
            failure_count += 1

    login_success_gauge.set(success_count)
    login_failure_gauge.set(failure_count)

    df = pd.read_csv(StringIO(log_text))
    if 'USER_ID' in df.columns:
        unique_login_attempts_guage.set(df['USER_ID'].nunique())
    else:
        logger.warning("USER_ID field is not present in the log data")


def geolocation(sf, chunk_size=100):
    """
    Get geolocation data from login events.
    """
    logger.info("Getting geolocation data...")
    try:
        end_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        start_time = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')

        query = f"SELECT UserId, LoginGeo.Latitude, LoginGeo.Longitude, Status, Browser FROM LoginHistory WHERE LoginTime >= {start_time} AND LoginTime <= {end_time}"
        user_location = run_sf_cli_query(query=query, alias=sf)
        locations = user_location

        user_ids = [record['UserId'] for record in locations]

        # Query User object to get names for the UserIds in chunks
        user_map = {}
        for i in range(0, len(user_ids), chunk_size):
            chunk = user_ids[i:i + chunk_size]
            user_query = f"SELECT Id, Name FROM User WHERE Id IN ({', '.join([f"'{uid}'" for uid in chunk])})"
            user_results = run_sf_cli_query(query=user_query, alias=sf)
            user_map.update({user['Id']: user['Name'] for user in user_results})

        for record in locations:
            record['UserName'] = user_map.get(record['UserId'], 'Unknown User')
            if 'LoginGeo' in record and record['LoginGeo']:
                latitude = record['LoginGeo']['Latitude']
                longitude = record['LoginGeo']['Longitude']
                username = record['UserName']
                browser = record['Browser']
                login_status = record['Status']
                geolocation_gauge.labels(user=username, longitude=longitude,
                                         latitude=latitude, browser=browser,
                                         status=login_status).set(1)

    except KeyError as e:
        logger.error("Key error: %s", e)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Unexpected error: %s", e)
