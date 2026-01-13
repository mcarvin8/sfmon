"""
Permission Sets & Profiles Monitoring Module

This module monitors permission set and profile technical debt including:
- Unassigned permission sets
- Permission sets with limited user assignments
- Profiles with few or no active users

Environment Variables:
    - PERMSET_LIMITED_USERS_THRESHOLD: Permission sets with <= this many users are flagged (default: 10)
    - PROFILE_UNDER_USERS_THRESHOLD: Profiles with <= this many users are flagged (default: 5)

Data Sources:
    - PermissionSet, PermissionSetAssignment, PermissionSetGroupComponent objects
    - Profile object
    - User object
"""
import os

from logger import logger
from gauges import (
    unused_permissionsets,
    limited_permissionsets,
    five_or_less_profile_assignees,
    unassigned_profiles
)
from query import query_records_all

# Thresholds for flagging permission sets and profiles
PERMSET_LIMITED_USERS_THRESHOLD = int(os.getenv('PERMSET_LIMITED_USERS_THRESHOLD', 10))
PROFILE_UNDER_USERS_THRESHOLD = int(os.getenv('PROFILE_UNDER_USERS_THRESHOLD', 5))


def unassigned_permission_sets(sf):
    """
    Query permission sets developed by FTE which are not assigned to any active users.
    """
    try:
        logger.info("Querying unassigned permission sets...")
        query = """
        SELECT Id, Name
        FROM PermissionSet
        WHERE Id NOT IN (
            SELECT PermissionSetId
            FROM PermissionSetAssignment
        )
        AND Id NOT IN (
            SELECT PermissionSetId
            FROM PermissionSetGroupComponent
        )
        AND NamespacePrefix = NULL
        AND IsOwnedByProfile = FALSE

        """
        results = query_records_all(sf, query)
        # Clear existing Prometheus gauge labels
        unused_permissionsets.clear()

        for record in results:
            unused_permissionsets.labels(
                name=record['Name'],
                id=record['Id']
            ).set(0)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching unassigned permission sets: %s", e)


def perm_sets_limited_users(sf):
    """
    Query permission sets developed by FTE assigned to limited active users.
    The threshold is configurable via PERMSET_LIMITED_USERS_THRESHOLD environment variable.
    """
    try:
        logger.info("Querying permission sets assigned to %d or less active users...", PERMSET_LIMITED_USERS_THRESHOLD)
        query = f"""
        SELECT PermissionSet.Id, PermissionSet.Name, Count(ID)
        FROM PermissionSetAssignment
        where PermissionSetId NOT IN (
            SELECT PermissionSetId
            FROM PermissionSetGroupComponent
        )
        AND PermissionSet.NamespacePrefix = NULL  
        GROUP BY PermissionSet.Id, PermissionSet.Name
        HAVING COUNT(Id) <= {PERMSET_LIMITED_USERS_THRESHOLD}
        """
        results = query_records_all(sf, query)
        # Clear existing Prometheus gauge labels
        limited_permissionsets.clear()

        for record in results:
            limited_permissionsets.labels(
                name=record['Name'],
                id=record['Id']
            ).set(int(record['expr0']))
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching permission sets assigned to 10 or less active users: %s", e)


def profile_assignment_under5(sf):
    """
    Query all profiles where limited assignees.
    The threshold is configurable via PROFILE_UNDER_USERS_THRESHOLD environment variable.
    """
    try:
        logger.info("Querying all profiles with %d or less assignees...", PROFILE_UNDER_USERS_THRESHOLD)
        query = f"""
        SELECT ProfileId, Profile.Name, COUNT(Id) userCount
        FROM User
        WHERE IsActive = TRUE
        GROUP BY ProfileId, Profile.Name
        HAVING COUNT(Id) <= {PROFILE_UNDER_USERS_THRESHOLD}
        """
        results = query_records_all(sf, query)
        # Clear existing Prometheus gauge labels
        five_or_less_profile_assignees.clear()

        for record in results:
            five_or_less_profile_assignees.labels(
                profileId=record['ProfileId'],
                profileName=record['Name']
            ).set(int(record['userCount']))
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching profiles with under 5 assignees: %s", e)


def profile_no_active_users(sf):
    """
    Query all profiles with no active users.
    """
    try:
        logger.info("Querying all profiles with no active users...")
        query = """
        SELECT Name, Id
        FROM Profile
        WHERE Id NOT IN (
        SELECT ProfileId FROM User WHERE IsActive = TRUE
        )
        """
        results = query_records_all(sf, query)
        # Clear existing Prometheus gauge labels
        unassigned_profiles.clear()

        for record in results:
            unassigned_profiles.labels(
                profileId=record['Id'],
                profileName=record['Name']
            ).set(0)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching profiles with no active users: %s", e)
