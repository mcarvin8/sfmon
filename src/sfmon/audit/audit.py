"""
Audit and Compliance Monitoring Orchestration Module

This module orchestrates all audit and compliance monitoring functions for the
production Salesforce org. It provides two main entry points:

Hourly Checks (run_hourly_audit):
    - Large query monitoring (>10,000 records)
    - Forbidden profile assignment detection

Daily Checks (run_daily_audit):
    - Suspicious audit trail activities
    - Org-wide sharing settings changes
    - Deployment and validation status
    - User login events and geolocation

Functions:
    - run_hourly_audit: Executes all hourly compliance checks
    - run_daily_audit: Executes all daily compliance checks
"""
from .large_queries import hourly_observe_user_querying_large_records
from .audit_trail import expose_suspicious_records
from .sharing_settings import monitor_org_wide_sharing_settings
from .forbidden_profiles import monitor_forbidden_profile_assignments
from .deployments import get_deployment_status
from .user_login import monitor_login_events, geolocation
from logger import logger


def run_hourly_audit(sf):
    """
    Hourly audit function for time-sensitive compliance checks.
    This function should be scheduled to run every hour.
    
    Args:
        sf: Salesforce connection object.
    """
    logger.info("Starting hourly audit compliance checks...")
    
    hourly_observe_user_querying_large_records(sf)
    monitor_forbidden_profile_assignments(sf)
    
    logger.info("Hourly audit compliance checks completed.")


def run_daily_audit(sf):
    """
    Daily audit function for compliance checks.
    This function is called daily at 8:00 AM PST (16:00 UTC) to run before BAR standup.
    
    Args:
        sf: Salesforce connection object.
    """
    logger.info("Starting daily audit compliance checks...")
    
    expose_suspicious_records(sf)
    monitor_org_wide_sharing_settings(sf)
    get_deployment_status(sf)
    monitor_login_events(sf)
    geolocation(sf, chunk_size=100)
    
    logger.info("Daily audit compliance checks completed.")
