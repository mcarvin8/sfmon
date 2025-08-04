"""
    Overall Org level functions.
"""
import requests

from cloudwatch_logging import logger
from constants import REQUESTS_TIMEOUT_SECONDS
from gauges import (api_usage_gauge, api_usage_percentage_gauge,
                    incident_gauge, total_permissionset_licenses_gauge,
                    total_usage_based_entitlements_licenses_gauge,
                    total_user_licenses_gauge,
                    used_permissionset_licenses_gauge, used_usage_based_entitlements_licenses_gauge,
                    used_user_licenses_gauge, percent_permissionset_used_gauge,
                    percent_usage_based_entitlements_used_gauge, percent_user_licenses_used_gauge,
                    maintenance_gauge)
from limits import salesforce_limits_descriptions
from query import query_records_all

def monitor_salesforce_limits(sf):
    """
    Monitor all Salesforce limits.
    """
    try:
        logger.info("Getting Salesforce API limits...")
        limits = dict(sf.limits())
        for limit_name, limit_data in limits.items():
            max_limit = limit_data['Max']
            remaining = limit_data['Remaining']
            used = max_limit - remaining

            if max_limit != 0:
                usage_percentage = (used * 100) / max_limit

                api_usage_gauge.labels(limit_name=limit_name).set(used)
                api_usage_percentage_gauge.labels(limit_name=limit_name, limit_description=salesforce_limits_descriptions.get(limit_name, 'Description not available'), limit_utilized=used, max_limit=max_limit).set(usage_percentage)
    except Exception as e:
        logger.error("Error getting limits: %s", e)

def get_salesforce_licenses(sf):
    """
    Get all license data.
    """
    logger.info("Getting Salesforce licenses...")
    total_user_licenses_gauge.clear()
    used_user_licenses_gauge.clear()
    percent_user_licenses_used_gauge.clear()
    percent_permissionset_used_gauge.clear()
    total_permissionset_licenses_gauge.clear()
    used_permissionset_licenses_gauge.clear()
    total_usage_based_entitlements_licenses_gauge.clear()
    used_usage_based_entitlements_licenses_gauge.clear()
    percent_usage_based_entitlements_used_gauge.clear()

    result_user_license = query_records_all(sf, "SELECT Name, Status, UsedLicenses, TotalLicenses FROM UserLicense")
    for entry in result_user_license:
        status = dict(entry)['Status']
        license_name = entry['Name']
        total_licenses = dict(entry)['TotalLicenses']
        used_licenses = dict(entry)['UsedLicenses']

        total_user_licenses_gauge.labels(license_name=license_name,
                                         status=status).set(total_licenses)
        used_user_licenses_gauge.labels(license_name=license_name, status=status).set(used_licenses)

        if total_licenses != 0:
            percent_used = (used_licenses / total_licenses) * 100
            percent_user_licenses_used_gauge.labels(license_name=license_name, status=status, used_licenses=used_licenses, total_licenses=total_licenses).set(percent_used)

    result_perm_set_license = query_records_all(sf, "SELECT MasterLabel, Status, ExpirationDate, TotalLicenses, UsedLicenses FROM PermissionSetLicense")
    for entry in result_perm_set_license:
        status = dict(entry)['Status']
        license_name = entry['MasterLabel']
        total_licenses = dict(entry)['TotalLicenses']
        used_licenses = dict(entry)['UsedLicenses']
        expiration_date = dict(entry)['ExpirationDate']

        total_permissionset_licenses_gauge.labels(license_name=license_name, status=status).set(total_licenses)
        used_permissionset_licenses_gauge.labels(license_name=license_name, status=status).set(used_licenses)

        if total_licenses != 0:
            percent_used = (used_licenses / total_licenses) * 100
            percent_permissionset_used_gauge.labels(license_name=license_name, status=status, expiration_date=expiration_date, used_licenses=used_licenses, total_licenses=total_licenses).set(percent_used)

    result_usage_based_entitlements = query_records_all(sf, "SELECT MasterLabel, AmountUsed, CurrentAmountAllowed, EndDate FROM TenantUsageEntitlement")
    for entry in result_usage_based_entitlements:
        license_name = dict(entry)['MasterLabel']
        total_licenses = dict(entry)['CurrentAmountAllowed']
        used_licenses = dict(entry)['AmountUsed']
        expiration_date = dict(entry)['EndDate']

        total_usage_based_entitlements_licenses_gauge.labels(license_name=license_name).set(total_licenses)
        if used_licenses:
            used_usage_based_entitlements_licenses_gauge.labels(license_name=license_name).set(used_licenses)

        if total_licenses != 0 and used_licenses is not None:
            percent_used = (used_licenses / total_licenses) * 100
            percent_usage_based_entitlements_used_gauge.labels(license_name=license_name, expiration_date=expiration_date, used_licenses=used_licenses, total_licenses=total_licenses).set(percent_used)


def fetch_pod(instance):
    """
    Fetch the Salesforce pod for a given instance.
    """
    result = query_records_all(instance, "Select FIELDS(ALL) From Organization LIMIT 1")
    return result[0]['InstanceName']


def get_salesforce_instance(sf):
    """
    Get instance info.
    """
    logger.info("Getting Salesforce instance info for Production...")
    try:
        pod = fetch_pod(sf)
        incident_gauge.clear()
        get_salesforce_incidents("Production", pod)
        get_salesforce_maintenances({"Production": pod})
    except requests.RequestException as e:
        logger.error("Error getting Salesforce instance status: %s", e)
    except Exception as e:
        logger.error("Error getting pod or incidents: %s", e)


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
    Get all scheduled maintenance details for the Production org only.
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
        logger.error("Error fetching maintenance data: %s", e)
