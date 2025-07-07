"""
    Deployment functions.
"""
from datetime import datetime

from cloudwatch_logging import logger
from gauges import (
    deployment_details_gauge, pending_time_gauge, deployment_time_gauge,
    validation_details_gauge, validation_pending_time_gauge, validation_time_gauge
)
from query import run_sf_cli_query


def get_deployment_status(sf):
    """
    Get deployment related info from the org and report metrics.
    """
    logger.info("Getting deployment status...")

    query = 'SELECT Id, Status, StartDate, CreatedBy.Name, CreatedDate, CompletedDate, CheckOnly FROM DeployRequest ORDER BY CompletedDate DESC'

    status_mapping = {
        'Succeeded': 1,
        'Failed': 0,
        'InProgress': 2,
        'Canceled': -1
    }

    try:
        result = run_sf_cli_query(query=query,
                                  alias=sf,use_tooling_api=True)
        for record in result:
            if record.get('Status') == 'InProgress':
                continue
            is_validation = record.get('CheckOnly', False)
            process_deployment_record(record, status_mapping, is_validation)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Failed to retrieve deployment status: %s", e)


def process_deployment_record(record, status_mapping, is_validation=False):
    """
    Process a single deployment record and report metrics.

    Args:
        record (dict): Deployment record from Salesforce.
        status_mapping (dict): Mapping of deployment statuses to metric values.
    """
    created_date = parse_datetime(record.get('CreatedDate'))
    start_date = parse_datetime(record.get('StartDate'))
    completed_date = parse_datetime(record.get('CompletedDate'))

    deployment_time = calculate_minutes_difference(start_date, completed_date)
    pending_time = calculate_minutes_difference(created_date, start_date)

    report_deployment_metrics(record, deployment_time, pending_time, status_mapping, is_validation)


def parse_datetime(date_str):
    """
    Parse Salesforce datetime string into a datetime object.

    Args:
        date_str (str): Datetime string.

    Returns:
        datetime or None
    """
    if not date_str:
        return None
    return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%f%z')


def calculate_minutes_difference(start, end):
    """
    Calculate the difference in minutes between two datetime objects.

    Args:
        start (datetime): Start time.
        end (datetime): End time.

    Returns:
        float: Difference in minutes, or 0.0 if inputs are None.
    """
    if start and end:
        return (end - start).total_seconds() / 60
    return 0.0


def report_deployment_metrics(record, deployment_time, pending_time, status_mapping, is_validation):
    """
    Send deployment-related metrics to CloudWatch gauges.

    Args:
        record (dict): Deployment record.
        deployment_time (float): Deployment duration in minutes.
        pending_time (float): Pending time in minutes.
        status_mapping (dict): Mapping of status strings to integer values.
    """
    deployment_id = record['Id']
    deployed_by = record['CreatedBy']['Name']
    status = record['Status']

    if is_validation:
        validation_details_gauge.labels(
            pending_time=pending_time,
            deployment_time=deployment_time,
            deployment_id=deployment_id,
            deployed_by=deployed_by,
            status=status
        ).set(status_mapping.get(status, -1))

        validation_pending_time_gauge.labels(
            deployment_id=deployment_id,
            deployed_by=deployed_by,
            status=status
        ).set(pending_time)

        validation_time_gauge.labels(
            deployment_id=deployment_id,
            deployed_by=deployed_by,
            status=status
        ).set(deployment_time)
    else:
        deployment_details_gauge.labels(
            pending_time=pending_time,
            deployment_time=deployment_time,
            deployment_id=deployment_id,
            deployed_by=deployed_by,
            status=status
        ).set(status_mapping.get(status, -1))

        pending_time_gauge.labels(
            deployment_id=deployment_id,
            deployed_by=deployed_by,
            status=status
        ).set(pending_time)

        deployment_time_gauge.labels(
            deployment_id=deployment_id,
            deployed_by=deployed_by,
            status=status
        ).set(deployment_time)
