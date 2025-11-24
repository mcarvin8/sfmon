"""
Salesforce Monitoring Service - Main Entry Point

This is the primary orchestration module for monitoring a Salesforce org.
It implements a comprehensive monitoring strategy with resource-optimized scheduling to track:
    - Salesforce org limits and API usage
    - Apex execution, errors, and flex queue
    - Bulk API operations (daily and hourly)
    - User login events and geolocation analysis
    - Deployment and validation status
    - Org-wide sharing settings changes
    - Compliance violations and suspicious audit trail activities
    - EPT/APT performance metrics
    - Report exports
    - Integration user password expiration
    - Technical debt monitoring (permission sets, profiles, Apex versions, security health, dormant users, queues, dashboards)

Resource Optimization Strategy:
    - Functions are staggered to prevent CPU/memory spikes
    - Critical 5-minute functions: limits, instance health, apex flex queue
    - Hourly functions distributed across :00, :10, :20, :40, :50 minutes
    - Daily functions scheduled 06:00-09:00 with 15-minute intervals
    - Performance monitoring: 06:00-07:30
    - Business functions: 07:30-08:45

The service uses APScheduler with cron-style scheduling and exposes metrics
via Prometheus on port 9001.

Environment Variables Required:
    - SALESFORCE_AUTH_URL: SFDX authentication URL for org
    
Environment Variables Optional:
    - INTEGRATION_USER_NAMES: Comma-separated list of integration user names to monitor
                              for password expiration (e.g., "User1,User2,User3")
    - QUERY_TIMEOUT_SECONDS: Timeout in seconds for Salesforce SOQL queries (default: 30)
    - SCHEDULE_<JOB_ID>: Custom cron schedule for any job. Set to "disabled" to skip a job.
                         Format: "minute=*/5", "hour=7,minute=30", "*/5 * * * *", or JSON.
                         Example: SCHEDULE_MONITOR_SALESFORCE_LIMITS="*/10"

Functions:
    - schedule_tasks: Configures all APScheduler jobs with optimized timing
    - main: Entry point that initializes connection and starts scheduler
"""
import os
import json
import re

from prometheus_client import start_http_server
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from apex_flex_queue import  monitor_apex_flex_queue
from apex_jobs import (async_apex_job_status, monitor_apex_execution_time,
                       expose_apex_exception_metrics,
                       concurrent_apex_errors,
                       expose_concurrent_long_running_apex_errors,
                       async_apex_execution_summary)
from bulk_api import daily_analyse_bulk_api, hourly_analyse_bulk_api
from logger import logger
from compliance import (hourly_observe_user_querying_large_records, expose_suspicious_records)
from connection_sf import get_salesforce_connection_url
from deployments import get_deployment_status
from ept_apt import get_salesforce_ept_and_apt
from overall_sf_org import (monitor_salesforce_limits,
                            get_salesforce_licenses,
                            get_salesforce_instance)
from user_login import monitor_login_events, geolocation, monitor_integration_user_passwords
from org_wide_sharing_setting import monitor_org_wide_sharing_settings
from report_export import hourly_report_export_records
from tech_debt import (unassigned_permission_sets, perm_sets_limited_users,
                       profile_assignment_under5, profile_no_active_users,
                       apex_classes_api_version, apex_triggers_api_version,
                       security_health_check, salesforce_health_risks,
                       workflow_rules_monitoring, dormant_salesforce_users,
                       dormant_portal_users, total_queues_per_object,
                       queues_with_no_members, queues_with_zero_open_cases,
                       public_groups_with_no_members, dashboards_with_inactive_users)


