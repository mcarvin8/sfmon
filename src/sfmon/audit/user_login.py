"""
User Login and Authentication Monitoring Module

This module monitors user login activity, authentication patterns in the production Salesforce org. 
It analyzes Login EventLogFile records and LoginHistory to track authentication trends, geolocation patterns, and
credential management.

Key Monitoring Areas:
    1. Login Events: Success/failure rates from hourly logs
    2. Geolocation Analysis: User login locations and browser information

Environment Variables:
    - GEOLOCATION_CHUNK_SIZE: Batch size for user lookups in geolocation queries (default: 100)
    - GEOLOCATION_LOOKBACK_HOURS: Number of hours to look back for geolocation data (default: 1)

Functions:
    - monitor_login_events: Processes hourly login logs for success/failure metrics
    - reset_login_gauges: Clears gauges before new data collection
    - fetch_latest_login_log: Retrieves most recent hourly login EventLogFile
    - process_login_log: Parses CSV log and counts login status
    - geolocation: Analyzes LoginHistory for geographic login patterns

Metrics Exposed:
    - login_success_gauge: Count of successful logins
    - login_failure_gauge: Count of failed login attempts
    - unique_login_attempts_gauge: Number of unique users attempting login
    - geolocation_gauge: Login locations with browser and status context

Use Cases:
    - Detecting unusual authentication patterns
    - Identifying geographic anomalies in login activity
    - Monitoring failed authentication attempts for security
    - Tracking unique user activity trends
"""
import csv
from datetime import datetime, timedelta, timezone
from io import StringIO
import os
import requests
import pandas as pd

from logger import logger
from constants import REQUESTS_TIMEOUT_SECONDS
from gauges import (login_failure_gauge, login_success_gauge,
                    geolocation_gauge, unique_login_attempts_gauge)
from query import query_records_all

# Geolocation configuration
GEOLOCATION_CHUNK_SIZE = int(os.getenv('GEOLOCATION_CHUNK_SIZE', 100))
GEOLOCATION_LOOKBACK_HOURS = int(os.getenv('GEOLOCATION_LOOKBACK_HOURS', 1))


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
    unique_login_attempts_gauge.set(0)


def fetch_latest_login_log(sf):
    '''
        Query log file for events.
    '''
    query = "SELECT Id, LogDate, Interval FROM EventLogFile WHERE EventType = 'Login' and Interval = 'Hourly' ORDER BY LogDate DESC"
    event_log_file = query_records_all(sf, query)
    if not event_log_file:
        return None

    log_id = event_log_file[0]['Id']

    log_data_url = sf.base_url + f"/sobjects/EventLogFile/{log_id}/LogFile"
    response = requests.get(log_data_url,
                            headers={"Authorization": f"Bearer {sf.session_id}"},
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
        unique_login_attempts_gauge.set(df['USER_ID'].nunique())
    else:
        logger.warning("USER_ID field is not present in the log data")


def geolocation(sf, chunk_size=None):
    """
    Get geolocation data from login events.
    The chunk size and lookback period are configurable via environment variables.
    
    Args:
        sf: Salesforce connection object.
        chunk_size: Optional batch size for user lookups (defaults to GEOLOCATION_CHUNK_SIZE env var).
    """
    # Use provided chunk_size or fall back to environment variable
    if chunk_size is None:
        chunk_size = GEOLOCATION_CHUNK_SIZE
    
    logger.info("Getting geolocation data (lookback: %d hours, chunk size: %d)...", 
                GEOLOCATION_LOOKBACK_HOURS, chunk_size)
    try:
        end_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        start_time = (datetime.now(timezone.utc) - timedelta(hours=GEOLOCATION_LOOKBACK_HOURS)).strftime('%Y-%m-%dT%H:%M:%SZ')

        query = f"SELECT UserId, LoginGeo.Latitude, LoginGeo.Longitude, Status, Browser FROM LoginHistory WHERE LoginTime >= {start_time} AND LoginTime <= {end_time}"
        user_location = query_records_all(sf, query)
        locations = user_location

        user_ids = [record['UserId'] for record in locations]

        # Query User object to get names for the UserIds in chunks
        user_map = {}
        for i in range(0, len(user_ids), chunk_size):
            chunk = user_ids[i:i + chunk_size]
            user_query = f"SELECT Id, Name FROM User WHERE Id IN ({', '.join([f"'{uid}'" for uid in chunk])})"
            user_results = query_records_all(sf, user_query)
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
