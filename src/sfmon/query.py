"""
Salesforce Query Utility Module

This module provides wrapper functions around Simple Salesforce's query functionality
with built-in pagination, timeout handling, and error management. It supports both
standard SOQL queries and Tooling API queries.

Functions:
    - query_result: Executes a SOQL or Tooling API query, returning the full response
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
from simple_salesforce.exceptions import (
    SalesforceExpiredSession,
    SalesforceMalformedRequest,
)

from . import orgs
from .constants import QUERY_TIMEOUT_SECONDS, REQUESTS_TIMEOUT_SECONDS
from .logger import logger
from .org_gauge import get_current_org
from .self_metrics import record_query_error


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
    if not response.ok:
        record_query_error()
    return response


def _run_query(sf, soql_query, execute, label):
    """Run execute(sf, soql_query) with sfmon's standard error handling.

    Re-authenticates the current org once on an expired session. Every
    failure is logged and counted with record_query_error(); returns the raw
    API response dict, or None if the query failed.
    """
    try:
        return execute(sf, soql_query)
    except SalesforceExpiredSession as e:
        logger.warning("Salesforce session expired, re-authenticating: %s", e)
        try:
            sf = _reconnect_current_org(sf)
            if sf:
                return execute(sf, soql_query)
        except Exception as retry_e:
            logger.error("%s failed after re-authentication: %s", label, retry_e)
        record_query_error()
        return None
    except requests.exceptions.Timeout:
        logger.error("%s timed out after : %s seconds.", label, QUERY_TIMEOUT_SECONDS)
        record_query_error()
        return None
    except SalesforceMalformedRequest as e:
        logger.error("Salesforce malformed request: %s", e)
        record_query_error()
        return None
    except Exception as e:
        logger.error("%s failed due to general exception: %s", label, e)
        record_query_error()
        return None


def _execute_rest(sf, soql_query):
    return sf.query_all(soql_query, timeout=QUERY_TIMEOUT_SECONDS)


def _execute_tooling(sf, soql_query):
    return sf.toolingexecute(f"query/?q={soql_query}", timeout=QUERY_TIMEOUT_SECONDS)


def query_result(sf, soql_query, tooling=False):
    """Run a SOQL query and return the full API response (records plus
    totalSize), or None if it failed. Use this instead of query_records_all
    when the caller needs totalSize, e.g. for SELECT COUNT() queries.
    """
    if tooling:
        return _run_query(sf, soql_query, _execute_tooling, "Tooling API query")
    return _run_query(sf, soql_query, _execute_rest, "Query")


def _records(result):
    return result["records"] if result and "records" in result else []


def query_records_all(sf, soql_query):
    """fetch all records from query using pagination - simple salesforce)"""
    return _records(query_result(sf, soql_query))


def tooling_query_records_all(sf, soql_query):
    """fetch all records from tooling api query using pagination - simple salesforce"""
    return _records(query_result(sf, soql_query, tooling=True))
