'''
    Apex Flex Queue Reporting
'''
from cloudwatch_logging import logger
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

        for record in results:
            apex_flex_queue.labels(
                id=record['Id'],
                ApexClassId=record['ApexClassId']
            ).set(1)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching Apex Flex Queue: %s", e)
