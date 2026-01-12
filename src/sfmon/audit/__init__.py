"""
Audit and Compliance Monitoring Package

This package contains modules for monitoring audit and compliance activities
in the Salesforce org, including:
- Large query monitoring (hourly_observe_user_querying_large_records)
- Forbidden profile detection (monitor_forbidden_profile_assignments)
- Audit trail analysis (expose_suspicious_records)
- Org-wide sharing settings (monitor_org_wide_sharing_settings)
- Deployment status tracking (get_deployment_status)
- User login and geolocation monitoring
- Report export tracking (hourly_report_export_records)

Optional grouped functions (for convenience):
- run_hourly_audit: Runs large queries + forbidden profiles checks
- run_daily_audit: Runs all daily audit checks together
"""
import sys
import os

# Add parent directory to path for importing shared modules
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# Re-export main functions for clean imports
from .audit import run_hourly_audit, run_daily_audit
from .large_queries import hourly_observe_user_querying_large_records
from .audit_trail import expose_suspicious_records
from .sharing_settings import monitor_org_wide_sharing_settings
from .forbidden_profiles import monitor_forbidden_profile_assignments
from .deployments import get_deployment_status
from .user_login import monitor_login_events, geolocation
from .utils import get_user_name, categorize_user_group
from .report_export import hourly_report_export_records

__all__ = [
    # Main entry points
    'run_hourly_audit',
    'run_daily_audit',
    # Individual functions
    'hourly_observe_user_querying_large_records',
    'expose_suspicious_records',
    'monitor_org_wide_sharing_settings',
    'monitor_forbidden_profile_assignments',
    'get_deployment_status',
    'monitor_login_events',
    'geolocation',
    # Utilities
    'get_user_name',
    'categorize_user_group',
    # Report exports
    'hourly_report_export_records',
]
