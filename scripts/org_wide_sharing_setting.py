"""
Organization-Wide Sharing Settings Monitoring Module

This module monitors changes to Salesforce organization-wide default (OWD) sharing
settings by analyzing SetupAuditTrail records. OWD changes can significantly impact
data visibility and security, so tracking these modifications is critical for
compliance and security auditing.

Monitored Changes:
    - Sharing model changes (Private, Public Read Only, Public Read/Write)
    - Object-level OWD modifications
    - Manual sharing rule changes
    - Territory-based sharing adjustments

Functions:
    - query_setup_audit_trail: Fetches yesterday's audit trail records
    - monitor_org_wide_sharing_settings: Filters and processes sharing-related changes

Alert Triggers:
    - Section = 'Sharing Defaults'
    - Any action modifying object sharing models
    - Changes to grant access using hierarchies
    - Modifications to manual sharing settings

Metrics Exposed:
    - Timestamp of change
    - User who made the change
    - Action performed (e.g., 'changedObjectSharing')
    - Details of the change from Display field

Use Cases:
    - Security compliance auditing
    - Detecting unauthorized sharing model changes
    - Tracking data access expansion
    - Correlating sharing changes with security incidents
"""
from logger import logger
from compliance import get_user_name
from gauges import org_wide_sharing__setting_changes
from query import query_records_all


def query_setup_audit_trail(sf):
    '''
    fetch audit trail records from today's date
    '''
    soql_query = "SELECT Action, CreatedById, CreatedDate, Display, Section FROM SetupAuditTrail WHERE CreatedDate=YESTERDAY ORDER BY CreatedDate DESC"
    result = query_records_all(sf, soql_query)

    return result

def monitor_org_wide_sharing_settings(sf):
    '''
    monitors changes to the org-wide sharing settings by querying the SetupAuditTrail object
    '''

    logger.info("Getting Org-Wide Sharing Settings...")

    try:
        org_wide_sharing__setting_changes.clear()
        changes = query_setup_audit_trail(sf)

        if not changes:
            logger.info("No changes found in Org-Wide Sharing Settings for today.")
            return


        for change in changes:
            if change['Section'] == 'Sharing Defaults':
                action = change.get('Action', 'Unknown')
                created_date = change.get('CreatedDate', 'Unknown')
                user_id = change.get('CreatedById', 'Unknown')
                user_name = get_user_name(sf, user_id)
                details = change.get('Display', 'Unknown')
                org_wide_sharing__setting_changes.labels(date=created_date, user=user_name, action=action, display=details).set(1)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("An unexpected error occurred during monitoring Org-Wide Sharing Settings: %s", e)
