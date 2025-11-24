"""
Salesforce Query Utility Module

This module provides wrapper functions around Simple Salesforce's query functionality
with built-in pagination, timeout handling, and error management. It supports both
standard SOQL queries and Tooling API queries for production monitoring.

Functions:
    - query_records_all: Executes standard SOQL query with automatic pagination
    - tooling_query_records_all: Executes Tooling API query with pagination

Features:
    - Automatic pagination for large result sets
    - Configurable query timeout via QUERY_TIMEOUT_SECONDS environment variable (default: 30 seconds)
    - Comprehensive exception handling for network and API errors
    - Graceful failure with empty list returns
    - Detailed error logging for debugging

Tooling API Use Cases:
    - DeployRequest monitoring
    - ApexClass and ApexTrigger metadata queries
    - DebugLevel and TraceFlag management
    - Metadata API operation tracking

Standard API Use Cases:
    - All sobject record queries
    - SetupAuditTrail monitoring
    - User and license queries
    - Custom object queries
"""
import requests

from constants import QUERY_TIMEOUT_SECONDS
from logger import logger
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
