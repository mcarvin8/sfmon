"""
    Monitor critical Salesforce endpoints.
"""
import csv
from datetime import datetime, timedelta, timezone
import io
from io import StringIO
import json
import logging
import os
import subprocess
import time

import requests
from prometheus_client import Gauge, start_http_server
from simple_salesforce import SalesforceMalformedRequest, Salesforce

# Set up logging for CloudWatch
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
TOTAL_LICENSES = 'Total Salesforce licenses'
USED_LICENSES = 'Used Salesforce licenses'
USED_LICENSES_PERCENTAGE = 'Percentage of Salesforce licenses used'
REQUESTS_TIMEOUT_SECONDS = 300

# Prometheus metrics
api_usage_gauge = Gauge('salesforce_api_usage', 'Salesforce API Usage', ['limit_name'])
api_usage_percentage_gauge = Gauge('salesforce_api_usage_percentage', 'Salesforce API Usage Percentage', ['limit_name', 'limit_description', 'limit_utilized', 'max_limit'])

total_user_licenses_gauge = Gauge('salesforce_total_user_licenses',
                                  TOTAL_LICENSES, ['license_name', 'status'])
used_user_licenses_gauge = Gauge('salesforce_used_user_licenses',
                                 USED_LICENSES, ['license_name', 'status'])
percent_user_licenses_used_gauge = Gauge('salesforce_user_licenses_usage_percentage', USED_LICENSES_PERCENTAGE, ['license_name', 'status', 'used_licenses', 'total_licenses'])

total_permissionset_licenses_gauge = Gauge('salesforce_total_permissionset_licenses', TOTAL_LICENSES, ['license_name', 'status'])
used_permissionset_licenses_gauge = Gauge('salesforce_used_permissionset_licenses', USED_LICENSES, ['license_name', 'status'])
percent_permissionset_used_gauge = Gauge('salesforce_permissionset_license_usage_percentage', USED_LICENSES_PERCENTAGE, ['license_name', 'status', 'used_licenses', 'total_licenses', 'expiration_date'])

total_usage_based_entitlements_licenses_gauge = Gauge('salesforce_total_licenses_usage_based_entitlements', TOTAL_LICENSES, ['license_name'])
used_usage_based_entitlements_licenses_gauge = Gauge('salesforce_used_licenses_usage_based_entitlements', USED_LICENSES, ['license_name'])
percent_usage_based_entitlements_used_gauge = Gauge('salesforce_percent_used_usage_based_entitlements', USED_LICENSES_PERCENTAGE, ['license_name', 'used_licenses', 'total_licenses', 'expiration_date'])

incident_gauge = Gauge('salesforce_incidents', 'Number of active Salesforce incidents', ['pod', 'severity', 'message'])
login_count_gauge = Gauge('salesforce_login_count', 'Number of logins', ['geohash', 'latitude', 'longitude'])

deployment_details_gauge = Gauge('deployment_details', 'Salesforce Deployment details', ['pending_time', 'deployment_time', 'deployed_by', 'status', 'deployment_id'])
pending_time_gauge = Gauge('deployment_pending_time', 'Pending time before starting the deployment', ['deployment_id', 'deployed_by', 'status'])
deployment_time_gauge = Gauge('deployment_time', 'Time taken for the deployment', ['deployment_id', 'deployed_by', 'status'])

ept_metric = Gauge('salesforce_experienced_page_time', 'Experienced Page Time (EPT) in seconds', ['EFFECTIVE_PAGE_TIME_DEVIATION_REASON', 'EFFECTIVE_PAGE_TIME_DEVIATION_ERROR_TYPE', 'PREVPAGE_ENTITY_TYPE', 'PREVPAGE_APP_NAME', 'PAGE_ENTITY_TYPE', 'PAGE_APP_NAME', 'BROWSER_NAME'])

login_success_gauge = Gauge('salesforce_login_success_total', 'Total number of successful Salesforce logins')
login_failure_gauge = Gauge('salesforce_login_failure_total', 'Total number of failed Salesforce logins')

geolocation_gauge = Gauge('user_location', 'Longitude and Latitude of user location', ['user', 'longitude', 'latitude', 'browser', 'status'])

async_job_status_gauge = Gauge('salesforce_async_job_status_count', 'Total count of Salesforce Async Jobs by Status', ['status', 'method', 'job_type', 'number_of_errors'])

