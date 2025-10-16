"""
User Login and Authentication Monitoring Module

This module monitors user login activity, authentication patterns, and integration user
password expiration in the production Salesforce org. It analyzes Login EventLogFile
records and LoginHistory to track authentication trends, geolocation patterns, and
credential management.

Key Monitoring Areas:
    1. Login Events: Success/failure rates from hourly logs
    2. Geolocation Analysis: User login locations and browser information
    3. Integration User Passwords: Tracks password expiration for critical service accounts

Monitored Integration Users (Production):
    - BizApps Monitoring
    - GitlabIntegration Prod

Functions:
    - monitor_login_events: Processes hourly login logs for success/failure metrics
    - reset_login_gauges: Clears gauges before new data collection
    - fetch_latest_login_log: Retrieves most recent hourly login EventLogFile
    - process_login_log: Parses CSV log and counts login status
    - geolocation: Analyzes LoginHistory for geographic login patterns
    - monitor_integration_user_passwords: Tracks password expiration (90-day policy)

Metrics Exposed:
    - login_success_gauge: Count of successful logins
    - login_failure_gauge: Count of failed login attempts
    - unique_login_attempts_gauge: Number of unique users attempting login
    - geolocation_gauge: Login locations with browser and status context
    - integration_user_password_expiration_gauge: Days until password expires

Use Cases:
    - Detecting unusual authentication patterns
    - Identifying geographic anomalies in login activity
    - Preventing service disruptions from expired integration user passwords
    - Monitoring failed authentication attempts for security
    - Tracking unique user activity trends
"""
import csv
from datetime import datetime, timedelta, timezone
from io import StringIO
import requests
import pandas as pd

from logger import logger
from constants import REQUESTS_TIMEOUT_SECONDS
from gauges import (login_failure_gauge, login_success_gauge,
                    geolocation_gauge, unique_login_attempts_guage,
                    integration_user_password_expiration_gauge)
from query import query_records_all

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


def monitor_integration_user_passwords(sf):
    """
    Monitor password expiration for core integration users.
    Queries specific integration users and calculates days until password expiration.
    Password policy: 90 days from LastPasswordChangeDate
    """
    logger.info("Monitoring integration user password expiration...")
    
    try:
        # Query core integration users
        query = """
            SELECT Id, Name, Username, LastPasswordChangeDate
            FROM User
            WHERE Name IN ('BizApps Monitoring', 'GitlabIntegration Prod')
        """
        users = query_records_all(sf, query)
        
        if not users:
            logger.warning("No integration users found")
            return
        integration_user_password_expiration_gauge.clear()
        # Process each user
        for user in users:
            user_id = user.get('Id', 'Unknown')
            name = user.get('Name', 'Unknown')
            username = user.get('Username', 'Unknown')
            last_password_change = user.get('LastPasswordChangeDate')
            
            if last_password_change:
                # Parse the datetime and calculate days until expiration
                try:
                    # Salesforce returns datetime in ISO format
                    password_change_date = datetime.fromisoformat(
                        last_password_change.replace('Z', '+00:00')
                    )
                    current_date = datetime.now(timezone.utc)
                    days_since_change = (current_date - password_change_date).days
                    days_until_expiration = 90 - days_since_change
                    
                    # Format date for label (YYYY-MM-DD)
                    last_change_formatted = password_change_date.strftime('%Y-%m-%d')
                    
                    logger.info(
                        "User: %s | Username: %s | Last Password Change: %s | Days Until Expiration: %d",
                        name, username, last_change_formatted, days_until_expiration
                    )
                    
                    # Set gauge metric
                    integration_user_password_expiration_gauge.labels(
                        user_id=user_id,
                        name=name,
                        username=username,
                        last_password_change_date=last_change_formatted,
                        days_until_expiration=str(days_until_expiration)
                    ).set(days_until_expiration)
                    
                except (ValueError, TypeError) as e:
                    logger.error(
                        "Error parsing date for user %s: %s",
                        name, e
                    )
            else:
                logger.warning("No LastPasswordChangeDate for user: %s", name)
    
    # pylint: disable=broad-except
    except Exception:
        logger.exception("Failed to monitor integration user passwords")
