"""
Apex Flex Queue Monitoring Module

This module monitors the Salesforce Apex Flex Queue for the production environment.
It queries AsyncApexJob records with 'Holding' status and exposes them as
Prometheus metrics for alerting and monitoring purposes.

Functions:
    - monitor_apex_flex_queue: Queries and reports jobs in holding status
"""
from logger import logger
from gauges import apex_flex_queue
from query import query_records_all

def monitor_apex_flex_queue(sf):
    """
    Query all records in holding in the Apex Flex Queue
    """
    try:
        logger.info("Querying all records in Flex Queue")
        query = """
        SELECT Id, ApexClassId FROM AsyncApexJob WHERE Status = 'Holding'
        """
        results = query_records_all(sf, query)
        # Clear existing Prometheus gauge labels
        apex_flex_queue.clear()

        if results:
            for record in results:
                apex_flex_queue.labels(
                    id=record['Id'],
                    ApexClassId=record['ApexClassId']
                ).set(1)
        else:
            # Emit a 0-valued series when no records are found
            apex_flex_queue.labels(
                id="none",
                ApexClassId="none"
            ).set(0)    
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching Apex Flex Queue: %s", e)
