"""
User Management Monitoring Module

This module monitors user-related technical debt including:
- Dormant Salesforce licensed users (inactive 90+ days)
- Dormant Portal/Community users (inactive 90+ days)

Data Sources:
    - User object with Profile.UserLicense
"""
from logger import logger
from gauges import (
    dormant_salesforce_users_gauge,
    dormant_portal_users_gauge,
)
from query import query_records_all


def dormant_salesforce_users(sf):
    """
    Query dormant Salesforce users - active users whose accounts are at least 90 days old 
    and who either haven't logged in during the last 90 days or have never logged in.
    """
    try:
        logger.info("Querying dormant Salesforce users...")
        query = """
        SELECT Id, Name, CreatedDate, Username, Email, IsActive, LastLoginDate, Profile.Name
        FROM User
        WHERE IsActive = true
        AND Profile.UserLicense.Name = 'Salesforce'
        AND (LastLoginDate < LAST_N_DAYS:90 OR LastLoginDate = Null)
        AND CreatedDate < LAST_N_DAYS:90
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
    Query dormant Portal users - active users whose accounts are at least 90 days old 
    and who either haven't logged in during the last 90 days or have never logged in.
    """
    try:
        logger.info("Querying dormant Portal users...")
        query = """
        SELECT Id, Name, CreatedDate, Username, Email, IsActive, LastLoginDate, Profile.Name
        FROM User
        WHERE IsActive = true
        AND Profile.UserLicense.Name != 'Salesforce'
        AND (LastLoginDate < LAST_N_DAYS:90 OR LastLoginDate = Null)
        AND CreatedDate < LAST_N_DAYS:90
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