def parse_cron_schedule(schedule_str):
    """
    Parse a cron schedule string into CronTrigger parameters.
    
    Supports multiple formats:
    1. Standard cron: "*/5 * * * *" -> minute='*/5'
    2. Parameter format: "minute=*/5" or "hour=7,minute=30"
    3. JSON format: '{"minute": "*/5"}' or '{"hour": "7", "minute": "30"}'
    4. Simple minute: "*/5" -> minute='*/5'
    
    Args:
        schedule_str: Cron schedule string in one of the supported formats
        
    Returns:
        dict: Keyword arguments for CronTrigger
    """
    if not schedule_str or schedule_str.lower() in ('disabled', 'none', ''):
        return None
    
    schedule_str = schedule_str.strip()
    
    # Try JSON format first
    if schedule_str.startswith('{'):
        try:
            return json.loads(schedule_str)
        except json.JSONDecodeError:
            pass
    
    # Try standard cron format: "*/5 * * * *"
    cron_parts = schedule_str.split()
    if len(cron_parts) == 5:
        result = {}
        if cron_parts[0] != '*':
            result['minute'] = cron_parts[0]
        if cron_parts[1] != '*':
            result['hour'] = cron_parts[1]
        if cron_parts[2] != '*':
            result['day'] = cron_parts[2]
        if cron_parts[3] != '*':
            result['month'] = cron_parts[3]
        if cron_parts[4] != '*':
            result['day_of_week'] = cron_parts[4]
        return result if result else None
    
    # Try parameter format: "minute=*/5" or "hour=7,minute=30"
    if '=' in schedule_str:
        params = {}
        for part in schedule_str.split(','):
            if '=' in part:
                key, value = part.split('=', 1)
                params[key.strip()] = value.strip()
        if params:
            return params
    
    # Simple format: assume it's just minutes if it's a single value
    # e.g., "*/5" or "0" or "10,50"
    if re.match(r'^[\d\*\/,]+$', schedule_str):
        return {'minute': schedule_str}
    
    # If we can't parse it, return None to use default
    logger.warning("Could not parse schedule string: %s, using default", schedule_str)
    return None


def get_schedule_config(job_id, default_schedule):
    """
    Get schedule configuration for a job from environment variable or use default.
    
    Environment variable format: SCHEDULE_<JOB_ID>
    Example: SCHEDULE_MONITOR_SALESFORCE_LIMITS="*/5"
    
    Args:
        job_id: The job identifier
        default_schedule: Default schedule dict for CronTrigger, or None to skip by default
        
    Returns:
        dict or None: Schedule configuration for CronTrigger, None if disabled
    """
    env_var = f'SCHEDULE_{job_id.upper()}'
    env_value = os.getenv(env_var)
    
    if env_value:
        parsed = parse_cron_schedule(env_value)
        if parsed is None:
            # Disabled or invalid - return None to skip scheduling
            logger.info("Job %s is disabled or has invalid schedule, skipping", job_id)
            return None
        logger.info("Using custom schedule for %s: %s", job_id, env_value)
        return parsed
    
    # Use default (may be None)
    return default_schedule


