"""
User Management Monitoring Module

This module monitors user-related technical debt including:
- Dormant Salesforce licensed users (inactive N+ days)
- Dormant Portal/Community users (inactive N+ days)

Environment Variables:
    - DORMANT_USER_DAYS: Number of days of inactivity to consider a user dormant (default: 90)

Data Sources:
    - User object with Profile.UserLicense
"""
import os

from logger import logger
from gauges import (
    dormant_salesforce_users_gauge,
    dormant_portal_users_gauge,
)
from query import query_records_all

# Number of days of inactivity to consider a user dormant
DORMANT_USER_DAYS = int(os.getenv('DORMANT_USER_DAYS', 90))


def dormant_salesforce_users(sf):
    """
    Query dormant Salesforce users - active users whose accounts are at least N days old 
    and who either haven't logged in during the last N days or have never logged in.
    The threshold is configurable via DORMANT_USER_DAYS environment variable.
    """
    try:
        logger.info("Querying dormant Salesforce users (inactive %d+ days)...", DORMANT_USER_DAYS)
        query = f"""
        SELECT Id, Name, CreatedDate, Username, Email, IsActive, LastLoginDate, Profile.Name
        FROM User
        WHERE IsActive = true
        AND Profile.UserLicense.Name = 'Salesforce'
        AND (LastLoginDate < LAST_N_DAYS:{DORMANT_USER_DAYS} OR LastLoginDate = Null)
        AND CreatedDate < LAST_N_DAYS:{DORMANT_USER_DAYS}
        ORDER BY LastLoginDate ASC
        """
        results = query_records_all(sf, query)
        
        # Clear existing Prometheus gauge labels
        dormant_salesforce_users_gauge.clear()

        for record in results:
            # Handle null LastLoginDate
            last_login = record.get('LastLoginDate', 'Never')
            if last_login is None:
                last_login = 'Never'
            
            dormant_salesforce_users_gauge.labels(
                user_id=record['Id'],
                username=record['Username'],
                email=record['Email'],
                profile_name=record['Profile']['Name'],
                created_date=record['CreatedDate'],
                last_login_date=last_login
            ).set(1)
            
        logger.info("Found %d dormant Salesforce users", len(results))
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching dormant Salesforce users: %s", e)


def dormant_portal_users(sf):
    """
    Query dormant Portal users - active users whose accounts are at least N days old 
    and who either haven't logged in during the last N days or have never logged in.
    The threshold is configurable via DORMANT_USER_DAYS environment variable.
    """
    try:
        logger.info("Querying dormant Portal users (inactive %d+ days)...", DORMANT_USER_DAYS)
        query = f"""
        SELECT Id, Name, CreatedDate, Username, Email, IsActive, LastLoginDate, Profile.Name
        FROM User
        WHERE IsActive = true
        AND Profile.UserLicense.Name != 'Salesforce'
        AND (LastLoginDate < LAST_N_DAYS:{DORMANT_USER_DAYS} OR LastLoginDate = Null)
        AND CreatedDate < LAST_N_DAYS:{DORMANT_USER_DAYS}
        ORDER BY LastLoginDate ASC
        """
        results = query_records_all(sf, query)
        
        # Clear existing Prometheus gauge labels
        dormant_portal_users_gauge.clear()

        for record in results:
            # Handle null LastLoginDate
            last_login = record.get('LastLoginDate', 'Never')
            if last_login is None:
                last_login = 'Never'
            
            dormant_portal_users_gauge.labels(
                user_id=record['Id'],
                username=record['Username'],
                email=record['Email'],
                profile_name=record['Profile']['Name'],
                created_date=record['CreatedDate'],
                last_login_date=last_login
            ).set(1)
            
        logger.info("Found %d dormant Portal users", len(results))
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching dormant Portal users: %s", e)