run_time_metric = Gauge('salesforce_apex_run_time_seconds', 'Total Apex execution time', ['entry_point', 'quiddity'])
cpu_time_metric = Gauge('salesforce_apex_cpu_time_seconds', 'CPU time used by Apex execution', ['entry_point', 'quiddity'])
exec_time_metric = Gauge('salesforce_apex_execution_time_seconds', 'Total execution time', ['entry_point', 'quiddity'])
db_total_time_metric = Gauge('salesforce_apex_db_total_time_seconds', 'Total database execution time', ['entry_point', 'quiddity'])
callout_time_metric = Gauge('salesforce_apex_callout_time_seconds', 'Total callout time', ['entry_point', 'quiddity'])
long_running_requests_metric = Gauge('salesforce_apex_long_running_requests_total', 'Number of long-running requests', ['entry_point', 'quiddity'])

apex_cpu_timeout_exception_metric_gauge = Gauge('apex_cpu_timeout_exceeded_exceptions', 'Count of CPU timeout exceptions', ['request_id', 'entry_point', 'quiddity', 'cpu_time', 'run_time', 'exception_type', 'exception_message', 'stack_trace', 'exception_category'])
total_apex_exception_metric_guage = Gauge('total_apex_exceptions', 'Count of Apex exceptions by category', ['exception_category'])


salesforce_limits_descriptions = {
    'ActiveScratchOrgs': 'Number of active scratch orgs in use.',
    'AnalyticsExternalDataSizeMB': 'Storage size used by external analytics data in MB.',
    'CdpAiInferenceApiMonthlyLimit': 'Monthly limit for CDP AI Inference API calls.',
    'ConcurrentAsyncGetReportInstances': 'Number of concurrent asynchronous report instances.',
    'ConcurrentEinsteinDataInsightsStoryCreation': 'Concurrent creation limit for Einstein Data Insights stories.',
    'ConcurrentEinsteinDiscoveryStoryCreation': 'Concurrent creation limit for Einstein Discovery stories.',
    'ConcurrentSyncReportRuns': 'Number of concurrent synchronous report runs.',
    'DailyAnalyticsDataflowJobExecutions': 'Daily limit for executing analytics dataflow jobs.',
    'DailyAnalyticsUploadedFilesSizeMB': 'Daily limit on size of uploaded analytics files in MB.',
    'DailyApiRequests': 'Daily limit on API requests.',
    'DailyAsyncApexExecutions': 'Daily limit for asynchronous Apex executions.',
    'DailyAsyncApexTests': 'Daily limit for asynchronous Apex test executions.',
    'DailyBulkApiBatches': 'Daily limit on bulk API batches.',
    'DailyBulkV2QueryFileStorageMB': 'Daily limit on storage size for Bulk API v2 query files in MB.',
    'DailyBulkV2QueryJobs': 'Daily limit on Bulk API v2 query jobs.',
    'DailyDeliveredPlatformEvents': 'Daily limit for delivered platform events.',
    'DailyDurableGenericStreamingApiEvents': 'Daily limit for durable generic streaming API events.',
    'DailyDurableStreamingApiEvents': 'Daily limit for durable streaming API events.',
    'DailyEinsteinDataInsightsStoryCreation': 'Daily limit for Einstein Data Insights story creation.',
    'DailyEinsteinDiscoveryOptimizationJobRuns': 'Daily limit for Einstein Discovery optimization job runs.',
    'DailyEinsteinDiscoveryPredictAPICalls': 'Daily limit for Einstein Discovery Predict API calls.',
    'DailyEinsteinDiscoveryPredictionsByCDC': 'Daily limit for Einstein Discovery predictions by CDC.',
    'DailyEinsteinDiscoveryStoryCreation': 'Daily limit for Einstein Discovery story creation.',
    'DailyFunctionsApiCallLimit': 'Daily limit for Salesforce Functions API calls.',
    'DailyGenericStreamingApiEvents': 'Daily limit for generic streaming API events.',
    'DailyScratchOrgs': 'Daily limit for scratch org creation.',
    'DailyStandardVolumePlatformEvents': 'Daily limit for standard volume platform events.',
    'DailyStreamingApiEvents': 'Daily limit for streaming API events.',
    'DailyWorkflowEmails': 'Daily limit for workflow emails sent.',
    'DataStorageMB': 'Total data storage limit in MB.',
    'DurableStreamingApiConcurrentClients': 'Concurrent client limit for durable streaming API.',
    'FileStorageMB': 'Total file storage limit in MB.',
    'HourlyAsyncReportRuns': 'Hourly limit for asynchronous report runs.',
    'HourlyDashboardRefreshes': 'Hourly limit for dashboard refreshes.',
    'HourlyDashboardResults': 'Hourly limit for retrieving dashboard results.',
    'HourlyDashboardStatuses': 'Hourly limit for checking dashboard statuses.',
    'HourlyElevateAsyncReportRuns': 'Hourly limit for elevate asynchronous report runs.',
    'HourlyElevateSyncReportRuns': 'Hourly limit for elevate synchronous report runs.',
    'HourlyLongTermIdMapping': 'Hourly limit for long-term ID mapping.',
    'HourlyManagedContentPublicRequests': 'Hourly limit for managed content public requests.',
    'HourlyODataCallout': 'Hourly limit for OData callouts.',
    'HourlyPublishedPlatformEvents': 'Hourly limit for published platform events.',
    'HourlyPublishedStandardVolumePlatformEvents': 'Hourly limit for published standard volume platform events.',
    'HourlyShortTermIdMapping': 'Hourly limit for short-term ID mapping.',
    'HourlySyncReportRuns': 'Hourly limit for synchronous report runs.',
    'HourlyTimeBasedWorkflow': 'Hourly limit for time-based workflow actions.',
    'MassEmail': 'Daily limit for sending mass emails.',
    'MonthlyEinsteinDiscoveryStoryCreation': 'Monthly limit for Einstein Discovery story creation.',
    'MonthlyPlatformEventsUsageEntitlement': 'Monthly limit for platform events usage.',
    'Package2VersionCreates': 'Limit for creating package versions.',
    'Package2VersionCreatesWithoutValidation': 'Limit for creating package versions without validation.',
    'PermissionSets': 'Total number of permission sets allowed.',
    'PrivateConnectOutboundCalloutHourlyLimitMB': 'Hourly limit on Private Connect outbound callout data in MB.',
    'PublishCallbackUsageInApex': 'Limit for publish callback usage in Apex.',
    'SingleEmail': 'Daily limit for sending single emails.',
    'StreamingApiConcurrentClients': 'Concurrent client limit for streaming API.'
}


