'''
    Org-wide sharing setting functions
'''
from cloudwatch_logging import logger
from compliance import get_user_name
from gauges import org_wide_sharing__setting_changes
from query import run_sf_cli_query


def query_setup_audit_trail(sf):
    '''
    fetch audit trail records from today's date
    '''
    soql_query = "SELECT Action, CreatedById, CreatedDate, Display, Section FROM SetupAuditTrail WHERE CreatedDate=YESTERDAY ORDER BY CreatedDate DESC"
    result = run_sf_cli_query(query=soql_query, alias=sf)

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
