'''
    Payment gateway and method functions.
'''
from datetime import datetime, timedelta

from cloudwatch_logging import logger
from constants import QUERY_TIMEOUT_SECONDS
import pytz


def get_time_threshold(minutes=5):
    '''Returns a formatted string of the time threshold
    for the last specified number of minutes in GMT timezone.'''
    gmt_timezone = pytz.timezone('GMT')
    current_time = datetime.now(gmt_timezone)
    time_threshold = current_time - timedelta(minutes=minutes)

    return time_threshold.strftime("%Y-%m-%dT%H:%M:%SZ")


def query_records(sf, soql_query):
    '''fetch payment gateways for FullQA'''

    result = sf.query(soql_query, timeout=QUERY_TIMEOUT_SECONDS)
    return result['records'] if 'records' in result else []


def monitor_payment_method_status(sf, pms_gauge, minutes):
    '''monitors changes in Payment method status for FullQA'''

    logger.info("Getting Payment Methods status from FullQA...")

    time_threshold_str = get_time_threshold(minutes)

    try:
        query_payment_method_record = (
            f"SELECT blng__Active__c, blng__AutoPay__C, blng__PaymentGateway__r.Name, \
            blng__PaymentGatewayToken__c, Id, Name, CreatedBy.Name, LastModifiedDate \
            FROM blng__PaymentMethod__c \
            WHERE blng__Active__c = true AND LastModifiedDate > {time_threshold_str} \
            ORDER BY LastModifiedDate DESC"
        )
        changes = query_records(sf, query_payment_method_record)

        if not changes:
            logger.info("No recent changes in Active billing field for Payment method.")
            # Set default label with value 0 to indicate no data
            pms_gauge.labels(
                billing_active_status='N/A',
                billing_autopay_status='N/A',
                billing_payment_gateway_name='N/A',
                payment_gateway_token='N/A',
                payment_method_id='N/A',
                payment_method_name='N/A',
                user_name='N/A',
                last_modified_date='N/A'
            ).set(0)
            return

        for change in changes:
            billing_active_status=change.get('blng__Active__c', 'Unknown')
            billing_autopay_status=change.get('blng__AutoPay__c', 'Unknown')
            billing_payment_gateway_name=change.get('blng__PaymentGateway__r', {}).get('Name', 'Unknown')
            payment_gateway_token=change.get('blng__PaymentGatewayToken__c', 'Unknown')
            payment_method_id=change.get('Id', 'Unknown')
            payment_method_name=change.get('Name', 'Unknown')
            user_name=change.get('CreatedBy', {}).get('Name', 'Unknown')
            last_modified_date=change.get('LastModifiedDate', 'Unknown')

            pms_gauge.labels(
                billing_active_status=billing_active_status,
                billing_autopay_status=billing_autopay_status,
                billing_payment_gateway_name=billing_payment_gateway_name,
                payment_gateway_token=payment_gateway_token,
                payment_method_id=payment_method_id,
                payment_method_name=payment_method_name,
                user_name=user_name,
                last_modified_date=last_modified_date
            ).set(1)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("An unexpected error occurred during monitoring Payment method status: %s", e)


def monitor_payment_gateway_status(sf, pgs_gauge, minutes):
    '''monitors changes in Payment Gateway status for FullQA'''

    logger.info("Getting Payment Gateways status from FullQA...")
    time_threshold_str = get_time_threshold(minutes)

    try:
        query_gateway_record = (
            f"SELECT LastModifiedBy.Name, blng__Active__c, blng__Default__c, blng__GatewayType__c, Id, Name, LastModifiedDate \
            FROM blng__PaymentGateway__c \
            WHERE Name in ('CyberSource (CC)', 'CyberSource (ACH)') AND LastModifiedDate > {time_threshold_str} \
            ORDER BY LastModifiedDate DESC"
        )
        changes = query_records(sf, query_gateway_record)

        if not changes:
            logger.info("No Payment Gateways found.")
            # Set default label with value 0 to indicate no data
            pgs_gauge.labels(
                billing_active_status='N/A',
                billing_default_status='N/A',
                billing_gateway_type='N/A',
                payment_gateway_name='N/A',
                record_id='N/A',
                user_name='N/A',
                last_modified_date='N/A'
            ).set(0)
            return

        processed_gateways = set()

        for change in changes:
            payment_gateway_name = change.get('Name', 'Unknown')
            processed_gateways.add(payment_gateway_name)

            # Set value to 1 only if gateway is active or default
            is_active = change.get('blng__Active__c', False)
            is_default = change.get('blng__Default__c', False)
            metric_value = 1 if (is_active or is_default) else 0

            billing_active_status=change.get('blng__Active__c', 'Unknown')
            billing_default_status=change.get('blng__Default__c', 'Unknown')
            billing_gateway_type=change.get('blng__GatewayType__c', 'Unknown')
            record_id=change.get('Id', 'Unknown')
            user_name=change.get('LastModifiedBy', {}).get('Name', 'Unknown')
            last_modified_date=change.get('LastModifiedDate', 'Unknown')

            pgs_gauge.labels(
                billing_active_status=billing_active_status,
                billing_default_status=billing_default_status,
                billing_gateway_type=billing_gateway_type,
                payment_gateway_name=payment_gateway_name,
                record_id=record_id,
                user_name=user_name,
                last_modified_date=last_modified_date
            ).set(metric_value)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("An unexpected error occurred during monitoring Payment Gateway status: %s", e)
