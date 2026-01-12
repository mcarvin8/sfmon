"""
Org-Wide Sharing Settings Monitoring Module

This module monitors changes to org-wide sharing settings by querying
SetupAuditTrail records. It identifies changes to sharing defaults and
exposes them as Prometheus metrics for compliance tracking.

Functions:
    - monitor_org_wide_sharing_settings: Main monitoring function
"""
from .utils import get_user_name, categorize_user_group
from .audit_trail import query_setup_audit_trail
from logger import logger
from gauges import org_wide_sharing__setting_changes


def monitor_org_wide_sharing_settings(sf):
    '''
    Monitors changes to the org-wide sharing settings by querying the SetupAuditTrail object.
    '''
    logger.info("Getting Org-Wide Sharing Settings...")

    try:
        org_wide_sharing__setting_changes.clear()
        changes = query_setup_audit_trail(sf)

        has_sharing_changes = False
        if changes:
            for change in changes:
                if change['Section'] == 'Sharing Defaults':
                    action = change.get('Action', 'Unknown')
                    created_date = change.get('CreatedDate', 'Unknown')
                    user_id = change.get('CreatedById', 'Unknown')
                    user_name = get_user_name(sf, user_id)
                    user_group = categorize_user_group(user_name)
                    details = change.get('Display', 'Unknown')
                    org_wide_sharing__setting_changes.labels(
                        date=created_date, user=user_name, user_group=user_group,
                        action=action, display=details
                    ).set(1)
                    has_sharing_changes = True

        # Ensure metric is visible even when there are no sharing changes
        if not has_sharing_changes:
            logger.info("No changes found in Org-Wide Sharing Settings for today.")
            org_wide_sharing__setting_changes.labels(
                date='none',
                user='No Changes',
                user_group='Other',
                action='none',
                display='No org-wide sharing setting changes'
            ).set(0)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("An unexpected error occurred during monitoring Org-Wide Sharing Settings: %s", e)
