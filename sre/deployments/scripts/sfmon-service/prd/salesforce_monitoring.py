"""
    Monitor critical Salesforce endpoints.
"""
import os
import time

from prometheus_client import start_http_server
import schedule

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
from constants import PRD_ALIAS
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
                       deprecated_apex_classes)

def schedule_tasks(sf):
    """
    Schedule all tasks as per the required intervals.
    """
    # Execute each task once at script startup
    logger.info("Executing tasks at startup...")
    monitor_salesforce_limits(PRD_ALIAS)
    get_salesforce_licenses(PRD_ALIAS)
    get_salesforce_instance(PRD_ALIAS)
    daily_analyse_bulk_api(sf)
    get_deployment_status(PRD_ALIAS)
    geolocation(sf, chunk_size=100)
    community_login_error_logger_details(PRD_ALIAS)
    community_registration_error_logger_details(PRD_ALIAS)
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
    monitor_org_wide_sharing_settings(PRD_ALIAS)
    expose_suspicious_records(sf)
    unassigned_permission_sets(PRD_ALIAS)
    profile_assignment_under5(PRD_ALIAS)
    profile_no_active_users(PRD_ALIAS)
    perm_sets_limited_users(PRD_ALIAS)
    deprecated_apex_classes(PRD_ALIAS)
    logger.info("Initial execution completed, scheduling tasks...")

    # Every 5 minutes
    schedule.every(5).minutes.do(lambda: monitor_salesforce_limits(PRD_ALIAS))
    schedule.every(5).minutes.do(lambda: get_salesforce_licenses(PRD_ALIAS))
    schedule.every(5).minutes.do(lambda: get_salesforce_instance(PRD_ALIAS))

    # Twice a day
    schedule.every().day.at("08:00").do(lambda: daily_analyse_bulk_api(sf))
    schedule.every().day.at("20:00").do(lambda: daily_analyse_bulk_api(sf))
    schedule.every().day.at("08:00").do(lambda: get_deployment_status(PRD_ALIAS))
    schedule.every().day.at("20:00").do(lambda: get_deployment_status(PRD_ALIAS))
    schedule.every().day.at("08:00").do(lambda: geolocation(sf, chunk_size=100))
    schedule.every().day.at("20:00").do(lambda: geolocation(sf, chunk_size=100))
    schedule.every().day.at("08:00").do(lambda: community_login_error_logger_details(PRD_ALIAS))
    schedule.every().day.at("20:00").do(lambda: community_login_error_logger_details(PRD_ALIAS))
    schedule.every().day.at("08:00").do(lambda: community_registration_error_logger_details(PRD_ALIAS))
    schedule.every().day.at("20:00").do(lambda: community_registration_error_logger_details(PRD_ALIAS))
    schedule.every().day.at("08:00").do(lambda: monitor_org_wide_sharing_settings(PRD_ALIAS))
    schedule.every().day.at("20:00").do(lambda: monitor_org_wide_sharing_settings(PRD_ALIAS))

    # Once in a day
    schedule.every().day.at("00:05").do(lambda: expose_concurrent_long_running_apex_errors(sf))
    schedule.every().day.at("00:00").do(lambda: expose_suspicious_records(sf))
    schedule.every().day.at("00:00").do(lambda: unassigned_permission_sets(PRD_ALIAS))
    schedule.every().day.at("00:00").do(lambda: profile_assignment_under5(PRD_ALIAS))
    schedule.every().day.at("00:00").do(lambda: profile_no_active_users(PRD_ALIAS))
    schedule.every().day.at("00:00").do(lambda: perm_sets_limited_users(PRD_ALIAS))
    schedule.every().day.at("00:00").do(lambda: deprecated_apex_classes(PRD_ALIAS))

    # Every 30 minutes
    schedule.every(30).minutes.do(lambda: hourly_analyse_bulk_api(sf))
    schedule.every(30).minutes.do(lambda: get_salesforce_ept_and_apt(sf))
    schedule.every(30).minutes.do(lambda: monitor_login_events(sf))
    schedule.every(30).minutes.do(lambda: async_apex_job_status(sf))
    schedule.every(30).minutes.do(lambda: monitor_apex_execution_time(sf))
    schedule.every(30).minutes.do(lambda: async_apex_execution_summary(sf))
    schedule.every(30).minutes.do(lambda: concurrent_apex_errors(sf))
    schedule.every(30).minutes.do(lambda: expose_apex_exception_metrics(sf))
    schedule.every(30).minutes.do(lambda: hourly_observe_user_querying_large_records(sf))
    schedule.every(30).minutes.do(lambda: hourly_report_export_records(sf))


def main():
    """
    Main function. Runs tasks according to their respective schedules.
    """
    start_http_server(9001)
    sf = get_salesforce_connection_url(url=os.getenv('PRODUCTION_AUTH_URL'), alias=PRD_ALIAS)
    schedule_tasks(sf)
    while True:
        schedule.run_pending()
        logger.info('Sleeping for 5 minutes...')
        time.sleep(300)
        logger.info('Resuming...')


if __name__ == '__main__':
    main()
