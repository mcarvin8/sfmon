"""
    Overall Org level functions.
"""
import requests

from cloudwatch_logging import logger
from constants import REQUESTS_TIMEOUT_SECONDS
from gauges import ( incident_gauge,
                    maintenance_gauge)
from query import run_sf_cli_query


def fetch_pod(instance):
    """
    Fetch the Salesforce pod for a given instance.
    """
    result = run_sf_cli_query(query="Select FIELDS(ALL) From Organization LIMIT 1",
                              alias=instance)
    return result[0]['InstanceName']


def get_salesforce_instance(sf_fqa, sf_fqab, sf_dev):
    """
    Get instance info for the org.
    """
    logger.info("Getting Salesforce instance info...")
    pod_map = {
        "FullQA": fetch_pod(sf_fqa),
        "FullQAB": fetch_pod(sf_fqab),
        "Dev": fetch_pod(sf_dev)
    }
    incident_gauge.clear()
    for org in ("Dev", "FullQA", "FullQAB"):
        try:
            pod = pod_map.get(org)
            get_salesforce_incidents(org, pod)
        except requests.RequestException as e:
            logger.error("Error getting Salesforce instance status: %s", e)
        # pylint: disable=broad-except
        except Exception as e:
            logger.error("Error getting pod or incidents: %s", e)

    get_salesforce_maintenances(pod_map)


def get_salesforce_incidents(org, instancepod):
    """
    Get all open incidents against the org.
    """
    try:
        response = requests.get("https://api.status.salesforce.com/v1/incidents/active",
                                timeout=REQUESTS_TIMEOUT_SECONDS)
        response.raise_for_status()
        incidents = response.json()
        incident_cnt = 0
        no_msg = 'No message'

        for element in incidents:
            try:
                incident_events = element.get('IncidentEvents', [])
                if incident_events:
                    latest_message = incident_events[0].get('message', no_msg)
                    original_message = incident_events[-1].get('message', no_msg)
                else:
                    latest_message = no_msg
                    original_message = no_msg

                # Access the IncidentImpacts to get the severity
                severity = element['IncidentImpacts'][0].get('severity', 'unknown')
                pods = str(element['instanceKeys']).replace("'", "").replace("[", "").replace("]", "")

                if instancepod in pods:
                    incident_gauge.labels(environment=org,
                                          pod=instancepod,
                                          severity=severity,
                                          message=latest_message,
                                          original_message=original_message
                                          ).set(1)
                    incident_cnt += 1
            except (KeyError, IndexError) as e:
                logger.warning("Error processing incident element: %s", e)

        # If no incidents were counted, ensure the gauge is set to 0 with severity 'ok'
        if incident_cnt == 0:
            incident_gauge.labels(environment=org,
                                  pod=instancepod,
                                  severity='ok',
                                  message=None,
                                  original_message=None
                                  ).set(0)

    except requests.RequestException as e:
        logger.error("Error fetching incidents: %s", e)
        # Clear the specific gauge only in case of an error
        incident_gauge.labels(environment=org,
                              pod=instancepod,
                              severity='ok',
                              message=None,
                              original_message=None
                              ).set(0)


def get_salesforce_maintenances(pod_map):
    """
    Get all scheduled maintenance details against the org.
    """
    try:
        response = requests.get("https://api.status.salesforce.com/v1/maintenances",
                                timeout=REQUESTS_TIMEOUT_SECONDS)
        response.raise_for_status()
        maintenance_data = response.json()

        pod_map_reversed = {v: k for k, v in pod_map.items()}
        maintenance_gauge.clear()

        for maintenance in maintenance_data:
            instance_keys = maintenance.get('instanceKeys', [])

            for pod in instance_keys:
                if pod in pod_map_reversed:
                    status = maintenance['message'].get('eventStatus', 'unknown')
                    if str(status).lower() in ("scheduled", "in progress"):
                        pod_name = pod_map_reversed[pod]
                        maintenance_id = maintenance['id']
                        planned_start_time = maintenance.get('plannedStartTime', 'unknown')
                        planned_end_time = maintenance.get('plannedEndTime', 'unknown')
                        maintenance_gauge.labels(environment=pod_name,
                                                        maintenance_id=maintenance_id,
                                                        status=status,
                                                        planned_start_time=planned_start_time,
                                                        planned_end_time=planned_end_time).set(1)

    except requests.RequestException as e:
        logger.error("Error fetching incidents: %s", e)
