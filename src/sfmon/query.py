"""
Salesforce Query Utility Module

This module provides wrapper functions around Simple Salesforce's query functionality
with built-in pagination, timeout handling, and error management. It supports both
standard SOQL queries and Tooling API queries.

Functions:
    - query_records_all: Executes standard SOQL query with automatic pagination
    - tooling_query_records_all: Executes Tooling API query with pagination

Features:
    - Automatic pagination for large result sets
    - Configurable query timeout (30 seconds default)
    - Comprehensive exception handling for network and API errors
    - Graceful failure with empty list returns
    - Detailed error logging for debugging
"""

import requests

from constants import QUERY_TIMEOUT_SECONDS
from logger import logger
from simple_salesforce.exceptions import (
    SalesforceExpiredSession,
    SalesforceMalformedRequest,
)


def query_records_all(sf, soql_query):
    """fetch all records from query using pagination - simple salesforce)"""
    try:
        result = sf.query_all(soql_query, timeout=QUERY_TIMEOUT_SECONDS)
        return result["records"] if "records" in result else []
    except SalesforceExpiredSession as e:
        logger.warning("Salesforce session expired, re-authenticating: %s", e)
        try:
            import salesforce_monitoring

            salesforce_monitoring.reauthenticate_connections()
            sf = salesforce_monitoring.sf_connection
            if sf:
                result = sf.query_all(soql_query, timeout=QUERY_TIMEOUT_SECONDS)
                return result["records"] if "records" in result else []
        except Exception as retry_e:
            logger.error("Query failed after re-authentication: %s", retry_e)
        return []
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
    """fetch all records from tooling api query using pagination - simple salesforce"""
    try:
        result = sf.toolingexecute(
            f"query/?q={soql_query}", timeout=QUERY_TIMEOUT_SECONDS
        )
        return result["records"] if "records" in result else []
    except SalesforceExpiredSession as e:
        logger.warning("Salesforce session expired, re-authenticating: %s", e)
        try:
            import salesforce_monitoring

            salesforce_monitoring.reauthenticate_connections()
            sf = salesforce_monitoring.sf_connection
            if sf:
                result = sf.toolingexecute(
                    f"query/?q={soql_query}", timeout=QUERY_TIMEOUT_SECONDS
                )
                return result["records"] if "records" in result else []
        except Exception as retry_e:
            logger.error(
                "Tooling API query failed after re-authentication: %s", retry_e
            )
        return []
    except requests.exceptions.Timeout:
        logger.error(
            "Tooling API query timed out after : %s seconds.", QUERY_TIMEOUT_SECONDS
        )
        return []
    except SalesforceMalformedRequest as e:
        logger.error("Salesforce tooling API malformed request: %s", e)
        return []
    except Exception as e:
        logger.error("Tooling API query failed due to general exception: %s", e)
        return []
