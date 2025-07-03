"""
Functions to monitor tech debt.
"""
from cloudwatch_logging import logger
from gauges import unused_permissionsets, five_or_less_profile_assignees
from query import run_sf_cli_query

def unassigned_permission_sets(sf):
    """
    Query permission sets developed by FTE which are not assigned to any active users.
    """
    try:
        logger.info("Querying unassigned permission sets...")
        query = """
        SELECT Name, Id 
        FROM PermissionSet 
        WHERE NamespacePrefix = '' 
        AND IsOwnedByProfile = false
        AND PermissionSet.ProfileId = null
        AND Id NOT IN (
            SELECT PermissionSetId 
            FROM PermissionSetAssignment
        )
        """
        results = run_sf_cli_query(query=query, alias=sf)
        # Clear existing Prometheus gauge labels
        unused_permissionsets.clear()

        for record in results:
            # Expose unassigned permission sets as Prometheus metrics
            unused_permissionsets.labels(
                name=record['Name'],
                id=record['Id'] 
            ).set(1)  # Mark this permission set as unassigned
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching unassigned permission sets: %s", e)

def profile_assignment_under5(sf):
    """
   Surface all profiles where 5 or less assignees
    """
    try:
        logger.info("Querying all profiles with 5 or less assignees...")
        query = """
        SELECT ProfileId, COUNT(Id) userCount
        FROM User WHERE IsActive = TRUE
        GROUP BY ProfileId
        HAVING COUNT(Id) < 5
        """
        results = run_sf_cli_query(query=query, alias=sf)
        # Clear existing Prometheus gauge labels
        five_or_less_profile_assignees.clear()

        for record in results:
            # Expose unassigned permission sets as Prometheus metrics
            five_or_less_profile_assignees.labels(
                profileId=record['ProfileId']
            ).set(1)  # Mark this permission set as unassigned
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching profiles with under 5 assignees: %s", e)
