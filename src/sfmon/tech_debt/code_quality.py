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
import re

from logger import logger
from gauges import (
    deprecated_apex_class_gauge,
    deprecated_apex_trigger_gauge,
    workflow_rules_gauge,
    apex_character_limit_percentage_gauge,
    apex_class_length_without_comments_gauge,
    apex_trigger_length_without_comments_gauge,
)
from query import query_records_all, tooling_query_records_all

# API versions at or below this threshold are considered deprecated
DEPRECATED_API_VERSION = int(os.getenv("DEPRECATED_API_VERSION", 50))
# Salesforce Apex character limit (6M for Enterprise, Performance, Unlimited, Developer)
# Custom classes/triggers only (NamespacePrefix=null); excludes comments and @isTest classes
APEX_CHARACTER_LIMIT = int(os.getenv("APEX_CHARACTER_LIMIT", 6000000))


def apex_classes_api_version(sf):
    """
    Query all local apex classes running on outdated API versions.
    The threshold is configurable via DEPRECATED_API_VERSION environment variable.
    """
    try:
        logger.info(
            "Querying all local apex classes running on outdated API versions (<= %d)...",
            DEPRECATED_API_VERSION,
        )
        # SOQL; DEPRECATED_API_VERSION is int from env (B608)
        query = f"""
        SELECT Id,Name,ApiVersion
        FROM ApexClass
        WHERE NamespacePrefix = null AND ApiVersion <= {DEPRECATED_API_VERSION}
        """  # nosec B608
        results = query_records_all(sf, query)
        # Clear existing Prometheus gauge labels
        deprecated_apex_class_gauge.clear()

        for record in results:
            deprecated_apex_class_gauge.labels(
                id=record["Id"], name=record["Name"]
            ).set(int(record["ApiVersion"]))
    # pylint: disable=broad-except
    except Exception as e:
        logger.error(
            "Error fetching local apex classes running on outdated API versions: %s", e
        )


def apex_triggers_api_version(sf):
    """
    Query all local apex triggers running on outdated API versions.
    The threshold is configurable via DEPRECATED_API_VERSION environment variable.
    """
    try:
        logger.info(
            "Querying all local apex triggers running on outdated API versions (<= %d)...",
            DEPRECATED_API_VERSION,
        )
        # SOQL; DEPRECATED_API_VERSION is int from env (B608)
        query = f"""
        SELECT Id,Name,ApiVersion
        FROM ApexTrigger 
        WHERE NamespacePrefix = null AND ApiVersion <= {DEPRECATED_API_VERSION}
        """  # nosec B608
        results = query_records_all(sf, query)
        # Clear existing Prometheus gauge labels
        deprecated_apex_trigger_gauge.clear()

        for record in results:
            deprecated_apex_trigger_gauge.labels(
                id=record["Id"], name=record["Name"]
            ).set(int(record["ApiVersion"]))
    # pylint: disable=broad-except
    except Exception as e:
        logger.error(
            "Error fetching local apex triggers running on outdated API versions: %s", e
        )


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
            workflow_id = record["Id"]
            created_date = record.get("CreatedDate", "Unknown")
            namespace_prefix = record.get("NamespacePrefix", "None") or "None"

            # Add all workflow rules to the gauge with a numeric value
            workflow_rules_gauge.labels(
                id=workflow_id,
                created_date=created_date,
                namespace_prefix=namespace_prefix,
            ).set(1)
            logger.debug("Added workflow rule to gauge: %s", workflow_id)

    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching workflow rules: %s", e)


def _is_test_class(body):
    """
    Return True if the Apex class is annotated with @isTest at class level.
    Checks Body for @isTest before the class keyword (excluding comments).
    """
    if not body or not isinstance(body, str):
        return False
    # Remove block comments /* ... */
    body_no_block = re.sub(r"/\*.*?\*/", "", body, flags=re.DOTALL)
    # Remove line comments // ...
    body_no_comments = re.sub(r"//[^\n]*", "", body_no_block)
    # Find first "class " keyword
    class_match = re.search(r"\bclass\s+\w+", body_no_comments, re.IGNORECASE)
    if not class_match:
        return False
    # Check if @isTest appears before the class keyword
    before_class = body_no_comments[: class_match.start()]
    return bool(re.search(r"@isTest\b", before_class, re.IGNORECASE))


def apex_used_limits_monitoring(sf):
    """
    Monitor Apex Used Limits: per-class/trigger length gauges and overall limit percentage.
    Runs 2 queries (ApexClass, ApexTrigger), populates 3 gauges. Custom classes/triggers only.
    Excludes @isTest classes from the limit percentage. Runs once daily.
    """
    try:
        logger.info(
            "Querying custom Apex classes and triggers for Used Limits monitoring..."
        )
        classes_query = """
        SELECT Id, Name, LengthWithoutComments, Body
        FROM ApexClass
        WHERE NamespacePrefix = null
        ORDER BY LengthWithoutComments DESC
        """
        triggers_query = """
        SELECT Id, Name, LengthWithoutComments
        FROM ApexTrigger
        WHERE NamespacePrefix = null
        ORDER BY LengthWithoutComments DESC
        """
        classes = query_records_all(sf, classes_query)
        triggers = query_records_all(sf, triggers_query)

        apex_class_length_without_comments_gauge.clear()
        apex_trigger_length_without_comments_gauge.clear()

        total_classes = 0
        for record in classes:
            length = int(record.get("LengthWithoutComments") or 0)
            is_test = "true" if _is_test_class(record.get("Body")) else "false"
            apex_class_length_without_comments_gauge.labels(
                id=record["Id"], name=record["Name"], is_test=is_test
            ).set(length)
            if is_test == "false":
                total_classes += length

        total_triggers = 0
        for record in triggers:
            length = int(record.get("LengthWithoutComments") or 0)
            apex_trigger_length_without_comments_gauge.labels(
                id=record["Id"], name=record["Name"], is_test="false"
            ).set(length)
            total_triggers += length

        total_chars = total_classes + total_triggers
        percentage = (total_chars / APEX_CHARACTER_LIMIT) * 100
        apex_character_limit_percentage_gauge.set(round(percentage, 2))

        logger.info(
            "Apex Used Limits: %d chars (%.2f%% of %d), %d classes + %d triggers",
            total_chars,
            percentage,
            APEX_CHARACTER_LIMIT,
            len(classes),
            len(triggers),
        )
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error monitoring Apex Used Limits: %s", e)
