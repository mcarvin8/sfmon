"""
Community Portal Monitoring Module

This module monitors Salesforce Community (PRM and GSP) login and registration failures
by querying SFDC_Logger__c custom object records. It tracks Error and Fatal level logs
to identify authentication issues, registration problems, and integration failures
affecting community users.

Monitored Communities:
    - Partner Relationship Management (PRM)
    - Global Service Portal (GSP)

Key Monitoring Areas:
    - Login failures and authentication errors
    - Registration process failures
    - Conversation ID issues
    - Avalara Identity integration errors
    - PRMP registration failures

Functions:
    - community_login_error_logger_details: Monitors login errors (last 7 days)
    - community_registration_error_logger_details: Monitors registration errors (last 7 days)

Log Sources:
    - Source: 'Community - Login'
    - Source: 'Community - Conversation Id'
    - Source: 'Community - Registration'
    - Source: 'GSP - Registration PRMP'
    - Source: 'AvalaraIdentityCreateAvataxAccount'

Metrics Exposed:
    - Error count by log level, message, and affected records
    - Callout response payloads for integration failures
    - Timestamp and user context for debugging
"""
from logger import logger
from gauges import community_login_error_metric, community_registration_error_metric
from query import query_records_all


def community_login_error_logger_details(sf):
    """
    Monitors Apex failure for login (PRM and GSP)
    from SFDC Logger records where source = 'Community - Login'
    and Log level is Error or Fatal
    """
    try:
        logger.info("Querying SFDC Logger Login records...")
        query = """
        SELECT Id, Name, Source_Name__c, CreatedDate, Log_Message__c, Record_Id__c, Log_Level__c 
        FROM SFDC_Logger__c 
        WHERE Source_Name__c = 'Community - Login' 
        AND Log_Level__c IN ('Error','Fatal') 
        AND CreatedDate = LAST_N_DAYS:7 
        ORDER BY CreatedDate DESC
        """
        results = query_records_all(sf, query)
        community_login_error_metric.clear()

        for record in results:
            # Expose logger details as Prometheus metrics
            community_login_error_metric.labels(
                id=record['Id'],
                name=record['Name'],
                log_level=record['Log_Level__c'],
                log_message=record['Log_Message__c'],
                record_id=record['Record_Id__c'],
                created_date=record['CreatedDate']
            ).set(1)  # Set value to 1 (or any other constant value)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching SFDC Logger Login records: %s", e)


def community_registration_error_logger_details(sf):
    """
    Monitors Apex failure for Registration (PRM and GSP) from SFDC Logger records
    where source = ('Community - Conversation Id',
                    'Community - Registration',
                    'GSP - Registration PRMP')
    and Log level is Error or Fatal
    """

    try:
        logger.info("Querying SFDC Logger Registration records...")
        query = """
		SELECT Id, Name, Source_Name__c, CreatedDate, Log_Message__c, Record_Id__c, Log_Level__c, Log_Callout_Response_Payload__c 
		FROM SFDC_Logger__c 
		WHERE Source_Name__c IN ('Community - Conversation Id', 'Community - Registration', 'GSP - Registration PRMP', 'AvalaraIdentityCreateAvataxAccount')
		AND Log_Level__c IN ('Error','Fatal') 
		AND CreatedDate = LAST_N_DAYS:7 
		ORDER BY CreatedDate DESC
        """
        results = query_records_all(sf, query)
        community_registration_error_metric.clear()

        for record in results:
            # Expose logger details as Prometheus metrics
            community_registration_error_metric.labels(
                id=record['Id'],
                name=record['Name'],
                source_name=record['Source_Name__c'],
                log_level=record['Log_Level__c'],
                log_message=record['Log_Message__c'],
                callout_response=record['Log_Callout_Response_Payload__c'],
                record_id=record['Record_Id__c'],
                created_date=record['CreatedDate']
            ).set(1)  # Set value to 1 (or any other constant value)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching SFDC Logger Registration records: %s", e)
