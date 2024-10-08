"""
    Monitor critical Salesforce endpoints.
"""
from collections import defaultdict
import csv
from datetime import datetime, timedelta, timezone
import io
from io import StringIO
import os
import time

import requests
from prometheus_client import start_http_server
from simple_salesforce import SalesforceMalformedRequest
import schedule

from cloudwatch_logging import logger
from connection_sf import get_salesforce_connection_url
import gauges
from limits import salesforce_limits_descriptions


# Constants
REQUESTS_TIMEOUT_SECONDS = 300
QUERY_TIMEOUT_SECONDS = 30


def monitor_salesforce_limits(limits):
    """
    Monitor all Salesforce limits.
    """
    logger.info("Monitoring Salesforce limits...")
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


def daily_analyse_bulk_api(sf):
    """
    Analyse Bulk API usage with respect to user_id, entity_type, operation_type, number of rows processed, number of failures.
    """

    logger.info("Getting Daily Bulk API details...")
    try:
        log_query = (
            "SELECT Id FROM EventLogFile WHERE EventType = 'BulkAPI' and Interval = 'Daily' "
            "ORDER BY LogDate DESC LIMIT 1")

        bulk_api_logs = parse_logs(sf, log_query)

        batch_counts = defaultdict(int)
        total_records_failed = defaultdict(int)
        total_records_processed = defaultdict(int)
        entity_type_counts = defaultdict(int)

        for row in bulk_api_logs:
            job_id = row['JOB_ID'] if row['JOB_ID'] else None
            user_id = row['USER_ID']
            entity_type = row['ENTITY_TYPE'] if row['ENTITY_TYPE'] else None
            operation_type = row['OPERATION_TYPE'] if row['OPERATION_TYPE'] else None
            rows_processed = int(row['ROWS_PROCESSED']) if row['ROWS_PROCESSED'].isdigit() else 0
            number_failures = int(row['NUMBER_FAILURES']) if row['NUMBER_FAILURES'].isdigit() else 0

            if not entity_type or entity_type.lower() == 'none':
                continue

            batch_counts[(job_id, user_id, entity_type)] += 1
            total_records_failed[(job_id, user_id, entity_type)] += number_failures
            total_records_processed[(job_id, user_id, entity_type)] += rows_processed
            entity_type_counts[(user_id, operation_type, entity_type)] += 1

        for key, count in batch_counts.items():
            job_id, user_id, entity_type = key
            gauges.daily_batch_count_metric.labels(
                job_id=job_id, user_id=user_id, entity_type=entity_type,
                total_records_failed=total_records_failed[key],
                total_records_processed=total_records_processed[key]).set(count)

        for (user_id, operation_type, entity_type), count in entity_type_counts.items():
            gauges.daily_entity_type_count_metric.labels(user_id=user_id, operation_type=operation_type, entity_type=entity_type).set(count)

    except Exception as e:
        logger.error("An unexpected error occurred: %s", e)


