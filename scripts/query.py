'''
    Runs a query with simple salesforce with pagination enabled.
'''
import requests

from constants import QUERY_TIMEOUT_SECONDS
from cloudwatch_logging import logger
from simple_salesforce.exceptions import SalesforceMalformedRequest

def query_records_all(sf, soql_query):
    '''fetch all records from query using pagination - simple salesforce)'''
    try:
        result = sf.query_all(soql_query, timeout=QUERY_TIMEOUT_SECONDS)
        return result['records'] if 'records' in result else []
    except requests.exceptions.Timeout:
        logger.error("Query timed out after : %s seconds.", QUERY_TIMEOUT_SECONDS)
        return []
    except SalesforceMalformedRequest as e:
        logger.error("Salesforce malformed request: %s", e)
        return []
    except Exception as e:
        logger.error("Query failed due to general exception: %s", e)
        return []

def tooling_query_records_all(sf, soql_query):
    '''fetch all records from tooling api query using pagination - simple salesforce'''
    try:
        result = sf.toolingexecute(f'query/?q={soql_query}', timeout=QUERY_TIMEOUT_SECONDS)
        return result['records'] if 'records' in result else []
    except requests.exceptions.Timeout:
        logger.error("Tooling API query timed out after : %s seconds.", QUERY_TIMEOUT_SECONDS)
        return []
    except SalesforceMalformedRequest as e:
        logger.error("Salesforce tooling API malformed request: %s", e)
        return []
    except Exception as e:
        logger.error("Tooling API query failed due to general exception: %s", e)
        return []
