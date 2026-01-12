"""
Ops (Operations) Monitoring Package

This package contains modules for operational monitoring of the Salesforce org,
including:
- Salesforce org limits and API usage
- Apex execution, errors, and flex queue
- Bulk API operations (daily and hourly)
- EPT/APT performance metrics
- Organization status and incidents

Main monitoring functions are re-exported for clean imports.
"""
import sys
import os

# Add parent directory to path for importing shared modules
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# Re-export main functions for clean imports
from .apex_flex_queue import monitor_apex_flex_queue
from .apex_jobs import (
    async_apex_job_status,
    monitor_apex_execution_time,
    expose_apex_exception_metrics,
    concurrent_apex_errors,
    expose_concurrent_long_running_apex_errors,
    async_apex_execution_summary
)
from .bulk_api import daily_analyse_bulk_api, hourly_analyse_bulk_api
from .overall_sf_org import (
    monitor_salesforce_limits,
    get_salesforce_licenses,
    get_salesforce_instance
)
from .ept_apt import get_salesforce_ept_and_apt
from .limits import salesforce_limits_descriptions

__all__ = [
    # Apex monitoring
    'monitor_apex_flex_queue',
    'async_apex_job_status',
    'monitor_apex_execution_time',
    'expose_apex_exception_metrics',
    'concurrent_apex_errors',
    'expose_concurrent_long_running_apex_errors',
    'async_apex_execution_summary',
    # Bulk API
    'daily_analyse_bulk_api',
    'hourly_analyse_bulk_api',
    # Org-level monitoring
    'monitor_salesforce_limits',
    'get_salesforce_licenses',
    'get_salesforce_instance',
    # Performance
    'get_salesforce_ept_and_apt',
    # Utilities
    'salesforce_limits_descriptions',
]