def get_salesforce_connection_url(url):
    """
    Connect to Salesforce using the Salesforce CLI and Simple Salesforce via a URL
    Requires `sf` CLI v2.24.4/newer
    """
    try:
        login_cmd = f'echo {url} | sf org login sfdx-url --set-default --sfdx-url-stdin -'
        subprocess.run(login_cmd, check=True, shell=True)
        display_cmd = subprocess.run('sf org display --json', check=True,
                                     shell=True, stdout=subprocess.PIPE)
        sfdx_info = json.loads(display_cmd.stdout)

        access_token = sfdx_info['result']['accessToken']
        instance_url = sfdx_info['result']['instanceUrl']
        api_version = sfdx_info['result']['apiVersion']
        domain = 'test' if 'sandbox' in instance_url else 'login'
        return Salesforce(instance_url=instance_url, session_id=access_token, domain=domain, version=api_version)

    except subprocess.CalledProcessError as e:
        logging.error("Error logging into Salesforce: %s", e)
        raise
    except KeyError as e:
        logging.error("Missing expected key in Salesforce CLI output: %s", e)
        raise


def monitor_salesforce_limits(limits):
    """
    Monitor all Salesforce limits.
    """
    for limit_name, limit_data in limits.items():
        max_limit = limit_data['Max']
        remaining = limit_data['Remaining']
        used = max_limit - remaining

        if max_limit != 0:
            usage_percentage = (used * 100) / max_limit

            api_usage_gauge.labels(limit_name=limit_name).set(used)
            api_usage_percentage_gauge.labels(limit_name=limit_name, limit_description=salesforce_limits_descriptions.get(limit_name, 'Description not available'), limit_utilized=used, max_limit=max_limit).set(usage_percentage)

            if usage_percentage >= 90:
                logging.warning('API usage for %s has exceeded %s percent of the total limit.',
                                limit_name, usage_percentage)


