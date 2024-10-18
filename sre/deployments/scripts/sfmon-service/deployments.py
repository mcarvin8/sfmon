"""
    Deployment functions.
"""
from datetime import datetime

from cloudwatch_logging import logger
from gauges import deployment_details_gauge, pending_time_gauge, deployment_time_gauge


def get_deployment_status(sf):
    """
    Get deployment related info from the org.
    """
    logger.info("Getting deployment status...")

    query = """SELECT Id, Status, StartDate, CreatedBy.Name, CreatedDate, CompletedDate, CheckOnly FROM DeployRequest WHERE CheckOnly = false ORDER BY CompletedDate DESC"""

    status_mapping = {'Succeeded': 1,'Failed': 0,'InProgress': 2, 'Canceled': -1}

    result = sf.toolingexecute(f'query/?q={query}')

    if result['records']:
        for record in result['records']:
            # Skip "InProgress" deployments
            if record['Status'] == 'InProgress':
                continue
            created_date = datetime.strptime(record['CreatedDate'], '%Y-%m-%dT%H:%M:%S.%f%z') if record['CreatedDate'] else None
            start_date = datetime.strptime(record['StartDate'], '%Y-%m-%dT%H:%M:%S.%f%z') if record['StartDate'] else None
            completed_date = datetime.strptime(record['CompletedDate'], '%Y-%m-%dT%H:%M:%S.%f%z') if record['CompletedDate'] else None

            # Calculate deployment_time and pending_time, or default to zero
            deployment_time = (completed_date - start_date).total_seconds()/60 if start_date and completed_date else 0.0
            pending_time = (start_date - created_date).total_seconds()/60 if created_date and start_date else 0.0

            deployment_details_gauge.labels(pending_time=pending_time, deployment_time=deployment_time, deployment_id=record['Id'],
                                            deployed_by=record['CreatedBy']['Name'], status=record['Status']).set(status_mapping[record['Status']])
            pending_time_gauge.labels(deployment_id=record['Id'], deployed_by=record['CreatedBy']['Name'], status=record['Status']).set(pending_time)
            deployment_time_gauge.labels(deployment_id=record['Id'], deployed_by=record['CreatedBy']['Name'], status=record['Status']).set(deployment_time)
