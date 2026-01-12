"""
Shared Utility Functions for Audit Module

This module provides common utility functions used across the audit monitoring
service, including user lookups and group categorization.

Environment Variables:
    - INTEGRATION_USER_NAMES: Comma-separated list of integration user names
                              to exclude from compliance monitoring

Functions:
    - get_user_name: Resolves Salesforce user ID to display name
    - categorize_user_group: Categorizes users as 'Integration User' or 'Other'
"""
import os
from logger import logger
from query import query_records_all


def _get_integration_users():
    """
    Load integration user names from environment variable.
    
    Returns:
        set: Set of integration user names (empty set if not configured).
    """
    env_value = os.getenv('INTEGRATION_USER_NAMES', '')
    if not env_value:
        return set()
    return set(name.strip() for name in env_value.split(',') if name.strip())


# Load integration users once at module import
INTEGRATION_USERS = _get_integration_users()


def get_user_name(sf, user_id):
    """
    Helper function to fetch user name by user ID.
    
    Args:
        sf: Salesforce connection object.
        user_id: Salesforce User ID.
    
    Returns:
        str: User's display name or 'Unknown User' if not found.
    """
    try:
        query = f"SELECT Name FROM User WHERE Id = '{user_id}'"
        result = query_records_all(sf, query)
        return result[0]['Name'] if result else 'Unknown User'
    except Exception as e:  # pylint: disable=broad-except
        logger.error("Error fetching user name for ID %s: %s", user_id, e)
        return 'Unknown User'


def categorize_user_group(user_name):
    """
    Categorize a user into a user group for filtering purposes.
    
    Args:
        user_name: Name of the user from audit trail.
    
    Returns:
        str: 'Integration User' if in INTEGRATION_USER_NAMES, otherwise 'Other'.
    """
    if user_name in INTEGRATION_USERS:
        return 'Integration User'
    return 'Other'
