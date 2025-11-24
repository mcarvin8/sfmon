"""
Salesforce Monitoring Service - Main Entry Point

This is the primary orchestration module for monitoring the Salesforce production environment.
It implements a comprehensive monitoring strategy with resource-optimized scheduling to track:
    - Salesforce org limits and API usage
    - Apex execution, errors, and flex queue
    - Bulk API operations (daily and hourly)
    - User login events and geolocation analysis
    - Community login and registration errors
    - Deployment and validation status
    - Org-wide sharing settings changes
    - Compliance violations and suspicious audit trail activities
    - EPT/APT performance metrics
    - Report exports
    - Integration user password expiration

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

Functions:
    - schedule_tasks: Configures all APScheduler jobs with optimized timing
    - main: Entry point that initializes connection and starts scheduler
"""
import os

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
from community import (community_login_error_logger_details,
                       community_registration_error_logger_details)
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

def schedule_tasks(sf, scheduler):
    """
    Schedule all tasks using APScheduler with cron syntax for precise timing.
    
    OPTIMIZATION STRATEGY (Resource Load Distribution):
    - ALL non-critical functions are staggered to prevent CPU/memory spikes
    - Resource-intensive functions have 15+ minute intervals between executions
    - Functions are grouped by type and scheduled in logical time blocks:
      * 06:00-07:30: Performance & Apex monitoring (15-minute intervals)
      * 07:30-08:45: Daily business functions (15-minute intervals)  
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
    community_login_error_logger_details(sf)
    community_registration_error_logger_details(sf)
    monitor_integration_user_passwords(sf)
    logger.info("Initial execution completed, scheduling tasks with APScheduler...")

    # Every 5 minutes on the dot (0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55)
    scheduler.add_job(
        func=lambda: monitor_salesforce_limits(sf),
        trigger=CronTrigger(minute='*/5'),
        id='monitor_salesforce_limits',
        name='Monitor Salesforce Limits'
    )
    scheduler.add_job(
        func=lambda: get_salesforce_instance(sf),
        trigger=CronTrigger(minute='*/5'),
        id='get_salesforce_instance',
        name='Get Salesforce Instance'
    )
    scheduler.add_job(
        func=lambda: monitor_apex_flex_queue(sf),
        trigger=CronTrigger(minute='*/5'),
        id='monitor_apex_flex_queue',
        name='Monitor Apex Flex Queue'
    )

    # Daily Business Functions - Staggered across morning hours (07:30-08:45)
    # to prevent resource spikes from simultaneous execution

    # Morning Business Hours Block (07:30-08:15)
    scheduler.add_job(
        func=lambda: daily_analyse_bulk_api(sf),
        trigger=CronTrigger(hour='7', minute='30'),
        id='daily_analyse_bulk_api',
        name='Daily Analyse Bulk API'
    )
    scheduler.add_job(
        func=lambda: get_deployment_status(sf),
        trigger=CronTrigger(hour='7', minute='45'),
        id='get_deployment_status',
        name='Get Deployment Status'
    )
    scheduler.add_job(
        func=lambda: geolocation(sf, chunk_size=100),
        trigger=CronTrigger(hour='8', minute='0'),
        id='geolocation',
        name='Geolocation Analysis'
    )

    # Community Monitoring Block (08:15-08:45)
    scheduler.add_job(
        func=lambda: community_login_error_logger_details(sf),
        trigger=CronTrigger(hour='8', minute='15'),
        id='community_login_error_logger_details',
        name='Community Login Error Logger'
    )
    scheduler.add_job(
        func=lambda: community_registration_error_logger_details(sf),
        trigger=CronTrigger(hour='8', minute='30'),
        id='community_registration_error_logger_details',
        name='Community Registration Error Logger'
    )
    scheduler.add_job(
        func=lambda: monitor_org_wide_sharing_settings(sf),
        trigger=CronTrigger(hour='8', minute='45'),
        id='monitor_org_wide_sharing_settings',
        name='Monitor Org Wide Sharing Settings'
    )
    scheduler.add_job(
        func=lambda: monitor_integration_user_passwords(sf),
        trigger=CronTrigger(hour='9', minute='0'),
        id='monitor_integration_user_passwords',
        name='Monitor Integration User Passwords'
    )

    # Performance & Apex Monitoring - Staggered across early morning (06:00-07:30)
    # Spread to avoid resource conflicts and provide comprehensive daily monitoring

    # Performance Metrics Block (06:00-06:30)
    scheduler.add_job(
        func=lambda: get_salesforce_ept_and_apt(sf),
        trigger=CronTrigger(hour='6', minute='0'),
        id='get_salesforce_ept_and_apt',
        name='Get Salesforce EPT and APT'
    )
    scheduler.add_job(
        func=lambda: monitor_login_events(sf),
        trigger=CronTrigger(hour='6', minute='15'),
        id='monitor_login_events',
        name='Monitor Login Events'
    )
    scheduler.add_job(
        func=lambda: async_apex_job_status(sf),
        trigger=CronTrigger(hour='6', minute='30'),
        id='async_apex_job_status',
        name='Async Apex Job Status'
    )

    # Apex Performance Analysis Block (06:45-07:15)
    scheduler.add_job(
        func=lambda: monitor_apex_execution_time(sf),
        trigger=CronTrigger(hour='6', minute='45'),
        id='monitor_apex_execution_time',
        name='Monitor Apex Execution Time'
    )
    scheduler.add_job(
        func=lambda: async_apex_execution_summary(sf),
        trigger=CronTrigger(hour='7', minute='0'),
        id='async_apex_execution_summary',
        name='Async Apex Execution Summary'
    )

    # Apex Error Monitoring Block (07:15-07:30)
    scheduler.add_job(
        func=lambda: concurrent_apex_errors(sf),
        trigger=CronTrigger(hour='7', minute='15'),
        id='concurrent_apex_errors',
        name='Concurrent Apex Errors'
    )
    scheduler.add_job(
        func=lambda: expose_apex_exception_metrics(sf),
        trigger=CronTrigger(hour='7', minute='30'),
        id='expose_apex_exception_metrics',
        name='Expose Apex Exception Metrics'
    )

    # Hourly Monitoring Functions - Staggered to prevent simultaneous execution
    # Functions run at different minute intervals to distribute load

    # Bulk API Analysis - Every hour at :00
    scheduler.add_job(
        func=lambda: hourly_analyse_bulk_api(sf),
        trigger=CronTrigger(minute='0'),
        id='hourly_analyse_bulk_api',
        name='Hourly Analyse Bulk API'
    )

    # Salesforce Licenses - Twice per hour at :10 and :50
    scheduler.add_job(
        func=lambda: get_salesforce_licenses(sf),
        trigger=CronTrigger(minute='10,50'),
        id='get_salesforce_licenses',
        name='Get Salesforce Licenses'
    )

    # User Query Monitoring - Every hour at :20 (20 minutes after bulk API)
    scheduler.add_job(
        func=lambda: hourly_observe_user_querying_large_records(sf),
        trigger=CronTrigger(minute='20'),
        id='hourly_observe_user_querying_large_records',
        name='Hourly Observe User Querying Large Records'
    )

    # Report Export Monitoring - Every hour at :40 (40 minutes after bulk API)
    scheduler.add_job(
        func=lambda: hourly_report_export_records(sf),
        trigger=CronTrigger(minute='40'),
        id='hourly_report_export_records',
        name='Hourly Report Export Records'
    )

    logger.info("All jobs scheduled successfully with APScheduler")


def main():
    """
    Main function. Runs tasks using APScheduler with cron syntax for precise timing.
    """
    start_http_server(9001)
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
