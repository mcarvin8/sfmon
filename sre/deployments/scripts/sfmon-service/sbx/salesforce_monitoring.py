"""
    Monitor critical Salesforce endpoints.
"""
import os
import time

from prometheus_client import start_http_server
import schedule

from cloudwatch_logging import logger
from compliance import (track_email_deliverability_change,
                        track_contacts_with_valid_emails)
from constants import (DEV_ALIAS, FQA_ALIAS, FQAB_ALIAS)
from connection_sf import get_salesforce_connection_url
from gauges import (payment_method_status_gauge,
                    payment_gateway_status_gauge,
                    payment_method_status_gauge_fqab,
                    payment_gateway_status_gauge_fqab)
from overall_sf_org import (get_salesforce_instance)
from payment_gateways_and_methods import (monitor_payment_method_status,
                                          monitor_payment_gateway_status)


def schedule_tasks():
    """
    Schedule all tasks as per the required intervals.
    """

    # Execute each task once at script startup
    logger.info("Executing tasks at startup...")
    get_salesforce_instance(FQA_ALIAS, FQAB_ALIAS, DEV_ALIAS)
    track_email_deliverability_change(DEV_ALIAS, FQA_ALIAS, FQAB_ALIAS, minutes=5)
    track_contacts_with_valid_emails(FQA_ALIAS, FQAB_ALIAS, DEV_ALIAS)
    monitor_payment_gateway_status(FQA_ALIAS, payment_gateway_status_gauge, minutes=5)
    monitor_payment_method_status(FQA_ALIAS, payment_method_status_gauge, minutes=5)
    monitor_payment_gateway_status(FQAB_ALIAS, payment_gateway_status_gauge_fqab, minutes=5)
    monitor_payment_method_status(FQAB_ALIAS, payment_method_status_gauge_fqab, minutes=5)
    logger.info("Initial execution completed, scheduling tasks...")

    # Every 5 minutes
    schedule.every(5).minutes.do(lambda: get_salesforce_instance(FQA_ALIAS, FQAB_ALIAS, DEV_ALIAS))
    schedule.every(5).minutes.do(lambda: monitor_payment_gateway_status(FQA_ALIAS,
                                                                        payment_gateway_status_gauge,
                                                                        minutes=5))
    schedule.every(5).minutes.do(lambda: monitor_payment_method_status(FQA_ALIAS,
                                                                       payment_method_status_gauge,
                                                                       minutes=5))
    schedule.every(5).minutes.do(lambda: monitor_payment_gateway_status(FQAB_ALIAS,
                                                                        payment_gateway_status_gauge_fqab,
                                                                        minutes=5))
    schedule.every(5).minutes.do(lambda: monitor_payment_method_status(FQAB_ALIAS,
                                                                       payment_method_status_gauge_fqab,
                                                                       minutes=5))
    schedule.every(5).minutes.do(lambda: track_email_deliverability_change(DEV_ALIAS,
                                                                           FQA_ALIAS,
                                                                           FQAB_ALIAS,
                                                                           minutes=5))
    schedule.every(5).minutes.do(lambda: track_contacts_with_valid_emails(FQA_ALIAS,
                                                                           FQAB_ALIAS,
                                                                           DEV_ALIAS))


def main():
    """
    Main function. Runs tasks according to their respective schedules.
    """

    start_http_server(9001)
    get_salesforce_connection_url(url=os.getenv('FULLQA_AUTH_URL'), alias=FQA_ALIAS)
    get_salesforce_connection_url(url=os.getenv('FULLQAB_AUTH_URL'), alias=FQAB_ALIAS)
    get_salesforce_connection_url(url=os.getenv('DEV_AUTH_URL'), alias=DEV_ALIAS)
    schedule_tasks()
    while True:
        schedule.run_pending()
        logger.info('Sleeping for 5 minutes...')
        time.sleep(300)
        logger.info('Resuming...')


if __name__ == '__main__':
    main()
