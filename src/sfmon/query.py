"""
Salesforce Query Utility Module

This module provides wrapper functions around Simple Salesforce's query functionality
with built-in pagination, timeout handling, and error management. It supports both
standard SOQL queries and Tooling API queries.

Functions:
    - query_records_all: Executes standard SOQL query with automatic pagination
    - tooling_query_records_all: Executes Tooling API query with pagination
    - get_event_log_file: Downloads an EventLogFile's CSV, re-authenticating on 401

Features:
    - Automatic pagination for large result sets
    - Configurable query timeout (30 seconds default)
    - Comprehensive exception handling for network and API errors
    - Graceful failure with empty list returns
    - Detailed error logging for debugging
"""

import requests

from . import orgs
from .constants import QUERY_TIMEOUT_SECONDS, REQUESTS_TIMEOUT_SECONDS
from .logger import logger
from .org_gauge import get_current_org
from simple_salesforce.exceptions import (
    SalesforceExpiredSession,
    SalesforceMalformedRequest,
)


def _reconnect_current_org(sf):
    """Re-authenticate the org the current job is running against.

    Returns the new connection, or None if no connection could be made.
    Only this org is refreshed; other orgs in a fleet keep their sessions.
    """
    org_name = get_current_org()
    try:
        return orgs.reconnect(org_name, stale=sf)
    except Exception as e:
        logger.error("Failed to re-authenticate to org '%s': %s", org_name, e)
        return None


def _get_log_file(sf, log_id):
    return requests.get(
        f"{sf.base_url}/sobjects/EventLogFile/{log_id}/LogFile",
        headers={"Authorization": f"Bearer {sf.session_id}"},
        timeout=REQUESTS_TIMEOUT_SECONDS,
    )


def get_event_log_file(sf, log_id):
    """Download an EventLogFile's CSV content.

    The LogFile endpoint returns CSV, not JSON, so this uses requests with the
    connection's session token rather than simple_salesforce's restful().
    On a 401 (expired session) the current org is re-authenticated and the
    download retried once.

    Returns the requests.Response; callers keep their own status handling.
    """
    response = _get_log_file(sf, log_id)
    if response.status_code == 401:
        logger.warning(
            "Salesforce session expired downloading EventLogFile %s, re-authenticating",
            log_id,
        )
        new_sf = _reconnect_current_org(sf)
        if new_sf:
            response = _get_log_file(new_sf, log_id)
    return response


def query_records_all(sf, soql_query):
    """fetch all records from query using pagination - simple salesforce)"""
    try:
        result = sf.query_all(soql_query, timeout=QUERY_TIMEOUT_SECONDS)
        return result["records"] if "records" in result else []
    except SalesforceExpiredSession as e:
        logger.warning("Salesforce session expired, re-authenticating: %s", e)
        try:
            sf = _reconnect_current_org(sf)
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
            sf = _reconnect_current_org(sf)
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
