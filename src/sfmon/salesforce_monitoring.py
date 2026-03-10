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
    - Hourly functions distributed across :05, :15, :25, :35, :45, :55 minutes (off the hour)
    - Daily functions scheduled during off-peak hours to minimize business impact:
        * 06:00-07:35: Performance & Apex monitoring
        * 07:30-08:30: Daily business functions
        * 02:00-06:00: Tech debt monitoring (17 functions) - OFF-PEAK

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
    async_apex_job_status,
    monitor_apex_execution_time,
    expose_apex_exception_metrics,
    concurrent_apex_errors,
    expose_concurrent_long_running_apex_errors,
    async_apex_execution_summary,
    daily_analyse_bulk_api,
    hourly_analyse_bulk_api,
    monitor_salesforce_limits,
    get_salesforce_licenses,
    get_salesforce_instance,
    get_salesforce_ept_and_apt,
)

# Audit and compliance functions (audit package)
from audit import (
    hourly_observe_user_querying_large_records,
    expose_suspicious_records,
    monitor_org_wide_sharing_settings,
    monitor_forbidden_profile_assignments,
    get_deployment_status,
    monitor_login_events,
    geolocation,
    hourly_report_export_records,
)

# Tech debt monitoring functions (tech_debt package)
from tech_debt import (
    apex_classes_api_version,
    apex_triggers_api_version,
    workflow_rules_monitoring,
    apex_used_limits_monitoring,
    unassigned_permission_sets,
    perm_sets_limited_users,
    profile_assignment_under5,
    profile_no_active_users,
    security_health_check,
    salesforce_health_risks,
    dormant_salesforce_users,
    dormant_portal_users,
    total_queues_per_object,
    queues_with_no_members,
    queues_with_zero_open_cases,
    public_groups_with_no_members,
    dashboards_with_inactive_users,
    scheduled_apex_jobs_monitoring,
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


def _add_job_with_schedule(scheduler, sf, job_id, schedule, func, job_name):
    """Add a job to the scheduler with the given schedule."""
    scheduler.add_job(
        func=lambda f=func: f(sf),
        trigger=CronTrigger(**schedule),
        id=job_id,
        name=job_name,
    )


def schedule_tasks(sf, scheduler):
    """
    Schedule all tasks using APScheduler with cron syntax for precise timing.

    OPTIMIZATION STRATEGY (Resource Load Distribution):
    - ALL non-critical functions are staggered to prevent CPU/memory spikes
    - Hourly functions offset 5 minutes from the hour to avoid system congestion
    - Tech debt functions run during off-peak hours (2 AM - 6 AM) to minimize business impact
    - Resource-intensive functions have 15-minute intervals between executions

    SCHEDULE OVERVIEW:

    Critical Functions (Every 5 minutes):
        - monitor_salesforce_limits
        - get_salesforce_instance
        - monitor_apex_flex_queue

    Hourly Functions (staggered 5 mins off the hour):
        - :05 - hourly_analyse_bulk_api
        - :15 - get_salesforce_licenses
        - :25 - hourly_observe_user_querying_large_records
        - :35 - monitor_forbidden_profile_assignments
        - :45 - hourly_report_export_records
        - :55 - get_deployment_status

    Daily Performance & Apex Monitoring (06:00-07:35):
        - 06:00 - get_salesforce_ept_and_apt
        - 06:15 - monitor_login_events
        - 06:30 - async_apex_job_status
        - 06:45 - monitor_apex_execution_time
        - 07:00 - async_apex_execution_summary
        - 07:15 - concurrent_apex_errors
        - 07:25 - expose_apex_exception_metrics
        - 07:35 - expose_concurrent_long_running_apex_errors

    Daily Business Functions (07:30-08:30):
        - 07:30 - daily_analyse_bulk_api
        - 08:00 - geolocation
        - 08:15 - expose_suspicious_records
        - 08:30 - monitor_org_wide_sharing_settings

    Daily Tech Debt Monitoring (02:00-06:00) - OFF-PEAK HOURS:
        - 02:00 - unassigned_permission_sets
        - 02:15 - perm_sets_limited_users
        - 02:30 - profile_assignment_under5
        - 02:45 - profile_no_active_users
        - 03:00 - apex_classes_api_version
        - 03:05 - apex_used_limits_monitoring
        - 03:15 - apex_triggers_api_version
        - 03:30 - security_health_check
        - 03:45 - salesforce_health_risks
        - 04:00 - workflow_rules_monitoring
        - 04:15 - dormant_salesforce_users
        - 04:30 - dormant_portal_users
        - 04:45 - total_queues_per_object
        - 05:00 - queues_with_no_members
        - 05:15 - queues_with_zero_open_cases
        - 05:30 - public_groups_with_no_members
        - 05:45 - dashboards_with_inactive_users
        - 05:55 - scheduled_apex_jobs_monitoring
    """
    scheduled_jobs = [
        (
            "monitor_salesforce_limits",
            {"minute": "*/5"},
            monitor_salesforce_limits,
            "Monitor Salesforce Limits",
        ),
        (
            "get_salesforce_instance",
            {"minute": "*/5"},
            get_salesforce_instance,
            "Get Salesforce Instance",
        ),
        (
            "monitor_apex_flex_queue",
            {"minute": "*/5"},
            monitor_apex_flex_queue,
            "Monitor Apex Flex Queue",
        ),
        (
            "daily_analyse_bulk_api",
            {"hour": "7", "minute": "30"},
            daily_analyse_bulk_api,
            "Daily Analyse Bulk API",
        ),
        (
            "geolocation",
            {"hour": "8", "minute": "0"},
            geolocation,
            "Geolocation Analysis",
        ),
        (
            "expose_suspicious_records",
            {"hour": "8", "minute": "15"},
            expose_suspicious_records,
            "Expose Suspicious Records",
        ),
        (
            "monitor_org_wide_sharing_settings",
            {"hour": "8", "minute": "30"},
            monitor_org_wide_sharing_settings,
            "Monitor Org Wide Sharing Settings",
        ),
        (
            "unassigned_permission_sets",
            {"hour": "2", "minute": "0"},
            unassigned_permission_sets,
            "Unassigned Permission Sets",
        ),
        (
            "perm_sets_limited_users",
            {"hour": "2", "minute": "15"},
            perm_sets_limited_users,
            "Permission Sets Limited Users",
        ),
        (
            "profile_assignment_under5",
            {"hour": "2", "minute": "30"},
            profile_assignment_under5,
            "Profile Assignment Under 5",
        ),
        (
            "profile_no_active_users",
            {"hour": "2", "minute": "45"},
            profile_no_active_users,
            "Profile No Active Users",
        ),
        (
            "apex_classes_api_version",
            {"hour": "3", "minute": "0"},
            apex_classes_api_version,
            "Apex Classes API Version",
        ),
        (
            "apex_used_limits_monitoring",
            {"hour": "3", "minute": "5"},
            apex_used_limits_monitoring,
            "Apex Used Limits Monitoring",
        ),
        (
            "apex_triggers_api_version",
            {"hour": "3", "minute": "15"},
            apex_triggers_api_version,
            "Apex Triggers API Version",
        ),
        (
            "security_health_check",
            {"hour": "3", "minute": "30"},
            security_health_check,
            "Security Health Check",
        ),
        (
            "salesforce_health_risks",
            {"hour": "3", "minute": "45"},
            salesforce_health_risks,
            "Salesforce Health Risks",
        ),
        (
            "workflow_rules_monitoring",
            {"hour": "4", "minute": "0"},
            workflow_rules_monitoring,
            "Workflow Rules Monitoring",
        ),
        (
            "dormant_salesforce_users",
            {"hour": "4", "minute": "15"},
            dormant_salesforce_users,
            "Dormant Salesforce Users",
        ),
        (
            "dormant_portal_users",
            {"hour": "4", "minute": "30"},
            dormant_portal_users,
            "Dormant Portal Users",
        ),
        (
            "total_queues_per_object",
            {"hour": "4", "minute": "45"},
            total_queues_per_object,
            "Total Queues Per Object",
        ),
        (
            "queues_with_no_members",
            {"hour": "5", "minute": "0"},
            queues_with_no_members,
            "Queues With No Members",
        ),
        (
            "queues_with_zero_open_cases",
            {"hour": "5", "minute": "15"},
            queues_with_zero_open_cases,
            "Queues With Zero Open Cases",
        ),
        (
            "public_groups_with_no_members",
            {"hour": "5", "minute": "30"},
            public_groups_with_no_members,
            "Public Groups With No Members",
        ),
        (
            "dashboards_with_inactive_users",
            {"hour": "5", "minute": "45"},
            dashboards_with_inactive_users,
            "Dashboards With Inactive Users",
        ),
        (
            "scheduled_apex_jobs_monitoring",
            {"hour": "5", "minute": "55"},
            scheduled_apex_jobs_monitoring,
            "Scheduled Apex Jobs Monitoring",
        ),
        (
            "get_salesforce_ept_and_apt",
            {"hour": "6", "minute": "0"},
            get_salesforce_ept_and_apt,
            "Get Salesforce EPT and APT",
        ),
        (
            "monitor_login_events",
            {"hour": "6", "minute": "15"},
            monitor_login_events,
            "Monitor Login Events",
        ),
        (
            "async_apex_job_status",
            {"hour": "6", "minute": "30"},
            async_apex_job_status,
            "Async Apex Job Status",
        ),
        (
            "monitor_apex_execution_time",
            {"hour": "6", "minute": "45"},
            monitor_apex_execution_time,
            "Monitor Apex Execution Time",
        ),
        (
            "async_apex_execution_summary",
            {"hour": "7", "minute": "0"},
            async_apex_execution_summary,
            "Async Apex Execution Summary",
        ),
        (
            "concurrent_apex_errors",
            {"hour": "7", "minute": "15"},
            concurrent_apex_errors,
            "Concurrent Apex Errors",
        ),
        (
            "expose_apex_exception_metrics",
            {"hour": "7", "minute": "25"},
            expose_apex_exception_metrics,
            "Expose Apex Exception Metrics",
        ),
        (
            "expose_concurrent_long_running_apex_errors",
            {"hour": "7", "minute": "35"},
            expose_concurrent_long_running_apex_errors,
            "Expose Concurrent Long Running Apex Errors",
        ),
        (
            "hourly_analyse_bulk_api",
            {"minute": "5"},
            hourly_analyse_bulk_api,
            "Hourly Analyse Bulk API",
        ),
        (
            "get_salesforce_licenses",
            {"minute": "15"},
            get_salesforce_licenses,
            "Get Salesforce Licenses",
        ),
        (
            "hourly_observe_user_querying_large_records",
            {"minute": "25"},
            hourly_observe_user_querying_large_records,
            "Hourly Observe User Querying Large Records",
        ),
        (
            "monitor_forbidden_profile_assignments",
            {"minute": "35"},
            monitor_forbidden_profile_assignments,
            "Monitor Forbidden Profile Assignments",
        ),
        (
            "hourly_report_export_records",
            {"minute": "45"},
            hourly_report_export_records,
            "Hourly Report Export Records",
        ),
        (
            "get_deployment_status",
            {"minute": "55"},
            get_deployment_status,
            "Get Deployment Status",
        ),
    ]
    logger.info("Executing enabled tasks at startup (respecting config)...")
    for job_id, default_schedule, func, job_name in scheduled_jobs:
        schedule = get_schedule_config(job_id, default_schedule)
        if schedule:
            func(sf)  # initial run only for jobs enabled by config
            _add_job_with_schedule(scheduler, sf, job_id, schedule, func, job_name)
    logger.info("Initial execution completed, all jobs scheduled with APScheduler")


def main():
    """
    Main function. Runs tasks using APScheduler with cron syntax for precise timing.
    """
    # Start Prometheus metrics server
    metrics_port = int(os.getenv("METRICS_PORT", 9001))
    start_http_server(metrics_port)
    # Connect to Salesforce org
    sf = get_salesforce_connection_url(url=os.getenv("SALESFORCE_AUTH_URL"))
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


if __name__ == "__main__":
    main()
