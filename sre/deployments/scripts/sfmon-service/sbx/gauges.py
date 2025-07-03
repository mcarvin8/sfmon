"""
    Define all Prometheus gauges.
"""
from prometheus_client import Gauge
from constants import EMAIL_DELIVERABILITY_STR

# Prometheus metrics
incident_gauge = Gauge('salesforce_incidents',
                       'Number of active Salesforce incidents',
                       ['environment', 'pod', 'severity',
                        'message', 'original_message'])

maintenance_gauge = Gauge('salesforce_maintenance', 'Ongoing or Planned Salesforce Maintenance',
                          ['environment', 'maintenance_id', 'status',
                           'planned_start_time', 'planned_end_time'])

dev_email_deliverability_change_gauge = Gauge('dev_email_deliverability_change',
                                              EMAIL_DELIVERABILITY_STR,
                                                ['action', 'section', 'user',
                                                 'created_date', 'display', 'delegate_user'])

fullqa_email_deliverability_change_gauge = Gauge('fullqa_email_deliverability_change',
                                                 EMAIL_DELIVERABILITY_STR,
                                                ['action', 'section', 'user',
                                                 'created_date', 'display', 'delegate_user'])

fullqab_email_deliverability_change_gauge = Gauge('fullqab_email_deliverability_change',
                                                  EMAIL_DELIVERABILITY_STR,
                                                ['action', 'section', 'user',
                                                 'created_date', 'display', 'delegate_user'])

valid_contact_detail_gauge = Gauge(
    "salesforce_valid_contact_detail",
    "Details of valid contacts by ID and Email",
    ["org", "contact_id", "email"]
)

payment_method_status_gauge = Gauge('payment_method_status', 'Payment Methods Status',
                                    ['billing_active_status', 'billing_autopay_status',
                                     'billing_payment_gateway_name',
                                    'payment_gateway_token', 'payment_method_id',
                                    'payment_method_name', 'user_name', 'last_modified_date'])

payment_gateway_status_gauge = Gauge('payment_gateway_status', 'Payment Gateways Status',
                                    ['billing_active_status', 'billing_default_status',
                                     'billing_gateway_type',
                                    'payment_gateway_name', 'record_id',
                                    'user_name', 'last_modified_date'])

payment_method_status_gauge_fqab = Gauge('payment_method_status_fqab', 'Payment Methods Status',
                                    ['billing_active_status', 'billing_autopay_status',
                                     'billing_payment_gateway_name',
                                    'payment_gateway_token', 'payment_method_id',
                                    'payment_method_name', 'user_name', 'last_modified_date'])

payment_gateway_status_gauge_fqab = Gauge('payment_gateway_status_fqab', 'Payment Gateways Status',
                                    ['billing_active_status', 'billing_default_status',
                                     'billing_gateway_type',
                                    'payment_gateway_name', 'record_id',
                                    'user_name', 'last_modified_date'])