def hourly_analyse_bulk_api(sf):
    """
    Analyse Bulk API usage with respect to user_id, entity_type, operation_type, number of rows processed, number of failures.
    """

    logger.info("Getting Hourly based Bulk API details...")
    try:
        log_query = (
            "SELECT Id FROM EventLogFile WHERE EventType = 'BulkAPI' and Interval = 'Hourly' "
            "ORDER BY LogDate DESC LIMIT 1")

        bulk_api_logs = parse_logs(sf, log_query)

        batch_counts = defaultdict(int)
        total_records_failed = defaultdict(int)
        total_records_processed = defaultdict(int)
        entity_type_counts = defaultdict(int)

        for row in bulk_api_logs:
            job_id = row['JOB_ID'] if row['JOB_ID'] else None
            user_id = row['USER_ID']
            entity_type = row['ENTITY_TYPE'] if row['ENTITY_TYPE'] else None
            operation_type = row['OPERATION_TYPE'] if row['OPERATION_TYPE'] else None
            rows_processed = int(row['ROWS_PROCESSED']) if row['ROWS_PROCESSED'].isdigit() else 0
            number_failures = int(row['NUMBER_FAILURES']) if row['NUMBER_FAILURES'].isdigit() else 0

            if not entity_type or entity_type.lower() == 'none':
                continue

            batch_counts[(job_id, user_id, entity_type)] += 1
            total_records_failed[(job_id, user_id, entity_type)] += number_failures
            total_records_processed[(job_id, user_id, entity_type)] += rows_processed
            entity_type_counts[(user_id, operation_type, entity_type)] += 1

        for key, count in batch_counts.items():
            job_id, user_id, entity_type = key
            gauges.hourly_batch_count_metric.labels(
                job_id=job_id, user_id=user_id, entity_type=entity_type,
                total_records_failed=total_records_failed[key],
                total_records_processed=total_records_processed[key]).set(count)

        for (user_id, operation_type, entity_type), count in entity_type_counts.items():
            gauges.hourly_entity_type_count_metric.labels(user_id=user_id, operation_type=operation_type, entity_type=entity_type).set(count)

    except Exception as e:
        logger.error("An unexpected error occurred: %s", e)


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
    org_result = sf.query_all("Select FIELDS(ALL) From Organization LIMIT 1")
    pod = org_result['records'][0]['InstanceName']

    try:
        response = requests.get(f"https://api.status.salesforce.com/v1/instances/{pod}/status/preview?childProducts=false", timeout=REQUESTS_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
        release_version = data['releaseVersion']
        release_number = data['releaseNumber']
        next_maintenance = data['maintenanceWindow']
        logger.info("%s - Release: %s, Number: %s, Maintenance: %s",
                        pod, release_version, release_number, next_maintenance)
        get_salesforce_incidents(pod)
    except requests.RequestException as e:
        logger.error("Error getting Salesforce instance status: %s", e)
    except SalesforceMalformedRequest as e:
        logger.error("Salesforce malformed request error: %s", e)


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
                    gauges.incident_gauge.labels(pod=instancepod, severity=severity, message=message).set(1)
                    incident_cnt += 1
            except (KeyError, IndexError) as e:
                logger.warning("Error processing incident element: %s", e)
        if incident_cnt == 0:
            gauges.incident_gauge.labels(pod=instancepod, severity='ok', message=None).set(0)
    except requests.RequestException as e:
        logger.error("Error fetching incidents: %s", e)
        gauges.incident_gauge.clear()


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

            gauges.deployment_details_gauge.labels(pending_time=pending_time, deployment_time=deployment_time, deployment_id=record['Id'],
                                            deployed_by=record['CreatedBy']['Name'], status=record['Status']).set(status_mapping[record['Status']])
            gauges.pending_time_gauge.labels(deployment_id=record['Id'], deployed_by=record['CreatedBy']['Name'], status=record['Status']).set(pending_time)
            gauges.deployment_time_gauge.labels(deployment_id=record['Id'], deployed_by=record['CreatedBy']['Name'], status=record['Status']).set(deployment_time)


def get_salesforce_ept_and_apt(sf):
    """
    Get EPT and APT data from the org.
    """
    logger.info("Monitoring Salesforce EPT and APT data...")
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

            page_time_data = defaultdict(lambda: {'total_time': 0, 'count': 0, 'sessions': {}})

            for row in csv_data:

                page_name = row['PAGE_APP_NAME'] if row['PAGE_APP_NAME'] else 'Unknown_Page'
                page_duration = float(row['DURATION'])/1000 if row['DURATION'] else 0
                page_time_data[page_name]['total_time'] += page_duration
                page_time_data[page_name]['count'] += 1

                average_page_time = {page: {'avg_time': data['total_time'] / data['count'],'count': data['count']}
                                     for page, data in page_time_data.items()}

                if row['EFFECTIVE_PAGE_TIME_DEVIATION']:
                    ept = float(row['EFFECTIVE_PAGE_TIME'])/1000 if row['EFFECTIVE_PAGE_TIME'] else 0

                    gauges.ept_metric.labels(EFFECTIVE_PAGE_TIME_DEVIATION_REASON=row['EFFECTIVE_PAGE_TIME_DEVIATION_REASON'],
                                      EFFECTIVE_PAGE_TIME_DEVIATION_ERROR_TYPE=row['EFFECTIVE_PAGE_TIME_DEVIATION_ERROR_TYPE'],
                                      PREVPAGE_ENTITY_TYPE=row['PREVPAGE_ENTITY_TYPE'],
                                      PREVPAGE_APP_NAME=row['PREVPAGE_APP_NAME'],
                                      PAGE_ENTITY_TYPE=row['PAGE_ENTITY_TYPE'],
                                      PAGE_APP_NAME=row['PAGE_APP_NAME'],
                                      BROWSER_NAME=row['BROWSER_NAME']).set(ept)

            for page_name, page_details in average_page_time.items():
                gauges.apt_metric.labels(Page_name=page_name, Page_count=page_details['count']).set(page_details['avg_time'])


def monitor_login_events(sf):
    """
    Get login events from the org.
    """
    logger.info("Monitoring login events...")
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

                gauges.login_success_gauge.set(success_count)
                gauges.login_failure_gauge.set(failure_count)

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
    logger.info("Getting geolocation data...")
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
                gauges.geolocation_gauge.labels(user=username, longitude=longitude, latitude=latitude, browser=browser, status=login_status).set(1)

    except KeyError as e:
        logger.error("Key error: %s", e)
    except Exception as e:
        logger.error("Unexpected error: %s", e)


def async_apex_job_status(sf):
    """
    Get async apex job status details from the org.
    """
    logger.info("Getting Async Job status...")
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
        gauges.async_job_status_gauge.labels(status=status, method=method, job_type=job_type, number_of_errors=errors).set(count)


def parse_logs(sf, log_query):
    """
    Fetch and parse logs from given query
    """
    try:
        event_log_records = sf.query(log_query, timeout=QUERY_TIMEOUT_SECONDS)
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
        logger.error("Request error occurred: %s", req_err)
    except csv.Error as csv_err:
        logger.error("CSV processing error: %s", csv_err)
    except Exception as e:
        logger.error("An unexpected error occurred: %s", e)


def monitor_apex_execution(sf):
    """
    Get apex job execution details from the org
    and expose run_time, cpu_time, execution_time, database_time, callout_time etc details.
    """
    logger.info("Getting Apex executions...")
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

            gauges.run_time_metric.labels(entry_point=entry_point, quiddity=quiddity).set(run_time)
            gauges.cpu_time_metric.labels(entry_point=entry_point, quiddity=quiddity).set(cpu_time)
            gauges.exec_time_metric.labels(entry_point=entry_point, quiddity=quiddity).set(exec_time)
            gauges.db_total_time_metric.labels(entry_point=entry_point, quiddity=quiddity).set(db_total_time)
            gauges.callout_time_metric.labels(entry_point=entry_point, quiddity=quiddity).set(callout_time)
            gauges.long_running_requests_metric.labels(entry_point=entry_point, quiddity=quiddity).set(is_long_running)

    except Exception as e:
        logger.error("An unexpected error occurred: %s", e)


def expose_apex_exception_metrics(sf):
    """
    Processes list of Apex Unexpected Exception records and exposes two Prometheus metrics:
    1. Detailed metrics for each individual exception including 
        request ID, exception type, message, stack trace, and category fields.
    2. Metric that counts the total number of exceptions for each exception category.
    """
    logger.info("Getting Apex unexpected execeptions...")
    apex_unexpected_exception_query = (
        "SELECT Id FROM EventLogFile WHERE EventType = 'ApexUnexpectedException' and Interval = 'Hourly' "
        "ORDER BY LogDate DESC LIMIT 1")
    apex_unexpected_exception_records = list(parse_logs(sf, apex_unexpected_exception_query))

    exception_category_counts = {}

    for row in apex_unexpected_exception_records:
        try:
            category = row['EXCEPTION_CATEGORY']

            # Count the number of occurrences of each exception category
            if category in exception_category_counts:
                exception_category_counts[category] += 1
            else:
                exception_category_counts[category] = 1

            # Expose the details for each entry
            gauges.apex_exception_details_gauge.labels(
                request_id=row['REQUEST_ID'],
                exception_type=row['EXCEPTION_TYPE'],
                exception_message=row['EXCEPTION_MESSAGE'],
                stack_trace=row['STACK_TRACE'],
                exception_category=category
            ).set(1)

        except KeyError as e:
            logger.error("Missing expected key: %s. Record: %s", e, row)
        except TypeError as e:
            logger.error("Type error encountered: %s. Record: %s", e, row)
        except Exception as e:
            logger.error("Unexpected error: %s. Record: %s", e, row)

    try:
        # Expose the metrics for each exception category
        for category, count in exception_category_counts.items():
            gauges.apex_exception_category_count_gauge.labels(exception_category=category).set(count)
    except Exception as e:
        logger.error("Error while exposing category count metrics: %s", e)


def get_user_name(sf, user_id):
    """
    Helper function to fetch user name by user ID.
    """
    try:
        query = f"SELECT Name FROM User WHERE Id = '{user_id}'"
        result = sf.query(query, timeout=QUERY_TIMEOUT_SECONDS)
        return result['records'][0]['Name'] if result['records'] else 'Unknown User'
    except Exception as e:
        logger.error("Error fetching user name for ID %s: %s", user_id, e)
        return 'Unknown User'


def hourly_observe_user_querying_large_records(sf):
    '''
    Observe user activity who querries more than 10k records
    '''
    logger.info("Getting Compliance data - User details querying large records...")

    try:
        log_query = (
            "SELECT Id FROM EventLogFile WHERE EventType = 'API' and Interval = 'Hourly' "
            "ORDER BY LogDate DESC LIMIT 1")

        api_log_records = parse_logs(sf, log_query)
        large_query_counts = {}

        gauges.hourly_large_query_metric.clear()

        for row in api_log_records:
            rows_processed = int(row['ROWS_PROCESSED']) if row['ROWS_PROCESSED'].isdigit() else 0

            if rows_processed > 10000:
                user_id = row['USER_ID'] if row['USER_ID'] else None
                method = row['METHOD_NAME'] if row['METHOD_NAME'] else None
                entity_name = row['ENTITY_NAME'] if row['ENTITY_NAME'] else None

                if not user_id:
                    continue

                user_name = get_user_name(sf, user_id)

                key = (user_id, user_name, method, entity_name, rows_processed)
                large_query_counts[key] = large_query_counts.get(key, 0) + 1

        for (user_id, user_name, method, entity_name, rows_processed), count in large_query_counts.items():
            gauges.hourly_large_query_metric.labels(
                user_id=user_id,user_name=user_name,
                method=method,entity_name=entity_name,
                rows_processed=rows_processed
            ).set(count)

    except Exception as e:
        logger.error("An error occurred: %s", e)


def community_login_error_logger_details(sf):
    """
    Monitors Apex failure for login (PRM and GSP) from SFDC Logger records where source = 'Community - Login'
    and Log level is Error or Fatal
    """

    try:
        query = """
        SELECT Id, Name, Source_Name__c, CreatedDate, Log_Message__c, Record_Id__c, Log_Level__c 
        FROM SFDC_Logger__c 
        WHERE Source_Name__c = 'Community - Login' 
        AND Log_Level__c IN ('Error','Fatal') 
        AND CreatedDate = LAST_N_DAYS:7 
        ORDER BY CreatedDate DESC
        """
        results = sf.query_all(query)

        gauges.community_login_error_metric.clear()

        if results['totalSize'] > 0:
            for record in results['records']:
                # Expose logger details as Prometheus metrics
                gauges.community_login_error_metric.labels(
                    id=record['Id'],
                    name=record['Name'],
                    log_level=record['Log_Level__c'],
                    log_message=record['Log_Message__c'],
                    record_id=record['Record_Id__c'],
                    created_date=record['CreatedDate']
                ).set(1)  # Set value to 1 (or any other constant value)

    except Exception as e:
        logger.error("Error fetching SFDC Logger records: %s", e)


def schedule_tasks(sf):
    """
    Schedule all tasks as per the required intervals.
    """
    # Every 5 minutes
    schedule.every(5).minutes.do(lambda: monitor_salesforce_limits(dict(sf.limits())))
    schedule.every(5).minutes.do(lambda: get_salesforce_licenses(sf))
    schedule.every(5).minutes.do(lambda: get_salesforce_instance(sf))

    # Twice a day
    schedule.every().day.at("08:00").do(lambda: daily_analyse_bulk_api(sf))
    schedule.every().day.at("20:00").do(lambda: daily_analyse_bulk_api(sf))
    schedule.every().day.at("08:00").do(lambda: get_deployment_status(sf))
    schedule.every().day.at("20:00").do(lambda: get_deployment_status(sf))
    schedule.every().day.at("08:00").do(lambda: geolocation(sf, chunk_size=100))
    schedule.every().day.at("20:00").do(lambda: geolocation(sf, chunk_size=100))
    schedule.every().day.at("08:00").do(lambda: community_login_error_logger_details(sf))
    schedule.every().day.at("20:00").do(lambda: community_login_error_logger_details(sf))

    # Every 30 minutes
    schedule.every(30).minutes.do(lambda: hourly_analyse_bulk_api(sf))
    schedule.every(30).minutes.do(lambda: get_salesforce_ept_and_apt(sf))
    schedule.every(30).minutes.do(lambda: monitor_login_events(sf))
    schedule.every(30).minutes.do(lambda: async_apex_job_status(sf))
    schedule.every(30).minutes.do(lambda: monitor_apex_execution(sf))
    schedule.every(30).minutes.do(lambda: expose_apex_exception_metrics(sf))
    schedule.every(30).minutes.do(lambda: hourly_observe_user_querying_large_records(sf))

    # Infinite loop to run pending tasks
    while True:
        schedule.run_pending()
        logger.info('Sleeping for 5 minutes...')
        time.sleep(300)
        logger.info('Resuming...')


def main():
    """
    Main function. Initializes and runs tasks according to their respective schedules.
    """
    try:
        start_http_server(9001)
        sf = get_salesforce_connection_url(url=os.getenv('PRODUCTION_AUTH_URL'))
        schedule_tasks(sf)
    except Exception as e:
        logger.error("An error occurred: %s", e)


if __name__ == '__main__':
    main()
