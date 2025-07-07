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
from constants import SF_ALIAS
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
                       profile_no_active_users, perm_sets_limited_users)

def schedule_tasks():
    """
    Schedule all tasks as per the required intervals.
    """
    # Execute each task once at script startup
    logger.info("Executing tasks at startup...")
    monitor_salesforce_limits(SF_ALIAS)
    get_salesforce_licenses(SF_ALIAS)
    get_salesforce_instance(SF_ALIAS)
    daily_analyse_bulk_api(SF_ALIAS)
    get_deployment_status(SF_ALIAS)
    geolocation(SF_ALIAS, chunk_size=100)
    community_login_error_logger_details(SF_ALIAS)
    community_registration_error_logger_details(SF_ALIAS)
    hourly_analyse_bulk_api(SF_ALIAS)
    get_salesforce_ept_and_apt(SF_ALIAS)
    monitor_login_events(SF_ALIAS)
    async_apex_job_status(SF_ALIAS)
    monitor_apex_execution_time(SF_ALIAS)
    async_apex_execution_summary(SF_ALIAS)
    concurrent_apex_errors(SF_ALIAS)
    expose_concurrent_long_running_apex_errors(SF_ALIAS)
    expose_apex_exception_metrics(SF_ALIAS)
    hourly_observe_user_querying_large_records(SF_ALIAS)
    monitor_org_wide_sharing_settings(SF_ALIAS)
    expose_suspicious_records(SF_ALIAS)
    unassigned_permission_sets(SF_ALIAS)
    profile_assignment_under5(SF_ALIAS)
    profile_no_active_users(SF_ALIAS)
    perm_sets_limited_users(SF_ALIAS)
    logger.info("Initial execution completed, scheduling tasks...")

    # Every 5 minutes
    schedule.every(5).minutes.do(lambda: monitor_salesforce_limits(SF_ALIAS))
    schedule.every(5).minutes.do(lambda: get_salesforce_licenses(SF_ALIAS))
    schedule.every(5).minutes.do(lambda: get_salesforce_instance(SF_ALIAS))

    # Twice a day
    schedule.every().day.at("08:00").do(lambda: daily_analyse_bulk_api(SF_ALIAS))
    schedule.every().day.at("20:00").do(lambda: daily_analyse_bulk_api(SF_ALIAS))
    schedule.every().day.at("08:00").do(lambda: get_deployment_status(SF_ALIAS))
    schedule.every().day.at("20:00").do(lambda: get_deployment_status(SF_ALIAS))
    schedule.every().day.at("08:00").do(lambda: geolocation(SF_ALIAS, chunk_size=100))
    schedule.every().day.at("20:00").do(lambda: geolocation(SF_ALIAS, chunk_size=100))
    schedule.every().day.at("08:00").do(lambda: community_login_error_logger_details(SF_ALIAS))
    schedule.every().day.at("20:00").do(lambda: community_login_error_logger_details(SF_ALIAS))
    schedule.every().day.at("08:00").do(lambda: community_registration_error_logger_details(SF_ALIAS))
    schedule.every().day.at("20:00").do(lambda: community_registration_error_logger_details(SF_ALIAS))
    schedule.every().day.at("08:00").do(lambda: monitor_org_wide_sharing_settings(SF_ALIAS))
    schedule.every().day.at("20:00").do(lambda: monitor_org_wide_sharing_settings(SF_ALIAS))

    # Once in a day
    schedule.every().day.at("00:05").do(lambda: expose_concurrent_long_running_apex_errors(SF_ALIAS))
    schedule.every().day.at("00:00").do(lambda: expose_suspicious_records(SF_ALIAS))
    schedule.every().day.at("00:00").do(lambda: unassigned_permission_sets(SF_ALIAS))
    schedule.every().day.at("00:00").do(lambda: profile_assignment_under5(SF_ALIAS))
    schedule.every().day.at("00:00").do(lambda: profile_no_active_users(SF_ALIAS))
    schedule.every().day.at("00:00").do(lambda: perm_sets_limited_users(SF_ALIAS))

    # Every 30 minutes
    schedule.every(30).minutes.do(lambda: hourly_analyse_bulk_api(SF_ALIAS))
    schedule.every(30).minutes.do(lambda: get_salesforce_ept_and_apt(SF_ALIAS))
    schedule.every(30).minutes.do(lambda: monitor_login_events(SF_ALIAS))
    schedule.every(30).minutes.do(lambda: async_apex_job_status(SF_ALIAS))
    schedule.every(30).minutes.do(lambda: monitor_apex_execution_time(SF_ALIAS))
    schedule.every(30).minutes.do(lambda: async_apex_execution_summary(SF_ALIAS))
    schedule.every(30).minutes.do(lambda: concurrent_apex_errors(SF_ALIAS))
    schedule.every(30).minutes.do(lambda: expose_apex_exception_metrics(SF_ALIAS))
    schedule.every(30).minutes.do(lambda: hourly_observe_user_querying_large_records(SF_ALIAS))
    schedule.every(30).minutes.do(lambda: hourly_report_export_records(SF_ALIAS))


def main():
    """
    Main function. Runs tasks according to their respective schedules.
    """
    start_http_server(9001)
    get_salesforce_connection_url(url=os.getenv('SALESFORCE_AUTH_URL'), alias=SF_ALIAS)
    schedule_tasks()
    while True:
        schedule.run_pending()
        logger.info('Sleeping for 5 minutes...')
        time.sleep(300)
        logger.info('Resuming...')


if __name__ == '__main__':
    main()