def get_salesforce_licenses(sf):
    """
    Get all license data.
    """
    result_user_license = sf.query("SELECT Name, Status, UsedLicenses, TotalLicenses FROM UserLicense")
    for entry in result_user_license['records']:
        status = dict(entry)['Status']
        license_name = entry['Name']
        total_licenses = dict(entry)['TotalLicenses']
        used_licenses = dict(entry)['UsedLicenses']

        total_user_licenses_gauge.labels(license_name=license_name, status=status).set(total_licenses)
        used_user_licenses_gauge.labels(license_name=license_name, status=status).set(used_licenses)

        if total_licenses != 0:
            percent_used = (used_licenses / total_licenses) * 100
            percent_user_licenses_used_gauge.labels(license_name=license_name, status=status, used_licenses=used_licenses, total_licenses=total_licenses).set(percent_used)

            if percent_used >= 90:
                logging.warning('License usage for %s has exceeded %s percent of the total limit.',
                                license_name, percent_used)

    result_perm_set_license = sf.query("SELECT MasterLabel, Status, ExpirationDate, TotalLicenses, UsedLicenses FROM PermissionSetLicense")
    for entry in result_perm_set_license['records']:
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

            if percent_used >= 90:
                logging.warning('License usage for %s has exceeded %s percent of the total limit.', license_name, percent_used)

        if expiration_date:
            expiration_date = datetime.strptime(expiration_date, '%Y-%m-%d')
            days_until_expiration = (expiration_date - datetime.now()).days

            if days_until_expiration < 30 and status != 'Disabled':
                logging.warning("License %s with status %s is expiring in less than 30 days: %s days left.", license_name, status, days_until_expiration)

    result_usage_based_entitlements = sf.query("SELECT MasterLabel, AmountUsed, CurrentAmountAllowed, EndDate FROM TenantUsageEntitlement")
    for entry in result_usage_based_entitlements['records']:
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

            if percent_used >= 90:
                logging.warning('License usage for %s has exceeded %s percent of the total limit.',
                                license_name, percent_used)

        if expiration_date:
            expiration_date = datetime.strptime(expiration_date, '%Y-%m-%d')
            days_until_expiration = (expiration_date - datetime.now()).days

            if days_until_expiration < 30 and days_until_expiration >= 0:
                logging.warning("License %s is expiring in less than 30 days: %s days left.",
                                license_name, days_until_expiration)


