"""
    Overall Org level functions.
"""
from datetime import datetime
import requests

from simple_salesforce import SalesforceMalformedRequest

from cloudwatch_logging import logger
from constants import REQUESTS_TIMEOUT_SECONDS
import gauges
from limits import salesforce_limits_descriptions

def monitor_salesforce_limits(limits):
    """
    Monitor all Salesforce limits.
    """
    gauges.api_usage_gauge.clear()
    gauges.api_usage_percentage_gauge.clear()
    for limit_name, limit_data in limits.items():
        max_limit = limit_data['Max']
        remaining = limit_data['Remaining']
        used = max_limit - remaining

        if max_limit != 0:
            usage_percentage = (used * 100) / max_limit

            gauges.api_usage_gauge.labels(limit_name=limit_name).set(used)
            gauges.api_usage_percentage_gauge.labels(limit_name=limit_name, limit_description=salesforce_limits_descriptions.get(limit_name, 'Description not available'), limit_utilized=used, max_limit=max_limit).set(usage_percentage)

            if usage_percentage >= 90:
                logger.warning('API usage for %s has exceeded %s percent of the total limit.',
                                limit_name, usage_percentage)


def get_salesforce_licenses(sf):
    """
    Get all license data.
    """
    logger.info("Getting Salesforce licenses...")

    result_user_license = sf.query("SELECT Name, Status, UsedLicenses, TotalLicenses FROM UserLicense")
    for entry in result_user_license['records']:
        status = dict(entry)['Status']
        license_name = entry['Name']
        total_licenses = dict(entry)['TotalLicenses']
        used_licenses = dict(entry)['UsedLicenses']

        gauges.total_user_licenses_gauge.labels(license_name=license_name, status=status).set(total_licenses)
        gauges.used_user_licenses_gauge.labels(license_name=license_name, status=status).set(used_licenses)

        if total_licenses != 0:
            percent_used = (used_licenses / total_licenses) * 100
            gauges.percent_user_licenses_used_gauge.labels(license_name=license_name, status=status, used_licenses=used_licenses, total_licenses=total_licenses).set(percent_used)

            if percent_used >= 90:
                logger.warning('License usage for %s has exceeded %s percent of the total limit.',
                                license_name, percent_used)

    result_perm_set_license = sf.query("SELECT MasterLabel, Status, ExpirationDate, TotalLicenses, UsedLicenses FROM PermissionSetLicense")
    for entry in result_perm_set_license['records']:
        status = dict(entry)['Status']
        license_name = entry['MasterLabel']
        total_licenses = dict(entry)['TotalLicenses']
        used_licenses = dict(entry)['UsedLicenses']
        expiration_date = dict(entry)['ExpirationDate']

        gauges.total_permissionset_licenses_gauge.labels(license_name=license_name, status=status).set(total_licenses)
        gauges.used_permissionset_licenses_gauge.labels(license_name=license_name, status=status).set(used_licenses)

        if total_licenses != 0:
            percent_used = (used_licenses / total_licenses) * 100
            gauges.percent_permissionset_used_gauge.labels(license_name=license_name, status=status, expiration_date=expiration_date, used_licenses=used_licenses, total_licenses=total_licenses).set(percent_used)

            if percent_used >= 90:
                logger.warning('License usage for %s has exceeded %s percent of the total limit.', license_name, percent_used)

        if expiration_date:
            expiration_date = datetime.strptime(expiration_date, '%Y-%m-%d')
            days_until_expiration = (expiration_date - datetime.now()).days

            if days_until_expiration < 30 and status != 'Disabled':
                logger.warning("License %s with status %s is expiring in less than 30 days: %s days left.", license_name, status, days_until_expiration)

    result_usage_based_entitlements = sf.query("SELECT MasterLabel, AmountUsed, CurrentAmountAllowed, EndDate FROM TenantUsageEntitlement")
    for entry in result_usage_based_entitlements['records']:
        license_name = dict(entry)['MasterLabel']
        total_licenses = dict(entry)['CurrentAmountAllowed']
        used_licenses = dict(entry)['AmountUsed']
        expiration_date = dict(entry)['EndDate']

        gauges.total_usage_based_entitlements_licenses_gauge.labels(license_name=license_name).set(total_licenses)
        if used_licenses:
            gauges.used_usage_based_entitlements_licenses_gauge.labels(license_name=license_name).set(used_licenses)

        if total_licenses != 0 and used_licenses is not None:
            percent_used = (used_licenses / total_licenses) * 100
            gauges.percent_usage_based_entitlements_used_gauge.labels(license_name=license_name, expiration_date=expiration_date, used_licenses=used_licenses, total_licenses=total_licenses).set(percent_used)

            if percent_used >= 90:
                logger.warning('License usage for %s has exceeded %s percent of the total limit.',
                                license_name, percent_used)

        if expiration_date:
            expiration_date = datetime.strptime(expiration_date, '%Y-%m-%d')
            days_until_expiration = (expiration_date - datetime.now()).days

            if days_until_expiration < 30 and days_until_expiration >= 0:
                logger.warning("License %s is expiring in less than 30 days: %s days left.",
                                license_name, days_until_expiration)


