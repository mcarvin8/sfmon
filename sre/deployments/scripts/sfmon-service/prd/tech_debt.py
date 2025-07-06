"""
Functions to monitor tech debt.
"""
from cloudwatch_logging import logger
from gauges import (unused_permissionsets, five_or_less_profile_assignees,
                    unassigned_profiles, limited_permissionsets,
                    deprecated_apex_class_gauge)
from query import run_sf_cli_query

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
        results = run_sf_cli_query(query=query, alias=sf)
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
    Query permission sets developed by FTE assigned to 10 or less active users
    """
    try:
        logger.info("Querying permission sets assigned to 10 or less active users...")
        query = """
        SELECT PermissionSet.Id, PermissionSet.Name, Count(ID)
        FROM PermissionSetAssignment
        where PermissionSetId NOT IN (
            SELECT PermissionSetId
            FROM PermissionSetGroupComponent
        )
        AND PermissionSet.NamespacePrefix = NULL  
        GROUP BY PermissionSet.Id, PermissionSet.Name
        HAVING COUNT(Id) <= 10
        """
        results = run_sf_cli_query(query=query, alias=sf)
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
    Query all profiles where 5 or less assignees.
    """
    try:
        logger.info("Querying all profiles with 5 or less assignees...")
        query = """
        SELECT ProfileId, Profile.Name, COUNT(Id) userCount
        FROM User
        WHERE IsActive = TRUE
        GROUP BY ProfileId, Profile.Name
        HAVING COUNT(Id) <= 5
        """
        results = run_sf_cli_query(query=query, alias=sf)
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
        results = run_sf_cli_query(query=query, alias=sf)
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

def deprecated_apex_classes(sf):
    """
    Query all local apex classes running on deprecated API versions.
    """
    try:
        logger.info("Querying all local apex classes running on deprecated API versions...")
        query = """
        SELECT Id,Name,ApiVersion
        FROM ApexClass
        WHERE NamespacePrefix = null AND ApiVersion <= 30
        """
        results = run_sf_cli_query(query=query, alias=sf)
        # Clear existing Prometheus gauge labels
        deprecated_apex_class_gauge.clear()

        for record in results:
            deprecated_apex_class_gauge.labels(
                id=record['Id'],
                name=record['Name']
            ).set(int(record['ApiVersion']))
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching local apex classes running on deprecated API versions: %s", e)
