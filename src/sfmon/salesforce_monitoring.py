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
    - Technical debt monitoring:
        * Permission sets (unassigned, limited users)
        * Profiles (under 5 users, no active users)
        * Apex API versions (classes, triggers)
        * Security health check and risks
        * Workflow rules
        * Dormant users (Salesforce and Portal)
        * Queues (per object, no members, zero open cases)
        * Public groups (no members)
        * Dashboards (inactive running users)
        * Scheduled Apex jobs

Resource Optimization Strategy:
    - Functions are staggered to prevent CPU/memory spikes
    - Critical 5-minute functions: limits, instance health, apex flex queue
    - Hourly functions distributed across :00, :10/:50, :20, :40 minutes
    - Daily functions scheduled with 15-minute intervals:
        * 06:00-07:30: Performance & Apex monitoring
        * 07:30-09:00: Daily business functions
        * 09:15-13:15: Tech debt monitoring (17 functions)

The service uses APScheduler with cron-style scheduling and exposes metrics
via Prometheus on port 9001.

Environment Variables Required:
    - SALESFORCE_AUTH_URL: SFDX authentication URL for org
    
Environment Variables Optional:
    - CONFIG_FILE_PATH: Path to JSON configuration file (default: /app/sfmon/config.json)
    - QUERY_TIMEOUT_SECONDS: Timeout in seconds for Salesforce SOQL queries (default: 30)
    - METRICS_PORT: Prometheus metrics server port (default: 9001)
    
Configuration File:
    A JSON configuration file is used to configure schedules, disable functions,
    and set integration user names. See README for configuration file format and examples.

Functions:
    - schedule_tasks: Configures all APScheduler jobs with optimized timing
    - main: Entry point that initializes connection and starts scheduler