def get_salesforce_instance(sf):
    """
    Get instance info for the org.
    """
    logger.info("Getting Salesforce instance info...")
    prod_org_result = sf.query_all("Select FIELDS(ALL) From Organization LIMIT 1")
    prod_pod = prod_org_result['records'][0]['InstanceName']
    gauges.incident_gauge.clear()

    pod_map = {
        "Production": prod_pod,
        "FullQA": "USA654S",
        "Dev": "USA662S"
    }

    for org in ("Production", "Dev", "FullQA"):
        try:
            pod = pod_map.get(org)
            get_salesforce_incidents(org, pod)
        except requests.RequestException as e:
            logger.error("Error getting Salesforce instance status: %s", e)
        except SalesforceMalformedRequest as e:
            logger.error("Salesforce malformed request error: %s", e)

    get_salesforce_maintenances(pod_map)


def get_salesforce_incidents(org, instancepod):
    """
    Get all open incidents against the org.
    """
    try:
        # Clear the gauge for this specific org and pod combination before processing
        gauges.incident_gauge.labels(environment=org, pod=instancepod, severity='ok', message=None).set(0)

        response = requests.get("https://api.status.salesforce.com/v1/incidents/active",
                                timeout=REQUESTS_TIMEOUT_SECONDS)
        response.raise_for_status()
        incidents = response.json()
        incident_cnt = 0

        for element in incidents:
            try:
                # Check if IncidentEvents is not empty
                if element['IncidentEvents']:
                    message = element['IncidentEvents'][0].get('message', 'No message')
                else:
                    message = 'No message'

                # Access the IncidentImpacts to get the severity
                severity = element['IncidentImpacts'][0].get('severity', 'unknown')
                pods = str(element['instanceKeys']).replace("'", "").replace("[", "").replace("]", "")

                if instancepod in pods:
                    gauges.incident_gauge.labels(environment=org, pod=instancepod, severity=severity, message=message).set(1)
                    incident_cnt += 1
            except (KeyError, IndexError) as e:
                logger.warning("Error processing incident element: %s", e)

        # If no incidents were counted, ensure the gauge is set to 0 with severity 'ok'
        if incident_cnt == 0:
            gauges.incident_gauge.labels(environment=org, pod=instancepod, severity='ok', message=None).set(0)

    except requests.RequestException as e:
        logger.error("Error fetching incidents: %s", e)
        # Clear the specific gauge only in case of an error
        gauges.incident_gauge.labels(environment=org, pod=instancepod, severity='ok', message=None).set(0)


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
                        gauges.maintenance_gauge.labels(environment=pod_name,
                                                        maintenance_id=maintenance_id,
                                                        status=status,
                                                        planned_start_time=planned_start_time,
                                                        planned_end_time=planned_end_time).set(1)

    except requests.RequestException as e:
        logger.error("Error fetching incidents: %s", e)
        gauges.incident_gauge.clear()