def get_salesforce_instance(sf):
    """
    Get instance info for the org.
    """
    # At this stage, we're already authenticated to Prod for other monitoring checks
    org_result = sf.query_all("Select FIELDS(ALL) From Organization LIMIT 1")
    pod = org_result['records'][0]['InstanceName']

    try:
        response = requests.get(f"https://api.status.salesforce.com/v1/instances/{pod}/status/preview?childProducts=false", timeout=REQUESTS_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
        release_version = data['releaseVersion']
        release_number = data['releaseNumber']
        next_maintenance = data['maintenanceWindow']
        logging.info("%s - Release: %s, Number: %s, Maintenance: %s",
                        pod, release_version, release_number, next_maintenance)
        get_salesforce_incidents(pod)
    except requests.RequestException as e:
        logging.error("Error getting Salesforce instance status: %s", e)
    except SalesforceMalformedRequest as e:
        logging.error("Salesforce malformed request error: %s", e)


def get_salesforce_incidents(instancepod):
    """
    Get all open incidents against the org.
    """
    try:
        response = requests.get("https://api.status.salesforce.com/v1/incidents/active",
                                timeout=REQUESTS_TIMEOUT_SECONDS)
        response.raise_for_status()
        incidents = response.json()
        incident_cnt = 0

        for element in incidents:
            try:
                message = element['IncidentEvents'][0]['message']
                # Access the IncidentImpacts to get the severity
                severity = element['IncidentImpacts'][0]['severity']
                pods = str(element['instanceKeys']).replace("'", "").replace("[", "").replace("]", "")
                if instancepod in pods:
                    incident_gauge.labels(pod=instancepod, severity=severity, message=message).set(1)
                    incident_cnt += 1
            except (KeyError, IndexError) as e:
                logging.warning("Error processing incident element: %s", e)
        if incident_cnt == 0:
            incident_gauge.labels(pod=instancepod, severity='ok', message=None).set(0)
    except requests.RequestException as e:
        logging.error("Error fetching incidents: %s", e)
        incident_gauge.clear()


def get_deployment_status(sf):
    """
    Get deployment related info from the org.
    """
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


def get_salesforce_ept(sf):
    """
    Get EPT data from the org.
    """
    # Query the Event Log Files for EPT data
    query = """SELECT EventType, LogDate, Id FROM EventLogFile WHERE Interval='Hourly' and EventType = 'LightningPageView' ORDER BY LogDate DESC LIMIT 1"""
    result = sf.query(query)

    # Process the result to extract relevant EPT data
    for record in result['records']:
        log_data_url = sf.base_url + f"/sobjects/EventLogFile/{record['Id']}/LogFile"
        response = requests.get(log_data_url, headers={"Authorization": f"Bearer {sf.session_id}"},
                                timeout=REQUESTS_TIMEOUT_SECONDS)

        if response.status_code == 200:
            log_data = response.text
            csv_data = csv.DictReader(io.StringIO(log_data))

            for row in csv_data:
                if row['EFFECTIVE_PAGE_TIME_DEVIATION']:
                    ept = float(row['EFFECTIVE_PAGE_TIME'])/1000 if row['EFFECTIVE_PAGE_TIME'] else 0

                    ept_metric.labels(EFFECTIVE_PAGE_TIME_DEVIATION_REASON=row['EFFECTIVE_PAGE_TIME_DEVIATION_REASON'],
                                      EFFECTIVE_PAGE_TIME_DEVIATION_ERROR_TYPE=row['EFFECTIVE_PAGE_TIME_DEVIATION_ERROR_TYPE'],
                                      PREVPAGE_ENTITY_TYPE=row['PREVPAGE_ENTITY_TYPE'],
                                      PREVPAGE_APP_NAME=row['PREVPAGE_APP_NAME'],
                                      PAGE_ENTITY_TYPE=row['PAGE_ENTITY_TYPE'],
                                      PAGE_APP_NAME=row['PAGE_APP_NAME'],
                                      BROWSER_NAME=row['BROWSER_NAME']).set(ept)


def monitor_login_events(sf):
    """
    Get login events from the org.
    """
    try:
        query = "SELECT Id, LogDate, Interval FROM EventLogFile WHERE EventType = 'Login' and Interval = 'Hourly' ORDER BY LogDate DESC"
        event_log_file = sf.query(query)

        if event_log_file['totalSize'] > 0:
            log_id = event_log_file['records'][0]['Id']
            log_data_url = sf.base_url + f"/sobjects/EventLogFile/{log_id}/LogFile"
            log_data = requests.get(log_data_url,
                                    headers={"Authorization": f"Bearer {sf.session_id}"},
                                    timeout=REQUESTS_TIMEOUT_SECONDS)
            log_data.raise_for_status()  # Raise an error if the request failed

            if log_data.text:
                csv_reader = csv.DictReader(StringIO(log_data.text))
                success_count = 0
                failure_count = 0

                for row in csv_reader:
                    status = row.get('LOGIN_STATUS')
                    if status == 'LOGIN_NO_ERROR':
                        success_count += 1
                    else:
                        failure_count += 1

                login_success_gauge.set(success_count)
                login_failure_gauge.set(failure_count)

            else:
                return None
        else:
            return None
    except Exception:
        return None


def geolocation(sf, chunk_size=100):
    """
    Get geolocation data from login events.
    """
    try:
        end_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        start_time = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')

        query = f"SELECT UserId, LoginGeo.Latitude, LoginGeo.Longitude, Status, Browser FROM LoginHistory WHERE LoginTime >= {start_time} AND LoginTime <= {end_time}"
        user_location = sf.query_all(query)
        locations = user_location['records']

        user_ids = [record['UserId'] for record in locations]

        # Query User object to get names for the UserIds in chunks
        user_map = {}
        for i in range(0, len(user_ids), chunk_size):
            chunk = user_ids[i:i + chunk_size]
            user_query = f"SELECT Id, Name FROM User WHERE Id IN ({', '.join([f"'{uid}'" for uid in chunk])})"
            user_results = sf.query_all(user_query)
            user_map.update({user['Id']: user['Name'] for user in user_results['records']})

        for record in locations:
            record['UserName'] = user_map.get(record['UserId'], 'Unknown User')
            if 'LoginGeo' in record and record['LoginGeo']:
                latitude = record['LoginGeo']['Latitude']
                longitude = record['LoginGeo']['Longitude']
                username = record['UserName']
                browser = record['Browser']
                login_status = record['Status']
                geolocation_gauge.labels(user=username, longitude=longitude, latitude=latitude, browser=browser, status=login_status).set(1)

    except KeyError as e:
        logging.error("Key error: %s", e)
    except Exception as e:
        logging.error("Unexpected error: %s", e)


def async_apex_job_status(sf):
    """
    Get async apex job status details from the org.
    """
    query = """
        SELECT Id, Status, JobType, ApexClassId, MethodName, NumberOfErrors FROM AsyncApexJob 
        WHERE CreatedDate = TODAY
    """

    result = sf.query_all(query)
    overall_status_counts = {}

    for record in result['records']:
        status = record['Status']
        job_type = record['JobType']
        method = record['MethodName']
        errors = record['NumberOfErrors']

        if (status, method, job_type, errors) not in overall_status_counts:
            overall_status_counts[(status, method, job_type, errors)] = 0
        overall_status_counts[(status, method, job_type, errors)] += 1

    for (status, method, job_type, errors), count in overall_status_counts.items():
        async_job_status_gauge.labels(status=status, method=method, job_type=job_type, number_of_errors=errors).set(count)


def parse_logs(sf, log_query):
    """
    Fetch and parse logs from given query
    """
    try:
        event_log_records = sf.query(log_query)
        if not event_log_records['totalSize']:
            return None

        log_id = event_log_records['records'][0]['Id']
        log_file_url = f"{sf.base_url}/sobjects/EventLogFile/{log_id}/LogFile"
        log_file_response = requests.get(log_file_url, headers={"Authorization": f"Bearer {sf.session_id}"}, timeout=REQUESTS_TIMEOUT_SECONDS)
        log_file_response.raise_for_status()

        log_content = log_file_response.text
        if not log_content:
            return None

        return csv.DictReader(StringIO(log_content))

    except requests.RequestException as req_err:
        logging.error("Request error occurred: %s", req_err)
    except csv.Error as csv_err:
        logging.error("CSV processing error: %s", csv_err)
    except Exception as e:
        logging.error("An unexpected error occurred: %s", e)


def monitor_apex_execution(sf):
    """
    Get apex job execution details from the org
    and expose run_time, cpu_time, execution_time, database_time, callout_time etc details.
    """

    try:
        log_query = (
            "SELECT Id FROM EventLogFile WHERE EventType = 'ApexExecution' and Interval = 'Hourly' "
            "ORDER BY LogDate DESC LIMIT 1")

        apex_execution_logs = parse_logs(sf, log_query)

        for log_entry in apex_execution_logs:
            entry_point = log_entry.get('ENTRY_POINT')
            run_time = float(log_entry.get('RUN_TIME', 0))
            cpu_time = float(log_entry.get('CPU_TIME', 0))
            exec_time = float(log_entry.get('EXEC_TIME', 0))
            db_total_time = float(log_entry.get('DB_TOTAL_TIME', 0))
            callout_time = float(log_entry.get('CALLOUT_TIME', 0))
            is_long_running = float(log_entry.get('IS_LONG_RUNNING_REQUEST', 0))
            quiddity = log_entry.get('QUIDDITY')

            run_time_metric.labels(entry_point=entry_point, quiddity=quiddity).set(run_time)
            cpu_time_metric.labels(entry_point=entry_point, quiddity=quiddity).set(cpu_time)
            exec_time_metric.labels(entry_point=entry_point, quiddity=quiddity).set(exec_time)
            db_total_time_metric.labels(entry_point=entry_point, quiddity=quiddity).set(db_total_time)
            callout_time_metric.labels(entry_point=entry_point, quiddity=quiddity).set(callout_time)
            long_running_requests_metric.labels(entry_point=entry_point, quiddity=quiddity).set(is_long_running)

    except Exception as e:
        logging.error("An unexpected error occurred: %s", e)


def apex_cpu_timeout_errors(sf):
    """
    Fetch ApexExecution and ApexUnexpectedException logs
    Match 'REQUEST_ID' of ApexExecution logs with ApexUnexpectedException
    Findout entries with EXCEPTION_MESSAGE containing 'Apex CPU time limit exceeded'
    and expose apex_cpu_timeout_exception_metric and total_apex_exception_metric
    """

    apex_cpu_timeout_exception_metric_gauge.clear()
    total_apex_exception_metric_guage.clear()

    try:
        apex_execution_query = (
            "SELECT Id FROM EventLogFile WHERE EventType = 'ApexExecution' and Interval = 'Hourly' "
            "ORDER BY LogDate DESC LIMIT 1")
        apex_execution_records = parse_logs(sf, apex_execution_query)

        apex_unexpected_exception_query = (
            "SELECT Id FROM EventLogFile WHERE EventType = 'ApexUnexpectedException' and Interval = 'Hourly' "
            "ORDER BY LogDate DESC LIMIT 1")
        apex_unexpected_exception_records = list(parse_logs(sf, apex_unexpected_exception_query))

        exception_category_counts = {}

        for row in apex_unexpected_exception_records:
            category = row['EXCEPTION_CATEGORY']
            if category in exception_category_counts:
                exception_category_counts[category] += 1
            else:
                exception_category_counts[category] = 1

        # Expose the metrics for each exception category
        for category, count in exception_category_counts.items():
            total_apex_exception_metric_guage.labels(exception_category=category).set(count)

        unexpected_exceptions = {
            row['REQUEST_ID']: {
                'EXCEPTION_TYPE': row['EXCEPTION_TYPE'],
                'EXCEPTION_MESSAGE': row['EXCEPTION_MESSAGE'],
                'STACK_TRACE': row['STACK_TRACE'],
                'EXCEPTION_CATEGORY': row['EXCEPTION_CATEGORY']}
                for row in apex_unexpected_exception_records
                if 'Apex CPU time limit exceeded' in row['EXCEPTION_MESSAGE']}

        apex_executions = {row['REQUEST_ID']: row for row in apex_execution_records}

        # Process each unexpected exception and find matching execution logs
        for request_id, exception_details in unexpected_exceptions.items():
            if request_id in apex_executions:
                execution_details = apex_executions[request_id]

                apex_cpu_timeout_exception_metric_gauge.labels(
                    request_id=request_id,
                    entry_point=execution_details['ENTRY_POINT'],
                    quiddity=execution_details['QUIDDITY'],
                    cpu_time=execution_details['CPU_TIME'],
                    run_time=execution_details['RUN_TIME'],
                    exception_type=exception_details['EXCEPTION_TYPE'],
                    exception_message=exception_details['EXCEPTION_MESSAGE'],
                    stack_trace=exception_details['STACK_TRACE'],
                    exception_category=exception_details['EXCEPTION_CATEGORY']).set(1)

    except Exception as e:
        logging.error("An unexpected error occurred: %s", e)


def main():
    """
    Main function.
    """
    start_http_server(9001)

    while True:
        try:
            sf = get_salesforce_connection_url(url=os.getenv('SALESFORCE_AUTH_URL'))
            logging.info("Monitoring Salesforce limits...")
            monitor_salesforce_limits(dict(sf.limits()))

            logging.info("Getting Salesforce licenses...")
            get_salesforce_licenses(sf)

            logging.info("Getting Salesforce instance info...")
            get_salesforce_instance(sf)

            logging.info("Getting deployment status...")
            get_deployment_status(sf)

            logging.info("Monitoring Salesforce EPT...")
            get_salesforce_ept(sf)

            logging.info("Monitoring login events...")
            monitor_login_events(sf)

            logging.info("Getting geolocation data...")
            geolocation(sf, chunk_size=100)

            logging.info("Getting Async Job status...")
            async_apex_job_status(sf)

            logging.info("Getting Apex executions...")
            monitor_apex_execution(sf)

            logging.info("Getting Apex CPU Timeout exeception errors...")
            apex_cpu_timeout_errors(sf)

        except Exception as e:
            logging.error("An error occurred: %s", e)
        logging.info('Sleeping for 30 minutes...')
        time.sleep(1800)
        logging.info('Resuming...')

if __name__ == '__main__':
    main()