def schedule_tasks(sf, scheduler):
    """
    Schedule all tasks using APScheduler with cron syntax for precise timing.
    
    OPTIMIZATION STRATEGY (Resource Load Distribution):
    - ALL non-critical functions are staggered to prevent CPU/memory spikes
    - Resource-intensive functions have 15+ minute intervals between executions
    - Functions are grouped by type and scheduled in logical time blocks:
      * 06:00-07:30: Performance & Apex monitoring (15-minute intervals)
      * 07:30-09:00: Daily business functions (15-minute intervals)
      * 09:15-13:00: Tech debt monitoring (15-minute intervals)
      * Hourly: :00 (bulk API), :10/:50 (licenses), :20 (user queries), :40 (reports)
    - Critical 5-minute functions (limits, instance, apex flex queue) remain unchanged
    - All daily functions run once per day during business hours for optimal resource usage
    """
    # Execute each task once at script startup
    # High-prority functions should be prioritized over minor functions (i.e. functions that run every 5 minutes take priority over daily functions)
    logger.info("Executing tasks at startup...")
    monitor_salesforce_limits(sf)
    monitor_apex_flex_queue(sf)
    get_salesforce_instance(sf)
    get_salesforce_licenses(sf)
    daily_analyse_bulk_api(sf)

    hourly_analyse_bulk_api(sf)
    get_salesforce_ept_and_apt(sf)
    monitor_login_events(sf)
    async_apex_job_status(sf)
    monitor_apex_execution_time(sf)
    async_apex_execution_summary(sf)
    concurrent_apex_errors(sf)
    expose_concurrent_long_running_apex_errors(sf)
    expose_apex_exception_metrics(sf)
    hourly_observe_user_querying_large_records(sf)
    monitor_org_wide_sharing_settings(sf)
    expose_suspicious_records(sf)
    get_deployment_status(sf)
    geolocation(sf, chunk_size=100)
    monitor_integration_user_passwords(sf)
    # Tech debt monitoring functions
    unassigned_permission_sets(sf)
    perm_sets_limited_users(sf)
    profile_assignment_under5(sf)
    profile_no_active_users(sf)
    apex_classes_api_version(sf)
    apex_triggers_api_version(sf)
    security_health_check(sf)
    salesforce_health_risks(sf)
    workflow_rules_monitoring(sf)
    dormant_salesforce_users(sf)
    dormant_portal_users(sf)
    total_queues_per_object(sf)
    queues_with_no_members(sf)
    queues_with_zero_open_cases(sf)
    public_groups_with_no_members(sf)
    dashboards_with_inactive_users(sf)
    logger.info("Initial execution completed, scheduling tasks with APScheduler...")

    # Every 5 minutes on the dot (0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55)
    schedule = get_schedule_config('monitor_salesforce_limits', {'minute': '*/5'})
    if schedule:
        scheduler.add_job(
            func=lambda: monitor_salesforce_limits(sf),
            trigger=CronTrigger(**schedule),
            id='monitor_salesforce_limits',
            name='Monitor Salesforce Limits'
        )
    
    schedule = get_schedule_config('get_salesforce_instance', {'minute': '*/5'})
    if schedule:
        scheduler.add_job(
            func=lambda: get_salesforce_instance(sf),
            trigger=CronTrigger(**schedule),
            id='get_salesforce_instance',
            name='Get Salesforce Instance'
        )
    
    schedule = get_schedule_config('monitor_apex_flex_queue', {'minute': '*/5'})
    if schedule:
        scheduler.add_job(
            func=lambda: monitor_apex_flex_queue(sf),
            trigger=CronTrigger(**schedule),
            id='monitor_apex_flex_queue',
            name='Monitor Apex Flex Queue'
        )

    # Daily Business Functions - Staggered across morning hours (07:30-08:45)
    # to prevent resource spikes from simultaneous execution

    # Morning Business Hours Block (07:30-08:15)
    schedule = get_schedule_config('daily_analyse_bulk_api', {'hour': '7', 'minute': '30'})
    if schedule:
        scheduler.add_job(
            func=lambda: daily_analyse_bulk_api(sf),
            trigger=CronTrigger(**schedule),
            id='daily_analyse_bulk_api',
            name='Daily Analyse Bulk API'
        )
    
    schedule = get_schedule_config('get_deployment_status', {'hour': '7', 'minute': '45'})
    if schedule:
        scheduler.add_job(
            func=lambda: get_deployment_status(sf),
            trigger=CronTrigger(**schedule),
            id='get_deployment_status',
            name='Get Deployment Status'
        )
    
    schedule = get_schedule_config('geolocation', {'hour': '8', 'minute': '0'})
    if schedule:
        scheduler.add_job(
            func=lambda: geolocation(sf, chunk_size=100),
            trigger=CronTrigger(**schedule),
            id='geolocation',
            name='Geolocation Analysis'
        )

    schedule = get_schedule_config('monitor_org_wide_sharing_settings', {'hour': '8', 'minute': '45'})
    if schedule:
        scheduler.add_job(
            func=lambda: monitor_org_wide_sharing_settings(sf),
            trigger=CronTrigger(**schedule),
            id='monitor_org_wide_sharing_settings',
            name='Monitor Org Wide Sharing Settings'
        )
    
    schedule = get_schedule_config('monitor_integration_user_passwords', {'hour': '9', 'minute': '0'})
    if schedule:
        scheduler.add_job(
            func=lambda: monitor_integration_user_passwords(sf),
            trigger=CronTrigger(**schedule),
            id='monitor_integration_user_passwords',
            name='Monitor Integration User Passwords'
        )

    # Tech Debt Monitoring Block - Daily functions (09:15-11:00)
    # Staggered to prevent resource conflicts with other daily functions
    schedule = get_schedule_config('unassigned_permission_sets', {'hour': '9', 'minute': '15'})
    if schedule:
        scheduler.add_job(
            func=lambda: unassigned_permission_sets(sf),
            trigger=CronTrigger(**schedule),
            id='unassigned_permission_sets',
            name='Unassigned Permission Sets'
        )
    
    schedule = get_schedule_config('perm_sets_limited_users', {'hour': '9', 'minute': '30'})
    if schedule:
        scheduler.add_job(
            func=lambda: perm_sets_limited_users(sf),
            trigger=CronTrigger(**schedule),
            id='perm_sets_limited_users',
            name='Permission Sets Limited Users'
        )
    
    schedule = get_schedule_config('profile_assignment_under5', {'hour': '9', 'minute': '45'})
    if schedule:
        scheduler.add_job(
            func=lambda: profile_assignment_under5(sf),
            trigger=CronTrigger(**schedule),
            id='profile_assignment_under5',
            name='Profile Assignment Under 5'
        )
    
    schedule = get_schedule_config('profile_no_active_users', {'hour': '10', 'minute': '0'})
    if schedule:
        scheduler.add_job(
            func=lambda: profile_no_active_users(sf),
            trigger=CronTrigger(**schedule),
            id='profile_no_active_users',
            name='Profile No Active Users'
        )
    
    schedule = get_schedule_config('apex_classes_api_version', {'hour': '10', 'minute': '15'})
    if schedule:
        scheduler.add_job(
            func=lambda: apex_classes_api_version(sf),
            trigger=CronTrigger(**schedule),
            id='apex_classes_api_version',
            name='Apex Classes API Version'
        )
    
    schedule = get_schedule_config('apex_triggers_api_version', {'hour': '10', 'minute': '30'})
    if schedule:
        scheduler.add_job(
            func=lambda: apex_triggers_api_version(sf),
            trigger=CronTrigger(**schedule),
            id='apex_triggers_api_version',
            name='Apex Triggers API Version'
        )
    
    schedule = get_schedule_config('security_health_check', {'hour': '10', 'minute': '45'})
    if schedule:
        scheduler.add_job(
            func=lambda: security_health_check(sf),
            trigger=CronTrigger(**schedule),
            id='security_health_check',
            name='Security Health Check'
        )
    
    schedule = get_schedule_config('salesforce_health_risks', {'hour': '11', 'minute': '0'})
    if schedule:
        scheduler.add_job(
            func=lambda: salesforce_health_risks(sf),
            trigger=CronTrigger(**schedule),
            id='salesforce_health_risks',
            name='Salesforce Health Risks'
        )
    
    schedule = get_schedule_config('workflow_rules_monitoring', {'hour': '11', 'minute': '15'})
    if schedule:
        scheduler.add_job(
            func=lambda: workflow_rules_monitoring(sf),
            trigger=CronTrigger(**schedule),
            id='workflow_rules_monitoring',
            name='Workflow Rules Monitoring'
        )
    
    schedule = get_schedule_config('dormant_salesforce_users', {'hour': '11', 'minute': '30'})
    if schedule:
        scheduler.add_job(
            func=lambda: dormant_salesforce_users(sf),
            trigger=CronTrigger(**schedule),
            id='dormant_salesforce_users',
            name='Dormant Salesforce Users'
        )
    
    schedule = get_schedule_config('dormant_portal_users', {'hour': '11', 'minute': '45'})
    if schedule:
        scheduler.add_job(
            func=lambda: dormant_portal_users(sf),
            trigger=CronTrigger(**schedule),
            id='dormant_portal_users',
            name='Dormant Portal Users'
        )
    
    schedule = get_schedule_config('total_queues_per_object', {'hour': '12', 'minute': '0'})
    if schedule:
        scheduler.add_job(
            func=lambda: total_queues_per_object(sf),
            trigger=CronTrigger(**schedule),
            id='total_queues_per_object',
            name='Total Queues Per Object'
        )
    
    schedule = get_schedule_config('queues_with_no_members', {'hour': '12', 'minute': '15'})
    if schedule:
        scheduler.add_job(
            func=lambda: queues_with_no_members(sf),
            trigger=CronTrigger(**schedule),
            id='queues_with_no_members',
            name='Queues With No Members'
        )
    
    schedule = get_schedule_config('queues_with_zero_open_cases', {'hour': '12', 'minute': '30'})
    if schedule:
        scheduler.add_job(
            func=lambda: queues_with_zero_open_cases(sf),
            trigger=CronTrigger(**schedule),
            id='queues_with_zero_open_cases',
            name='Queues With Zero Open Cases'
        )
    
    schedule = get_schedule_config('public_groups_with_no_members', {'hour': '12', 'minute': '45'})
    if schedule:
        scheduler.add_job(
            func=lambda: public_groups_with_no_members(sf),
            trigger=CronTrigger(**schedule),
            id='public_groups_with_no_members',
            name='Public Groups With No Members'
        )
    
    schedule = get_schedule_config('dashboards_with_inactive_users', {'hour': '13', 'minute': '0'})
    if schedule:
        scheduler.add_job(
            func=lambda: dashboards_with_inactive_users(sf),
            trigger=CronTrigger(**schedule),
            id='dashboards_with_inactive_users',
            name='Dashboards With Inactive Users'
        )

    # Performance & Apex Monitoring - Staggered across early morning (06:00-07:30)
    # Spread to avoid resource conflicts and provide comprehensive daily monitoring

    # Performance Metrics Block (06:00-06:30)
    schedule = get_schedule_config('get_salesforce_ept_and_apt', {'hour': '6', 'minute': '0'})
    if schedule:
        scheduler.add_job(
            func=lambda: get_salesforce_ept_and_apt(sf),
            trigger=CronTrigger(**schedule),
            id='get_salesforce_ept_and_apt',
            name='Get Salesforce EPT and APT'
        )
    
    schedule = get_schedule_config('monitor_login_events', {'hour': '6', 'minute': '15'})
    if schedule:
        scheduler.add_job(
            func=lambda: monitor_login_events(sf),
            trigger=CronTrigger(**schedule),
            id='monitor_login_events',
            name='Monitor Login Events'
        )
    
    schedule = get_schedule_config('async_apex_job_status', {'hour': '6', 'minute': '30'})
    if schedule:
        scheduler.add_job(
            func=lambda: async_apex_job_status(sf),
            trigger=CronTrigger(**schedule),
            id='async_apex_job_status',
            name='Async Apex Job Status'
        )

    # Apex Performance Analysis Block (06:45-07:15)
    schedule = get_schedule_config('monitor_apex_execution_time', {'hour': '6', 'minute': '45'})
    if schedule:
        scheduler.add_job(
            func=lambda: monitor_apex_execution_time(sf),
            trigger=CronTrigger(**schedule),
            id='monitor_apex_execution_time',
            name='Monitor Apex Execution Time'
        )
    
    schedule = get_schedule_config('async_apex_execution_summary', {'hour': '7', 'minute': '0'})
    if schedule:
        scheduler.add_job(
            func=lambda: async_apex_execution_summary(sf),
            trigger=CronTrigger(**schedule),
            id='async_apex_execution_summary',
            name='Async Apex Execution Summary'
        )

    # Apex Error Monitoring Block (07:15-07:30)
    schedule = get_schedule_config('concurrent_apex_errors', {'hour': '7', 'minute': '15'})
    if schedule:
        scheduler.add_job(
            func=lambda: concurrent_apex_errors(sf),
            trigger=CronTrigger(**schedule),
            id='concurrent_apex_errors',
            name='Concurrent Apex Errors'
        )
    
    schedule = get_schedule_config('expose_apex_exception_metrics', {'hour': '7', 'minute': '30'})
    if schedule:
        scheduler.add_job(
            func=lambda: expose_apex_exception_metrics(sf),
            trigger=CronTrigger(**schedule),
            id='expose_apex_exception_metrics',
            name='Expose Apex Exception Metrics'
        )

    # Hourly Monitoring Functions - Staggered to prevent simultaneous execution
    # Functions run at different minute intervals to distribute load

    # Bulk API Analysis - Every hour at :00
    schedule = get_schedule_config('hourly_analyse_bulk_api', {'minute': '0'})
    if schedule:
        scheduler.add_job(
            func=lambda: hourly_analyse_bulk_api(sf),
            trigger=CronTrigger(**schedule),
            id='hourly_analyse_bulk_api',
            name='Hourly Analyse Bulk API'
        )

    # Salesforce Licenses - Twice per hour at :10 and :50
    schedule = get_schedule_config('get_salesforce_licenses', {'minute': '10,50'})
    if schedule:
        scheduler.add_job(
            func=lambda: get_salesforce_licenses(sf),
            trigger=CronTrigger(**schedule),
            id='get_salesforce_licenses',
            name='Get Salesforce Licenses'
        )

    # User Query Monitoring - Every hour at :20 (20 minutes after bulk API)
    schedule = get_schedule_config('hourly_observe_user_querying_large_records', {'minute': '20'})
    if schedule:
        scheduler.add_job(
            func=lambda: hourly_observe_user_querying_large_records(sf),
            trigger=CronTrigger(**schedule),
            id='hourly_observe_user_querying_large_records',
            name='Hourly Observe User Querying Large Records'
        )

    # Report Export Monitoring - Every hour at :40 (40 minutes after bulk API)
    schedule = get_schedule_config('hourly_report_export_records', {'minute': '40'})
    if schedule:
        scheduler.add_job(
            func=lambda: hourly_report_export_records(sf),
            trigger=CronTrigger(**schedule),
            id='hourly_report_export_records',
            name='Hourly Report Export Records'
        )
    
    # Note: expose_suspicious_records is called at startup but not scheduled
    # Add it if you want it scheduled:
    schedule = get_schedule_config('expose_suspicious_records', None)
    if schedule:
        scheduler.add_job(
            func=lambda: expose_suspicious_records(sf),
            trigger=CronTrigger(**schedule),
            id='expose_suspicious_records',
            name='Expose Suspicious Records'
        )

    logger.info("All jobs scheduled successfully with APScheduler")


def main():
    """
    Main function. Runs tasks using APScheduler with cron syntax for precise timing.
    """
    # Start Prometheus metrics server
    metrics_port = int(os.getenv('METRICS_PORT', 9001))
    start_http_server(metrics_port)
    # Connect to Salesforce org
    sf = get_salesforce_connection_url(url=os.getenv('SALESFORCE_AUTH_URL'))
    # Initialize APScheduler
    scheduler = BlockingScheduler()
    # Schedule all tasks
    schedule_tasks(sf, scheduler)
    try:
        logger.info("Starting APScheduler...")
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down scheduler...")
        scheduler.shutdown()


if __name__ == '__main__':
    main()
