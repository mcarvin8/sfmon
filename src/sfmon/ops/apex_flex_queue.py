"""
Apex Flex Queue Monitoring Module

This module monitors the Salesforce Apex Flex Queue for the production environment.
It queries AsyncApexJob records with 'Holding' status and exposes them as
Prometheus metrics for alerting and monitoring purposes.

Environment Variables:
    - FLEX_QUEUE_LIMIT: Max jobs the Apex Flex Queue can hold at once (default: 100).
                         This is a fixed Salesforce platform constant, not something
                         exposed via SOQL or the REST /limits endpoint -- Salesforce
                         hard-caps the flex queue at 100 holding jobs regardless of
                         org/edition, so there's no live value to query.
    - FLEX_QUEUE_ALERT_THRESHOLD_PERCENT: Usage percentage of FLEX_QUEUE_LIMIT at/above
                                           which a Slack alert triggers, if
                                           SLACK_WEBHOOK_URL is set (default: 80)

Functions:
    - monitor_apex_flex_queue: Queries and reports jobs in holding status
"""

import os

from ..logger import logger
from ..slack_notify import sync_alerts
from .gauges import apex_flex_queue
from ..query import query_records_all

FLEX_QUEUE_LIMIT = int(os.getenv("FLEX_QUEUE_LIMIT", 100))
FLEX_QUEUE_ALERT_THRESHOLD_PERCENT = float(
    os.getenv("FLEX_QUEUE_ALERT_THRESHOLD_PERCENT", 80)
)


def monitor_apex_flex_queue(sf):
    """
    Query all records in holding in the Apex Flex Queue.

    If queue depth is at/above FLEX_QUEUE_ALERT_THRESHOLD_PERCENT of
    FLEX_QUEUE_LIMIT, also passed to sync_alerts() for Slack notification
    (no-op unless SLACK_WEBHOOK_URL is set). Depth at/above FLEX_QUEUE_LIMIT
    itself (the hard cap -- new jobs get rejected) is flagged critical.
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
                    id=record["Id"], ApexClassId=record["ApexClassId"]
                ).set(1)
        else:
            # Emit a 0-valued series when no records are found
            apex_flex_queue.labels(id="none", ApexClassId="none").set(0)

        queue_depth = len(results)
        percentage = (queue_depth / FLEX_QUEUE_LIMIT) * 100
        breached = {}
        if percentage >= FLEX_QUEUE_ALERT_THRESHOLD_PERCENT:
            breached["apex_flex_queue"] = {
                "title": f"Apex Flex Queue at {queue_depth}/{FLEX_QUEUE_LIMIT} jobs",
                "message": (
                    f"{queue_depth} jobs holding in the Apex Flex Queue "
                    f"({percentage:.1f}% of the {FLEX_QUEUE_LIMIT}-job limit)."
                ),
                "severity": "critical" if queue_depth >= FLEX_QUEUE_LIMIT else "warning",
            }
        sync_alerts("apex_flex_queue", breached)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching Apex Flex Queue: %s", e)
