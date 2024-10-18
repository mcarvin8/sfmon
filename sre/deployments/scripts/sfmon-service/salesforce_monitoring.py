"""
    Monitor critical Salesforce endpoints.
"""
import os
import time

from prometheus_client import start_http_server
import schedule

from apex_jobs import (async_apex_job_status, monitor_apex_execution_time, expose_apex_exception_metrics,
                       concurrent_apex_errors, expose_concurrent_long_running_apex_errors, async_apex_execution_summary)
from bulk_api import daily_analyse_bulk_api, hourly_analyse_bulk_api
from cloudwatch_logging import logger
from community import community_login_error_logger_details, community_Registration_error_logger_details
from compliance import hourly_observe_user_querying_large_records
from connection_sf import get_salesforce_connection_url
from deployments import get_deployment_status
from ept_apt import get_salesforce_ept_and_apt
from overall_sf_org import monitor_salesforce_limits, get_salesforce_licenses, get_salesforce_instance
from user_login import monitor_login_events, geolocation


def schedule_tasks(sf):
    """
    Schedule all tasks as per the required intervals.
    """
    # Execute each task once at script startup
    logger.info("Executing tasks at startup...")
    monitor_salesforce_limits(dict(sf.limits()))
    get_salesforce_licenses(sf)
    get_salesforce_instance(sf)
    daily_analyse_bulk_api(sf)
    get_deployment_status(sf)
    geolocation(sf, chunk_size=100)
    community_login_error_logger_details(sf)
    community_Registration_error_logger_details(sf)
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
    logger.info("Initial execution completed, scheduling tasks...")

    # Every 5 minutes
    schedule.every(5).minutes.do(lambda: monitor_salesforce_limits(dict(sf.limits())))
    schedule.every(5).minutes.do(lambda: get_salesforce_licenses(sf))
    schedule.every(5).minutes.do(lambda: get_salesforce_instance(sf))

    # Twice a day
    schedule.every().day.at("08:00").do(lambda: daily_analyse_bulk_api(sf))
    schedule.every().day.at("20:00").do(lambda: daily_analyse_bulk_api(sf))
    schedule.every().day.at("08:00").do(lambda: get_deployment_status(sf))
    schedule.every().day.at("20:00").do(lambda: get_deployment_status(sf))
    schedule.every().day.at("08:00").do(lambda: geolocation(sf, chunk_size=100))
    schedule.every().day.at("20:00").do(lambda: geolocation(sf, chunk_size=100))
    schedule.every().day.at("08:00").do(lambda: community_login_error_logger_details(sf))
    schedule.every().day.at("20:00").do(lambda: community_login_error_logger_details(sf))
    schedule.every().day.at("08:00").do(lambda: community_Registration_error_logger_details(sf))
    schedule.every().day.at("20:00").do(lambda: community_Registration_error_logger_details(sf))

    # Once in a day
    schedule.every().day.at("00:00").do(lambda: expose_concurrent_long_running_apex_errors(sf))

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


def main():
    """
    Main function. Runs tasks according to their respective schedules.
    """
    start_http_server(9001)
    sf = get_salesforce_connection_url(url=os.getenv('SALESFORCE_AUTH_URL'))
    schedule_tasks(sf)
    while True:
        schedule.run_pending()
        logger.info('Sleeping for 5 minutes...')
        time.sleep(300)
        logger.info('Resuming...')


if __name__ == '__main__':
    main()
