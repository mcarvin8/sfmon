"""
    Gauges for Prometheus.
"""
from prometheus_client import Gauge

# Constants
TOTAL_LICENSES = 'Total Salesforce licenses'
USED_LICENSES = 'Used Salesforce licenses'
USED_LICENSES_PERCENTAGE = 'Percentage of Salesforce licenses used'

# Prometheus metrics
api_usage_gauge = Gauge('salesforce_api_usage', 'Salesforce API Usage', ['limit_name'])
api_usage_percentage_gauge = Gauge('salesforce_api_usage_percentage',
                                   'Salesforce API Usage Percentage', 
                                   ['limit_name', 'limit_description',
                                    'limit_utilized', 'max_limit'])

total_user_licenses_gauge = Gauge('salesforce_total_user_licenses',
                                  TOTAL_LICENSES, ['license_name', 'status'])
used_user_licenses_gauge = Gauge('salesforce_used_user_licenses',
                                 USED_LICENSES, ['license_name', 'status'])
percent_user_licenses_used_gauge = Gauge('salesforce_user_licenses_usage_percentage',
                                         USED_LICENSES_PERCENTAGE,
                                         ['license_name', 'status',
                                          'used_licenses', 'total_licenses'])

total_permissionset_licenses_gauge = Gauge('salesforce_total_permissionset_licenses',
                                           TOTAL_LICENSES, ['license_name', 'status'])
used_permissionset_licenses_gauge = Gauge('salesforce_used_permissionset_licenses',
                                          USED_LICENSES, ['license_name', 'status'])
percent_permissionset_used_gauge = Gauge('salesforce_permissionset_license_usage_percentage',
                                         USED_LICENSES_PERCENTAGE,
                                         ['license_name', 'status', 'used_licenses',
                                          'total_licenses', 'expiration_date'])

total_usage_based_entitlements_licenses_gauge = Gauge('salesforce_total_licenses_usage_based_entitlements',
                                                      TOTAL_LICENSES, ['license_name'])
used_usage_based_entitlements_licenses_gauge = Gauge('salesforce_used_licenses_usage_based_entitlements',
                                                     USED_LICENSES, ['license_name'])
percent_usage_based_entitlements_used_gauge = Gauge('salesforce_percent_used_usage_based_entitlements',
                                                    USED_LICENSES_PERCENTAGE,
                                                    ['license_name', 'used_licenses',
                                                     'total_licenses', 'expiration_date'])

incident_gauge = Gauge('salesforce_incidents',
                       'Number of active Salesforce incidents',
                       ['pod', 'severity', 'message'])
login_count_gauge = Gauge('salesforce_login_count',
                          'Number of logins',
                          ['geohash', 'latitude', 'longitude'])

deployment_details_gauge = Gauge('deployment_details',
                                 'Salesforce Deployment details',
                                 ['pending_time', 'deployment_time',
                                  'deployed_by', 'status', 'deployment_id'])
pending_time_gauge = Gauge('deployment_pending_time',
                           'Pending time before starting the deployment',
                           ['deployment_id', 'deployed_by', 'status'])
deployment_time_gauge = Gauge('deployment_time',
                              'Time taken for the deployment',
                              ['deployment_id', 'deployed_by', 'status'])

ept_metric = Gauge('salesforce_experienced_page_time',
                   'Experienced Page Time (EPT) in seconds',
                   ['EFFECTIVE_PAGE_TIME_DEVIATION_REASON',
                    'EFFECTIVE_PAGE_TIME_DEVIATION_ERROR_TYPE',
                    'PREVPAGE_ENTITY_TYPE', 'PREVPAGE_APP_NAME',
                    'PAGE_ENTITY_TYPE', 'PAGE_APP_NAME', 'BROWSER_NAME'])

login_success_gauge = Gauge('salesforce_login_success_total',
                            'Total number of successful Salesforce logins')
login_failure_gauge = Gauge('salesforce_login_failure_total',
                            'Total number of failed Salesforce logins')

geolocation_gauge = Gauge('user_location',
                          'Longitude and Latitude of user location',
                          ['user', 'longitude', 'latitude', 'browser', 'status'])

async_job_status_gauge = Gauge('salesforce_async_job_status_count',
                               'Total count of Salesforce Async Jobs by Status',
                               ['status', 'method', 'job_type', 'number_of_errors'])

run_time_metric = Gauge('salesforce_apex_run_time_seconds',
                        'Total Apex execution time', 
                        ['entry_point', 'quiddity'])
cpu_time_metric = Gauge('salesforce_apex_cpu_time_seconds',
                        'CPU time used by Apex execution', 
                        ['entry_point', 'quiddity'])
exec_time_metric = Gauge('salesforce_apex_execution_time_seconds',
                         'Total execution time',
                         ['entry_point', 'quiddity'])
db_total_time_metric = Gauge('salesforce_apex_db_total_time_seconds',
                             'Total database execution time',
                             ['entry_point', 'quiddity'])
callout_time_metric = Gauge('salesforce_apex_callout_time_seconds',
                            'Total callout time',
                            ['entry_point', 'quiddity'])
long_running_requests_metric = Gauge('salesforce_apex_long_running_requests_total',
                                     'Number of long-running requests',
                                     ['entry_point', 'quiddity'])

apex_exception_details_gauge = Gauge('apex_exception_details',
                                     'Details of each Apex exception', 
                                     ['request_id', 'exception_category',
                                      'exception_type', 'exception_message',
                                      'stack_trace'])
apex_exception_category_count_gauge = Gauge('apex_exception_category_count',
                                            'Total count of Apex exceptions by category',
                                            ['exception_category'])
