"""
Forbidden Profile Assignment Monitoring Module

This module monitors for active users who have been assigned profiles
that should not be used in production (e.g., Admin-SoD-PreProd-Delivery).
It exposes violations as Prometheus metrics for alerting.

Environment Variables:
    - FORBIDDEN_PROD_PROFILES: Comma-separated list of profile names that
                               should not be assigned to active users in production

Functions:
    - monitor_forbidden_profile_assignments: Main monitoring function
"""
import os
from logger import logger
from gauges import forbidden_profile_users_gauge
from query import query_records_all


def _get_forbidden_profiles():
    """
    Load forbidden profile names from environment variable.
    
    Returns:
        list: List of forbidden profile names (empty list if not configured).
    """
    env_value = os.getenv('FORBIDDEN_PROD_PROFILES', '')
    if not env_value:
        return []
    return [name.strip() for name in env_value.split(',') if name.strip()]


FORBIDDEN_PROD_PROFILES = _get_forbidden_profiles()


def monitor_forbidden_profile_assignments(sf):
    """
    Monitor for active users assigned forbidden profiles in production.
    
    This function checks for active users who have been assigned profiles
    that should not be used in production (e.g., Admin-SoD-PreProd-Delivery).
    
    Args:
        sf: Salesforce connection object.
    """
    logger.info("Checking for active users with forbidden profile assignments...")
    
    try:
        forbidden_profile_users_gauge.clear()
        
        # Skip if no forbidden profiles configured
        if not FORBIDDEN_PROD_PROFILES:
            logger.info("No forbidden profiles configured (FORBIDDEN_PROD_PROFILES env var). Skipping check.")
            forbidden_profile_users_gauge.labels(
                user_id='none',
                user_name='Not Configured',
                username='none',
                profile_name='none'
            ).set(0)
            return
        
        # Build query to find active users with forbidden profiles
        profile_list = "', '".join(FORBIDDEN_PROD_PROFILES)
        query = f"""
            SELECT Id, Name, Username, Profile.Name 
            FROM User 
            WHERE IsActive = true 
            AND Profile.Name IN ('{profile_list}')
        """
        
        result = query_records_all(sf, query)
        
        has_violations = False
        if result:
            for user in result:
                user_id = user.get('Id', 'Unknown')
                user_name = user.get('Name', 'Unknown')
                username = user.get('Username', 'Unknown')
                profile_name = (user.get('Profile', {}).get('Name', 'Unknown')
                               if isinstance(user.get('Profile'), dict) else 'Unknown')
                
                logger.warning(
                    "COMPLIANCE VIOLATION: Active user '%s' (%s) assigned forbidden profile '%s'",
                    user_name, username, profile_name
                )
                
                forbidden_profile_users_gauge.labels(
                    user_id=user_id,
                    user_name=user_name,
                    username=username,
                    profile_name=profile_name
                ).set(1)
                has_violations = True
        
        if not has_violations:
            logger.info("No active users found with forbidden profile assignments.")
            forbidden_profile_users_gauge.labels(
                user_id='none',
                user_name='No Violations',
                username='none',
                profile_name='none'
            ).set(0)
    
    except Exception as e:  # pylint: disable=broad-except
        logger.error("Error checking forbidden profile assignments: %s", e)