"""
import os

from prometheus_client import start_http_server
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# Shared modules from root
from logger import logger
from connection_sf import get_salesforce_connection_url

# Operations monitoring functions (ops package)
from ops import (
    monitor_apex_flex_queue,
    async_apex_job_status, monitor_apex_execution_time,
    expose_apex_exception_metrics, concurrent_apex_errors,
    expose_concurrent_long_running_apex_errors, async_apex_execution_summary,
    daily_analyse_bulk_api, hourly_analyse_bulk_api,
    monitor_salesforce_limits, get_salesforce_licenses, get_salesforce_instance,
    get_salesforce_ept_and_apt
)

# Audit and compliance functions (audit package)
from audit import (
    hourly_observe_user_querying_large_records,
    expose_suspicious_records,
    monitor_org_wide_sharing_settings,
    monitor_forbidden_profile_assignments,
    get_deployment_status,
    monitor_login_events, geolocation,
    hourly_report_export_records
)

# Tech debt monitoring functions (tech_debt package)
from tech_debt import (
    apex_classes_api_version, apex_triggers_api_version, workflow_rules_monitoring,
    unassigned_permission_sets, perm_sets_limited_users,
    profile_assignment_under5, profile_no_active_users,
    security_health_check, salesforce_health_risks,
    dormant_salesforce_users, dormant_portal_users,
    total_queues_per_object, queues_with_no_members,
    queues_with_zero_open_cases, public_groups_with_no_members,
    dashboards_with_inactive_users, scheduled_apex_jobs_monitoring
)


def get_schedule_config(job_id, default_schedule):
    """
    Get schedule configuration for a job from config file, environment variable, or use default.
    
    Priority:
    1. Environment variable SCHEDULE_<JOB_ID> (highest priority)
    2. Config file schedules.<job_id>
    3. Default schedule (lowest priority)
    
    Args:
        job_id: The job identifier
        default_schedule: Default schedule dict for CronTrigger, or None to skip by default
        
    Returns:
        dict or None: Schedule configuration for CronTrigger, None if disabled
    """
    from config import get_schedule_from_config
    return get_schedule_from_config(job_id, default_schedule)


def schedule_tasks(sf, scheduler):
    """
    Schedule all tasks using APScheduler with cron syntax for precise timing.
    
    OPTIMIZATION STRATEGY (Resource Load Distribution):
    - ALL non-critical functions are staggered to prevent CPU/memory spikes
    - Resource-intensive functions have 15-minute intervals between executions
    - All daily functions run once per day during business hours for optimal resource usage
    
    SCHEDULE OVERVIEW:
    
    Critical Functions (Every 5 minutes):
        - monitor_salesforce_limits
        - get_salesforce_instance
        - monitor_apex_flex_queue
    
    Hourly Functions (staggered throughout the hour):
        - :00 - hourly_analyse_bulk_api
        - :10, :50 - get_salesforce_licenses
        - :20 - hourly_observe_user_querying_large_records
        - :40 - hourly_report_export_records
    
    Daily Performance & Apex Monitoring (06:00-07:30):
        - 06:00 - get_salesforce_ept_and_apt
        - 06:15 - monitor_login_events
        - 06:30 - async_apex_job_status
        - 06:45 - monitor_apex_execution_time
        - 07:00 - async_apex_execution_summary
        - 07:15 - concurrent_apex_errors
        - 07:30 - expose_apex_exception_metrics
    
    Daily Business Functions (07:30-09:00):
        - 07:30 - daily_analyse_bulk_api
        - 07:45 - get_deployment_status
        - 08:00 - geolocation
        - 08:45 - monitor_org_wide_sharing_settings
    
    Daily Tech Debt Monitoring (09:15-13:15):
        - 09:15 - unassigned_permission_sets
        - 09:30 - perm_sets_limited_users
        - 09:45 - profile_assignment_under5
        - 10:00 - profile_no_active_users
        - 10:15 - apex_classes_api_version
        - 10:30 - apex_triggers_api_version
        - 10:45 - security_health_check
        - 11:00 - salesforce_health_risks
        - 11:15 - workflow_rules_monitoring
        - 11:30 - dormant_salesforce_users
        - 11:45 - dormant_portal_users
        - 12:00 - total_queues_per_object
        - 12:15 - queues_with_no_members
        - 12:30 - queues_with_zero_open_cases
        - 12:45 - public_groups_with_no_members
        - 13:00 - dashboards_with_inactive_users
        - 13:15 - scheduled_apex_jobs_monitoring
    """
    # Execute each task once at script startup to populate initial metrics
    # Critical functions (5-minute interval) are executed first, followed by hourly and daily functions
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
    monitor_forbidden_profile_assignments(sf)
    monitor_org_wide_sharing_settings(sf)
    expose_suspicious_records(sf)
    get_deployment_status(sf)
    geolocation(sf, chunk_size=100)
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
    scheduled_apex_jobs_monitoring(sf)
    logger.info("Initial execution completed, scheduling tasks with APScheduler...")

    # Critical Functions - Every 5 minutes (*/5)
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

    # Daily Business Functions (07:30-09:00)
    # Staggered to prevent resource spikes from simultaneous execution
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
    
    # Tech Debt Monitoring Block (09:15-13:15)
    # 17 functions staggered at 15-minute intervals to prevent resource conflicts
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
    
    schedule = get_schedule_config('scheduled_apex_jobs_monitoring', {'hour': '13', 'minute': '15'})
    if schedule:
        scheduler.add_job(
            func=lambda: scheduled_apex_jobs_monitoring(sf),
            trigger=CronTrigger(**schedule),
            id='scheduled_apex_jobs_monitoring',
            name='Scheduled Apex Jobs Monitoring'
        )

    # Performance & Apex Monitoring (06:00-07:30)
    # 7 functions staggered at 15-minute intervals for comprehensive daily monitoring
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

    # Hourly Monitoring Functions
    # Staggered at :00, :10/:50, :20, :40 to distribute load across the hour
    schedule = get_schedule_config('hourly_analyse_bulk_api', {'minute': '0'})
    if schedule:
        scheduler.add_job(
            func=lambda: hourly_analyse_bulk_api(sf),
            trigger=CronTrigger(**schedule),
            id='hourly_analyse_bulk_api',
            name='Hourly Analyse Bulk API'
        )
    
    schedule = get_schedule_config('get_salesforce_licenses', {'minute': '10,50'})
    if schedule:
        scheduler.add_job(
            func=lambda: get_salesforce_licenses(sf),
            trigger=CronTrigger(**schedule),
            id='get_salesforce_licenses',
            name='Get Salesforce Licenses'
        )
    
    schedule = get_schedule_config('hourly_observe_user_querying_large_records', {'minute': '20'})
    if schedule:
        scheduler.add_job(
            func=lambda: hourly_observe_user_querying_large_records(sf),
            trigger=CronTrigger(**schedule),
            id='hourly_observe_user_querying_large_records',
            name='Hourly Observe User Querying Large Records'
        )
    
    schedule = get_schedule_config('hourly_report_export_records', {'minute': '40'})
    if schedule:
        scheduler.add_job(
            func=lambda: hourly_report_export_records(sf),
            trigger=CronTrigger(**schedule),
            id='hourly_report_export_records',
            name='Hourly Report Export Records'
        )
    
    # Audit Functions - Hourly
    schedule = get_schedule_config('monitor_forbidden_profile_assignments', {'minute': '30'})
    if schedule:
        scheduler.add_job(
            func=lambda: monitor_forbidden_profile_assignments(sf),
            trigger=CronTrigger(**schedule),
            id='monitor_forbidden_profile_assignments',
            name='Monitor Forbidden Profile Assignments'
        )

    # Audit Functions - Daily
    schedule = get_schedule_config('expose_suspicious_records', {'hour': '8', 'minute': '30'})
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
