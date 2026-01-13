"""
Code Quality & API Versions Monitoring Module

This module monitors code quality technical debt including:
- Apex classes on outdated API versions
- Apex triggers on outdated API versions
- Legacy workflow rules
- PMD static analysis violations

Environment Variables:
    - DEPRECATED_API_VERSION: API versions at or below this are considered deprecated (default: 50)

Data Sources:
    - ApexClass object (via standard API)
    - ApexTrigger object (via standard API)
    - WorkflowRule (via Tooling API)
    - Local file reports (pmd-report.xml, apexruleset.xml)
"""
import os

from logger import logger
from gauges import (
    deprecated_apex_class_gauge,
    deprecated_apex_trigger_gauge,
    workflow_rules_gauge
)
from query import query_records_all, tooling_query_records_all

# API versions at or below this threshold are considered deprecated
DEPRECATED_API_VERSION = int(os.getenv('DEPRECATED_API_VERSION', 50))


def apex_classes_api_version(sf):
    """
    Query all local apex classes running on outdated API versions.
    The threshold is configurable via DEPRECATED_API_VERSION environment variable.
    """
    try:
        logger.info("Querying all local apex classes running on outdated API versions (<= %d)...", DEPRECATED_API_VERSION)
        query = f"""
        SELECT Id,Name,ApiVersion
        FROM ApexClass
        WHERE NamespacePrefix = null AND ApiVersion <= {DEPRECATED_API_VERSION}
        """
        results = query_records_all(sf, query)
        # Clear existing Prometheus gauge labels
        deprecated_apex_class_gauge.clear()

        for record in results:
            deprecated_apex_class_gauge.labels(
                id=record['Id'],
                name=record['Name']
            ).set(int(record['ApiVersion']))
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching local apex classes running on outdated API versions: %s", e)


def apex_triggers_api_version(sf):
    """
    Query all local apex triggers running on outdated API versions.
    The threshold is configurable via DEPRECATED_API_VERSION environment variable.
    """
    try:
        logger.info("Querying all local apex triggers running on outdated API versions (<= %d)...", DEPRECATED_API_VERSION)
        query = f"""
        SELECT Id,Name,ApiVersion
        FROM ApexTrigger 
        WHERE NamespacePrefix = null AND ApiVersion <= {DEPRECATED_API_VERSION}
        """
        results = query_records_all(sf, query)
        # Clear existing Prometheus gauge labels
        deprecated_apex_trigger_gauge.clear()

        for record in results:
            deprecated_apex_trigger_gauge.labels(
                id=record['Id'],
                name=record['Name']
            ).set(int(record['ApiVersion']))
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching local apex triggers running on outdated API versions: %s", e)


def workflow_rules_monitoring(sf):
    """
    Query all workflow rules using the Tooling API and check their active status.
    """
    try:
        logger.info("Querying all workflow rules using Tooling API...")
        # First query to get all workflow rule IDs
        initial_query = """
        SELECT Id, CreatedDate, NamespacePrefix
        FROM WorkflowRule
        """
        results = tooling_query_records_all(sf, initial_query)
        # Clear existing Prometheus gauge labels
        workflow_rules_gauge.clear()

        for record in results:
            workflow_id = record['Id']
            created_date = record.get('CreatedDate', 'Unknown')
            namespace_prefix = record.get('NamespacePrefix', 'None') or 'None'
            
            # Add all workflow rules to the gauge with a numeric value
            workflow_rules_gauge.labels(
                id=workflow_id,
                created_date=created_date,
                namespace_prefix=namespace_prefix
            ).set(1)
            logger.debug("Added workflow rule to gauge: %s", workflow_id)
                
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching workflow rules: %s", e)
