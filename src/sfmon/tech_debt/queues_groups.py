"""
Queue & Group Management Monitoring Module

This module monitors queue and group technical debt including:
- Queue distribution across objects
- Queues without assigned members
- Case queues with no open cases
- Public groups without members

Data Sources:
    - Group object (Type='Queue' and Type='Regular')
    - QueueSobject object
    - GroupMember object
    - Case object
"""
from logger import logger
from gauges import (
    total_queues_per_object_gauge,
    queues_with_no_members_gauge,
    queues_with_zero_open_cases_gauge,
    public_groups_with_no_members_gauge,
)
from query import query_records_all


def total_queues_per_object(sf):
    """
    Query total queues per Salesforce object to identify queue distribution.
    """
    try:
        logger.info("Querying total queues per object...")
        query = """
        SELECT SobjectType, COUNT_DISTINCT(QueueId)
        FROM QueueSobject
        GROUP BY SobjectType
        ORDER BY COUNT_DISTINCT(QueueId) DESC
        """
        results = query_records_all(sf, query)
        
        # Clear existing Prometheus gauge labels
        total_queues_per_object_gauge.clear()

        for record in results:
            total_queues_per_object_gauge.labels(
                sobject_type=record['SobjectType']
            ).set(int(record['expr0']))
            
        logger.info("Found queues for %d different object types", len(results))
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching total queues per object: %s", e)


def queues_with_no_members(sf):
    """
    Query queues that have no members assigned to them.
    """
    try:
        logger.info("Querying queues with no members...")
        query = """
        SELECT Id, Name
        FROM Group
        WHERE Type = 'Queue'
        AND Id NOT IN (SELECT GroupID FROM GroupMember)
        """
        results = query_records_all(sf, query)
        
        # Clear existing Prometheus gauge labels
        queues_with_no_members_gauge.clear()

        for record in results:
            queues_with_no_members_gauge.labels(
                queue_id=record['Id'],
                queue_name=record['Name']
            ).set(1)
            
        logger.info("Found %d queues with no members", len(results))
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching queues with no members: %s", e)


def queues_with_zero_open_cases(sf):
    """
    Query queues that can own Cases but have zero open Cases.
    """
    try:
        logger.info("Querying queues with zero open cases...")
        query = """
        SELECT Id, Name
        FROM Group
        WHERE Type = 'Queue'
        AND Id IN (
          SELECT QueueId FROM QueueSobject WHERE SobjectType = 'Case'
        )
        AND Id NOT IN (
          SELECT OwnerId FROM Case WHERE IsClosed = false
        )
        """
        results = query_records_all(sf, query)
        
        # Clear existing Prometheus gauge labels
        queues_with_zero_open_cases_gauge.clear()

        for record in results:
            queues_with_zero_open_cases_gauge.labels(
                queue_id=record['Id'],
                queue_name=record['Name']
            ).set(1)
            
        logger.info("Found %d queues with zero open cases", len(results))
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching queues with zero open cases: %s", e)


def public_groups_with_no_members(sf):
    """
    Query dormant Public Groups with no members.
    """
    try:
        logger.info("Querying public groups with no members...")
        query = """
        SELECT Id, Name
        FROM Group
        WHERE Type = 'Regular'
        AND Id NOT IN (SELECT GroupId FROM GroupMember)
        ORDER BY Name
        """
        results = query_records_all(sf, query)
        
        # Clear existing Prometheus gauge labels
        public_groups_with_no_members_gauge.clear()

        for record in results:
            public_groups_with_no_members_gauge.labels(
                group_id=record['Id'],
                group_name=record['Name']
            ).set(1)
            
        logger.info("Found %d public groups with no members", len(results))
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching public groups with no members: %s", e)

