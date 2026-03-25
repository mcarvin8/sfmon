"""
Permission Sets & Profiles Monitoring Module

This module monitors permission set and profile technical debt including:
- Unassigned permission sets
- Permission sets with limited user assignments
- Profiles with few or no active users
- Permission sets with minimal permissions (consolidation candidates)

Environment Variables:
    - PERMSET_LIMITED_USERS_THRESHOLD: Permission sets with <= this many users are flagged (default: 10)
    - PROFILE_UNDER_USERS_THRESHOLD: Profiles with <= this many users are flagged (default: 5)

Data Sources:
    - PermissionSet, PermissionSetAssignment, PermissionSetGroupComponent objects
    - Profile object
    - User object
    - Local file reports (minimal-perm-sets.json)
"""
import json
import os

from logger import logger
from gauges import (
    unused_permissionsets,
    limited_permissionsets,
    five_or_less_profile_assignees,
    unassigned_profiles,
    minimal_permission_sets_gauge,
    minimal_permission_sets_percentage_gauge,
)
from query import query_records_all

# Thresholds for flagging permission sets and profiles
PERMSET_LIMITED_USERS_THRESHOLD = int(os.getenv("PERMSET_LIMITED_USERS_THRESHOLD", 10))
PROFILE_UNDER_USERS_THRESHOLD = int(os.getenv("PROFILE_UNDER_USERS_THRESHOLD", 5))


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
            unused_permissionsets.labels(name=record["Name"], id=record["Id"]).set(0)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching unassigned permission sets: %s", e)


def perm_sets_limited_users(sf):
    """
    Query permission sets developed by FTE assigned to limited active users.
    The threshold is configurable via PERMSET_LIMITED_USERS_THRESHOLD environment variable.
    """
    try:
        logger.info(
            "Querying permission sets assigned to %d or less active users...",
            PERMSET_LIMITED_USERS_THRESHOLD,
        )
        # SOQL; PERMSET_LIMITED_USERS_THRESHOLD is int from env (B608)
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
        """  # nosec B608
        results = query_records_all(sf, query)
        # Clear existing Prometheus gauge labels
        limited_permissionsets.clear()

        for record in results:
            limited_permissionsets.labels(name=record["Name"], id=record["Id"]).set(
                int(record["expr0"])
            )
    # pylint: disable=broad-except
    except Exception as e:
        logger.error(
            "Error fetching permission sets assigned to 10 or less active users: %s", e
        )


def profile_assignment_under5(sf):
    """
    Query all profiles where limited assignees.
    The threshold is configurable via PROFILE_UNDER_USERS_THRESHOLD environment variable.
    """
    try:
        logger.info(
            "Querying all profiles with %d or less assignees...",
            PROFILE_UNDER_USERS_THRESHOLD,
        )
        # SOQL; PROFILE_UNDER_USERS_THRESHOLD is int from env (B608)
        query = f"""
        SELECT ProfileId, Profile.Name, COUNT(Id) userCount
        FROM User
        WHERE IsActive = TRUE
        GROUP BY ProfileId, Profile.Name
        HAVING COUNT(Id) <= {PROFILE_UNDER_USERS_THRESHOLD}
        """  # nosec B608
        results = query_records_all(sf, query)
        # Clear existing Prometheus gauge labels
        five_or_less_profile_assignees.clear()

        for record in results:
            five_or_less_profile_assignees.labels(
                profileId=record["ProfileId"], profileName=record["Name"]
            ).set(int(record["userCount"]))
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
                profileId=record["Id"], profileName=record["Name"]
            ).set(0)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching profiles with no active users: %s", e)

def monitor_minimal_perm_sets(_sf):
    """
    Parse minimal permission sets report and set Prometheus gauges.
    Runs once daily to monitor tech debt from permission set analysis.

    Tracks permission sets with 5 or fewer permissions, which may be candidates
    for consolidation to reduce org complexity. Exposes two gauges:
    1. Individual minimal permission sets with permission counts
    2. Overall percentage of minimal permission sets

    Args:
        _sf: Salesforce connection (unused; scheduler passes the shared client).
    """
    try:
        logger.info("Monitoring minimal permission sets from report file...")

        # Report file is in the same directory as this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        report_file_path = os.path.join(script_dir, "minimal-perm-sets.json")

        if not os.path.exists(report_file_path):
            logger.warning(
                "Minimal permission sets report file not found at: %s", report_file_path
            )
            logger.info(
                "This file should be generated by a scheduled pipeline that retrieves metadata from production"
            )
            return

        logger.info("Found minimal permission sets report at: %s", report_file_path)

        # Clear existing Prometheus gauge labels
        minimal_permission_sets_gauge.clear()
        # Note: percentage gauge has no labels, so we don't clear it - we just set it

        # Read and parse the JSON report
        with open(report_file_path, "r", encoding="utf-8") as f:
            report_data = json.load(f)

        # Expected JSON structure:
        # {
        #   "scan_date": "2024-01-01T00:00:00Z",
        #   "total_permission_sets": 672,
        #   "threshold": 5,
        #   "minimal_permission_sets": [
        #     {
        #       "name": "Permission Set Name",
        #       "file_path": "filename",
        #       "permission_count": 3
        #     }
        #   ]
        # }

        minimal_permission_sets = report_data.get("minimal_permission_sets", [])
        total_permission_sets = report_data.get("total_permission_sets", 0)
        threshold = report_data.get("threshold", 5)
        scan_date = report_data.get("scan_date", "Unknown")

        # Set gauge values for each minimal permission set
        for perm_set in minimal_permission_sets:
            permission_set_name = perm_set.get("name", "Unknown")
            file_path = perm_set.get("file_path", "Unknown")
            permission_count = perm_set.get("permission_count", 0)

            minimal_permission_sets_gauge.labels(
                permission_set_name=permission_set_name,
                file_path=file_path,
                permission_count=str(permission_count),
            ).set(permission_count)

            logger.debug(
                "Found minimal permission set: %s (%s) - %d permissions",
                permission_set_name,
                file_path,
                permission_count,
            )

        # Calculate and set percentage gauge
        if total_permission_sets > 0:
            percentage = (len(minimal_permission_sets) / total_permission_sets) * 100
            minimal_permission_sets_percentage_gauge.set(percentage)
            logger.info("Minimal permission sets percentage: %.2f%%", percentage)

        logger.info(
            "Minimal permission sets monitoring completed. Found %d minimal permission sets (<= %d permissions) out of %d total (scan date: %s)",
            len(minimal_permission_sets),
            threshold,
            total_permission_sets,
            scan_date,
        )

    # pylint: disable=broad-except
    except json.JSONDecodeError as e:
        logger.error("Error parsing minimal permission sets JSON report: %s", e)
    except FileNotFoundError as e:
        logger.error("Minimal permission sets report file not found: %s", e)
    except Exception as e:
        logger.error("Error monitoring minimal permission sets: %s", e)
