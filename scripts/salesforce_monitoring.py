"""
    Monitor critical Salesforce endpoints.
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
from cloudwatch_logging import logger
from community import (community_login_error_logger_details,
                       community_registration_error_logger_details)
from compliance import (hourly_observe_user_querying_large_records, expose_suspicious_records)
from connection_sf import get_salesforce_connection_url
from deployments import get_deployment_status
from ept_apt import get_salesforce_ept_and_apt
from overall_sf_org import (monitor_salesforce_limits,
                            get_salesforce_licenses,
                            get_salesforce_instance)
from user_login import monitor_login_events, geolocation
from org_wide_sharing_setting import monitor_org_wide_sharing_settings
from report_export import hourly_report_export_records
from tech_debt import (unassigned_permission_sets, profile_assignment_under5,
                       profile_no_active_users, perm_sets_limited_users,
                       apex_classes_api_version)

def schedule_tasks(sf, scheduler):
    """
    Schedule all tasks using APScheduler with cron syntax for precise timing.
    """
    # Execute each task once at script startup
    logger.info("Executing tasks at startup...")
    monitor_salesforce_limits(sf)
    get_salesforce_licenses(sf)
    get_salesforce_instance(sf)
    daily_analyse_bulk_api(sf)
    get_deployment_status(sf)
    geolocation(sf, chunk_size=100)
    community_login_error_logger_details(sf)
    community_registration_error_logger_details(sf)
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
    unassigned_permission_sets(sf)
    profile_assignment_under5(sf)
    profile_no_active_users(sf)
    perm_sets_limited_users(sf)
    apex_classes_api_version(sf)
    monitor_apex_flex_queue(sf)
    logger.info("Initial execution completed, scheduling tasks with APScheduler...")

    # Every 5 minutes on the dot (0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55)
    scheduler.add_job(
        func=lambda: monitor_salesforce_limits(sf),
        trigger=CronTrigger(minute='*/5'),
        id='monitor_salesforce_limits',
        name='Monitor Salesforce Limits'
    )
    scheduler.add_job(
        func=lambda: get_salesforce_licenses(sf),
        trigger=CronTrigger(minute='*/5'),
        id='get_salesforce_licenses',
        name='Get Salesforce Licenses'
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

    # Twice a day
    scheduler.add_job(
        func=lambda: daily_analyse_bulk_api(sf),
        trigger=CronTrigger(hour='8,20', minute='0'),
        id='daily_analyse_bulk_api',
        name='Daily Analyse Bulk API'
    )
    scheduler.add_job(
        func=lambda: get_deployment_status(sf),
        trigger=CronTrigger(hour='8,20', minute='0'),
        id='get_deployment_status',
        name='Get Deployment Status'
    )
    scheduler.add_job(
        func=lambda: geolocation(sf, chunk_size=100),
        trigger=CronTrigger(hour='8,20', minute='0'),
        id='geolocation',
        name='Geolocation Analysis'
    )
    scheduler.add_job(
        func=lambda: community_login_error_logger_details(sf),
        trigger=CronTrigger(hour='8,20', minute='0'),
        id='community_login_error_logger_details',
        name='Community Login Error Logger'
    )
    scheduler.add_job(
        func=lambda: community_registration_error_logger_details(sf),
        trigger=CronTrigger(hour='8,20', minute='0'),
        id='community_registration_error_logger_details',
        name='Community Registration Error Logger'
    )
    scheduler.add_job(
        func=lambda: monitor_org_wide_sharing_settings(sf),
        trigger=CronTrigger(hour='8,20', minute='0'),
        id='monitor_org_wide_sharing_settings',
        name='Monitor Org Wide Sharing Settings'
    )
    scheduler.add_job(
        func=lambda: get_salesforce_ept_and_apt(sf),
        trigger=CronTrigger(hour='6,22', minute='0'),
        id='get_salesforce_ept_and_apt',
        name='Get Salesforce EPT and APT'
    )
    scheduler.add_job(
        func=lambda: monitor_login_events(sf),
        trigger=CronTrigger(hour='6,22', minute='0'),
        id='monitor_login_events',
        name='Monitor Login Events'
    )
    scheduler.add_job(
        func=lambda: async_apex_job_status(sf),
        trigger=CronTrigger(hour='6,22', minute='0'),
        id='async_apex_job_status',
        name='Async Apex Job Status'
    )
    scheduler.add_job(
        func=lambda: monitor_apex_execution_time(sf),
        trigger=CronTrigger(hour='6,22', minute='0'),
        id='monitor_apex_execution_time',
        name='Monitor Apex Execution Time'
    )
    scheduler.add_job(
        func=lambda: async_apex_execution_summary(sf),
        trigger=CronTrigger(hour='6,22', minute='0'),
        id='async_apex_execution_summary',
        name='Async Apex Execution Summary'
    )
    scheduler.add_job(
        func=lambda: concurrent_apex_errors(sf),
        trigger=CronTrigger(hour='6,22', minute='0'),
        id='concurrent_apex_errors',
        name='Concurrent Apex Errors'
    )
    scheduler.add_job(
        func=lambda: expose_apex_exception_metrics(sf),
        trigger=CronTrigger(hour='6,22', minute='0'),
        id='expose_apex_exception_metrics',
        name='Expose Apex Exception Metrics'
    )

    # Once a day at specific times
    scheduler.add_job(
        func=lambda: expose_concurrent_long_running_apex_errors(sf),
        trigger=CronTrigger(hour='0', minute='5'),
        id='expose_concurrent_long_running_apex_errors',
        name='Expose Concurrent Long Running Apex Errors'
    )
    scheduler.add_job(
        func=lambda: expose_suspicious_records(sf),
        trigger=CronTrigger(hour='0', minute='0'),
        id='expose_suspicious_records',
        name='Expose Suspicious Records'
    )
    scheduler.add_job(
        func=lambda: unassigned_permission_sets(sf),
        trigger=CronTrigger(hour='0', minute='0'),
        id='unassigned_permission_sets',
        name='Unassigned Permission Sets'
    )
    scheduler.add_job(
        func=lambda: profile_assignment_under5(sf),
        trigger=CronTrigger(hour='0', minute='0'),
        id='profile_assignment_under5',
        name='Profile Assignment Under 5'
    )
    scheduler.add_job(
        func=lambda: profile_no_active_users(sf),
        trigger=CronTrigger(hour='0', minute='0'),
        id='profile_no_active_users',
        name='Profile No Active Users'
    )
    scheduler.add_job(
        func=lambda: perm_sets_limited_users(sf),
        trigger=CronTrigger(hour='0', minute='0'),
        id='perm_sets_limited_users',
        name='Permission Sets Limited Users'
    )
    scheduler.add_job(
        func=lambda: apex_classes_api_version(sf),
        trigger=CronTrigger(hour='0', minute='0'),
        id='apex_classes_api_version',
        name='Apex Classes API Version'
    )

    # Every 30 minutes on the dot (0, 30)
    scheduler.add_job(
        func=lambda: hourly_analyse_bulk_api(sf),
        trigger=CronTrigger(minute='*/30'),
        id='hourly_analyse_bulk_api',
        name='Hourly Analyse Bulk API'
    )
    scheduler.add_job(
        func=lambda: hourly_observe_user_querying_large_records(sf),
        trigger=CronTrigger(minute='*/30'),
        id='hourly_observe_user_querying_large_records',
        name='Hourly Observe User Querying Large Records'
    )
    scheduler.add_job(
        func=lambda: hourly_report_export_records(sf),
        trigger=CronTrigger(minute='*/30'),
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
