"""
    Define all Prometheus gauges.
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

daily_batch_count_metric = Gauge('daily_bulk_api_batch_count',
                           'Count of batches by job_id, user_id, and entity_type', 
                           ['job_id', 'user_id', 'entity_type',
                            'total_records_failed', 'total_records_processed'])

daily_entity_type_count_metric = Gauge('daily_entity_type_count',
                                'Counts of ENTITY_TYPE by user_id and OPERATION_TYPE',
                                ['user_id', 'operation_type', 'entity_type'])

hourly_batch_count_metric = Gauge('hourly_bulk_api_batch_count',
                           'Count of batches by job_id, user_id, and entity_type', 
                           ['job_id', 'user_id', 'entity_type',
                            'total_records_failed', 'total_records_processed'])

hourly_entity_type_count_metric = Gauge('hourly_entity_type_count',
                                'Counts of ENTITY_TYPE by user_id and OPERATION_TYPE',
                                ['user_id', 'operation_type', 'entity_type'])

total_user_licenses_gauge = Gauge('salesforce_total_user_licenses',
                                  TOTAL_LICENSES, ['license_name', 'status'])
used_user_licenses_gauge = Gauge('salesforce_used_user_licenses',
                                 USED_LICENSES, ['license_name', 'status'])
percent_user_licenses_used_gauge = Gauge('salesforce_user_licenses_usage_percentage',
                                         USED_LICENSES_PERCENTAGE,
                                         ['license_name', 'status',
                                          'used_licenses', 'total_licenses'])

total_permissionset_licenses_gauge = Gauge('salesforce_total_permissionset_licenses',
                                           TOTAL_LICENSES,
                                           ['license_name', 'status'])
used_permissionset_licenses_gauge = Gauge('salesforce_used_permissionset_licenses',
                                          USED_LICENSES,
                                          ['license_name', 'status'])
percent_permissionset_used_gauge = Gauge('salesforce_permissionset_license_usage_percentage',
                                         USED_LICENSES_PERCENTAGE,
                                         ['license_name', 'status',
                                          'used_licenses', 'total_licenses', 'expiration_date'])

total_usage_based_entitlements_licenses_gauge = Gauge('salesforce_total_licenses_usage_based_entitlements',
                                                      TOTAL_LICENSES,
                                                      ['license_name'])
used_usage_based_entitlements_licenses_gauge = Gauge('salesforce_used_licenses_usage_based_entitlements',
                                                     USED_LICENSES,
                                                     ['license_name'])
percent_usage_based_entitlements_used_gauge = Gauge('salesforce_percent_used_usage_based_entitlements',
                                                    USED_LICENSES_PERCENTAGE,
                                                    ['license_name', 'used_licenses',
                                                     'total_licenses', 'expiration_date'])

incident_gauge = Gauge('salesforce_incidents',
                       'Number of active Salesforce incidents',
                       ['environment', 'pod', 'severity',
                        'message', 'original_message'])

maintenance_gauge = Gauge('salesforce_maintenance', 'Ongoing or Planned Salesforce Maintenance',
                          ['environment', 'maintenance_id', 'status',
                           'planned_start_time', 'planned_end_time'])

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

validation_details_gauge = Gauge('validation_details',
                                 'Salesforce Validation Deployment details',
                                 ['pending_time', 'deployment_time',
                                  'deployed_by', 'status', 'deployment_id'])
validation_pending_time_gauge = Gauge('validation_pending_time',
                           'Pending time before starting the validation',
                           ['deployment_id', 'deployed_by', 'status'])
validation_time_gauge = Gauge('validation_time',
                              'Time taken for the validation',
                              ['deployment_id', 'deployed_by', 'status'])

ept_metric = Gauge('salesforce_experienced_page_time',
                   'Experienced Page Time (EPT) in seconds', 
                   ['EFFECTIVE_PAGE_TIME_DEVIATION_REASON',
                    'EFFECTIVE_PAGE_TIME_DEVIATION_ERROR_TYPE',
                    'PREVPAGE_ENTITY_TYPE', 'PREVPAGE_APP_NAME', 'PAGE_ENTITY_TYPE',
                    'PAGE_APP_NAME', 'BROWSER_NAME'])

apt_metric = Gauge('salesforce_average_page_time',
                   'Average Page Time (APT) in seconds',
                   ['Page_name'])

login_success_gauge = Gauge('salesforce_login_success_total',
                            'Total number of successful Salesforce logins')

login_failure_gauge = Gauge('salesforce_login_failure_total',
                            'Total number of failed Salesforce logins')

unique_login_attempts_guage = Gauge('unique_login_count_total',
                            'Total number of Unique Salesforce logins')

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

top_apex_concurrent_errors_sorted_by_avg_runtime = Gauge('most_apex_concurrent_errors_sorted_by_runtime',
                                                         'Top Long Running Requests by Average Runtime with Runtime > 5 seconds',
                                                         ['entry_point', 'count',
                                                          'avg_exec_time', 'avg_db_time'])

top_apex_concurrent_errors_sorted_by_count = Gauge('most_apex_concurrent_errors_sorted_by_count',
                                                         'Top Long Running Requests by Count with Runtime > 5 seconds',
                                                         ['entry_point', 'avg_run_time',
                                                          'avg_exec_time', 'avg_db_time'])

concurrent_errors_count_gauge =  Gauge('concurrent_request_error_count',
                                       'Count of non-blank REQUEST_ID entries in CSV file',
                                       ['event_type'])

apex_exception_details_gauge = Gauge('apex_exception_details',
                                     'Details of each Apex exception',
                                     ['request_id', 'exception_category', 'timestamp',
                                      'exception_type', 'exception_message', 'stack_trace'])
apex_exception_category_count_gauge = Gauge('apex_exception_category_count',
                                            'Total count of Apex exceptions by category',
                                            ['exception_category'])

hourly_large_query_metric = Gauge('hourly_user_querying_large_records',
                                  'Number of large queries by user',
                           ['user_id', 'user_name', 'method', 'entity_name', 'rows_processed'])

community_login_error_metric = Gauge('community_login_error_details',
                                     'Details of SFDC logger entries', 
                                     ['id', 'name', 'log_level', 'log_message',
                                      'record_id', 'created_date'])

community_registration_error_metric = Gauge('community_registration_error_details',
                                            'Details of SFDC logger entries',
                                            ['id', 'name', 'source_name', 'log_level',
                                             'log_message', 'callout_response',
                                             'record_id', 'created_date'])
unused_permissionsets = Gauge('unused_permissionsets',
                                            'unused permissionsets',
                                            ['name', 'id'])
limited_permissionsets = Gauge('limited_permissionsets',
                                            'Permission sets assigned to 10 or less active users.',
                                            ['name', 'id'])
five_or_less_profile_assignees = Gauge('five_or_less_profile_assignees',
                                            'five_or_less_profile_assignees',
                                            ['profileId', 'profileName'])

unassigned_profiles = Gauge('unassigned_profiles',
                                            'Profiles with no active users.',
                                            ['profileId', 'profileName'])
apex_flex_queue = Gauge('apex_flex_queue',
                                            'Jobs in holding status flex queue',
                                            ['id','ApexClassId'])
deprecated_apex_class_gauge = Gauge('deprecated_apex_classes',
                                            'Apex classes running on deprecated API versions.',
                                            ['id', 'name'])

apex_entry_point_count = Gauge('apex_entry_point_count',
                               'Count of apex executions by entry point',
                               ['entry_point', 'quiddity'])
apex_avg_runtime = Gauge('apex_avg_runtime',
                         'Average runtime by entry point',
                         ['entry_point', 'quiddity'])
apex_max_runtime = Gauge('apex_max_runtime',
                         'Maximum runtime by entry point',
                         ['entry_point', 'quiddity'])
apex_total_runtime = Gauge('apex_total_runtime',
                           'Total runtime by entry point',
                           ['entry_point', 'quiddity'])
apex_avg_cputime = Gauge('apex_avg_cputime',
                         'Average CPU time by entry point',
                         ['entry_point', 'quiddity'])
apex_max_cputime = Gauge('apex_max_cputime',
                         'Maximum CPU time by entry point',
                         ['entry_point', 'quiddity'])
apex_runtime_gt_5s_count = Gauge('apex_runtime_gt_5s_count',
                                 'Count of apex executions with runtime > 5s', 
                                 ['entry_point', 'quiddity'])
apex_runtime_gt_10s_count = Gauge('apex_runtime_gt_10s_count',
                                  'Count of apex executions with runtime > 10s',
                                  ['entry_point', 'quiddity'])
apex_runtime_gt_5s_percentage = Gauge('apex_runtime_gt_5s_percentage',
                                      'Percentage of apex executions with runtime > 5s',
                                      ['entry_point', 'quiddity'])

org_wide_sharing__setting_changes = Gauge('org_wide_sharing_changes',
                                          'Track changes in Org-Wide Sharing Settings',
                                          ['date', 'user', 'action', 'display'])

hourly_report_export_metric = Gauge('hourly_report_export', 'Report export details',
                           ['user_name', 'timestamp', 'report_name', 'report_type_api_name'])

suspicious_records_gauge = Gauge('suspicious_records','suspicious records from Audit Trail logs',
                                ['action', 'section', 'user',
                                 'created_date', 'display', 'delegate_user'])
