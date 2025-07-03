"""
    Compliance functions.
"""
from datetime import datetime, timedelta
import re

import pytz

from cloudwatch_logging import logger
from gauges import (dev_email_deliverability_change_gauge,
                    fullqa_email_deliverability_change_gauge,
                    fullqab_email_deliverability_change_gauge,
                    valid_contact_detail_gauge)
from query import run_sf_cli_query

def extract_record_data(record):
    """Extract and normalize record data."""
    return {
        'action': record.get('Action', 'Unknown'),
        'section': record.get('Section', 'Unknown'),
        'user': (record.get('CreatedBy', {}).get('Name', 'Unknown') 
                if isinstance(record.get('CreatedBy'), dict) else 'Unknown'),
        'created_date': record.get('CreatedDate', 'Unknown'),
        'display': record.get('Display', 'Unknown'),
        'delegate_user': record.get('DelegateUser', 'Unknown')
    }


def expose_record_metric(gauge, record_data):
    """Expose the record data as a metric."""
    gauge.labels(**record_data).set(1)


def get_time_threshold(minutes):
    '''Returns a formatted string of the time threshold
    for the last specified number of minutes in PST timezone.'''
    pst_timezone = pytz.timezone('US/Pacific')
    current_time = datetime.now(pst_timezone)
    time_threshold = current_time - timedelta(minutes=minutes)

    return time_threshold.strftime("%Y-%m-%dT%H:%M:%S%z")


def process_env_records(sf_alias, email_deliverability_change_query, gauge, environment):
    """Process records for a specific Salesforce environment."""
    records = run_sf_cli_query(query=email_deliverability_change_query, alias=sf_alias)

    if records:
        for record in records:
            display_value = record.get('Display', '')
            # Filter records based on specific display values
            # if display_value.strip().lower() in [
            #     "changed access to send email level from no access to all email".lower(),
            #     "changed access to send email level from no access to system email only".lower()
            # ]:
            if re.match(r"Changed Access to Send Email level from No access to (All email|System email only)", display_value):
                record_data = extract_record_data(record)
                expose_record_metric(gauge, record_data)
            else:
                logger.info("Skipping record in %s due to unmatched display value: %s",
                            environment, display_value)
    else:
        logger.info("No email deliverability change found in %s.", environment)
        gauge.labels(
            action='N/A',
            section='N/A',
            user='N/A',
            created_date='N/A',
            display='N/A',
            delegate_user='N/A'
        ).set(0)


def track_email_deliverability_change(dev_alias, fqa_alias, fqab_alias, minutes):
    '''
    monitor email deliverability change
    '''
    logger.info("Track Email Deliverability Change...")

    time_threshold_str = get_time_threshold(minutes)

    try:
        dev_email_deliverability_change_gauge.clear()
        fullqa_email_deliverability_change_gauge.clear()
        fullqab_email_deliverability_change_gauge.clear()

        email_deliverability_change_query = (
                f"SELECT Action, Section, CreatedById, CreatedBy.Name, CreatedDate, Display, DelegateUser "
                f"FROM SetupAuditTrail WHERE Action='sendEmailAccessControl' AND CreatedDate > {time_threshold_str} "
                f"ORDER BY CreatedDate DESC"
            )

        # Process email deliverability changes
        process_env_records(dev_alias,
                            email_deliverability_change_query,
                            dev_email_deliverability_change_gauge,
                            "Dev")
        process_env_records(fqa_alias,
                            email_deliverability_change_query,
                            fullqa_email_deliverability_change_gauge,
                            "FullQA")
        process_env_records(fqab_alias,
                            email_deliverability_change_query,
                            fullqab_email_deliverability_change_gauge,
                            "FullQAB")

    # pylint: disable=broad-except
    except Exception as e:
        logger.error("An error occurred in track_email_deliverability_change : %s", e)


def track_contacts_with_valid_emails(fqa_alias, fqab_alias, dev_alias):
    '''
    Monitor contacts with valid emails in sandboxes.
    '''
    logger.info("Track Contacts with Valid Emails in Sandboxes...")
    try:
        def fetch_valid_contacts(alias):
            query = "SELECT Id, Email FROM Contact WHERE Email != null AND (NOT Email LIKE '%.invalid%') AND Account.Is_Test_Account__c=false AND Is_Test_Contact_Record__c=false LIMIT 1000"
            return run_sf_cli_query(alias, query)

        # Step 1: Run queries
        fullqa_contacts = fetch_valid_contacts(fqa_alias)
        fullqab_contacts = fetch_valid_contacts(fqab_alias)
        dev_contacts = fetch_valid_contacts(dev_alias)

        # Step 2: Clear gauge only after successful queries
        valid_contact_detail_gauge.clear()

        # Step 3: Set gauges from stored results
        for record in fullqa_contacts:
            valid_contact_detail_gauge.labels(
                org="FullQA",
                contact_id=record["Id"],
                email=record["Email"]
            ).set(1)

        for record in fullqab_contacts:
            valid_contact_detail_gauge.labels(
                org="FullQAB",
                contact_id=record["Id"],
                email=record["Email"]
            ).set(1)

        for record in dev_contacts:
            valid_contact_detail_gauge.labels(
                org="Dev",
                contact_id=record["Id"],
                email=record["Email"]
            ).set(1)

        logger.info("Valid contacts: FullQA=%s, FullQAB=%s, Dev=%s", len(fullqa_contacts), len(fullqab_contacts), len(dev_contacts))

    # pylint: disable=broad-except
    except Exception as e:
        logger.error("An error occurred in track_contacts_with_valid_emails : %s", e)
