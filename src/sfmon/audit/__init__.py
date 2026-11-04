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

# Re-export main functions for clean imports
from .audit import run_daily_audit, run_hourly_audit
from .audit_trail import expose_suspicious_records
from .deployments import get_deployment_status
from .forbidden_profiles import monitor_forbidden_profile_assignments
from .large_queries import hourly_observe_user_querying_large_records
from .report_export import hourly_report_export_records
from .sharing_settings import monitor_org_wide_sharing_settings
from .user_login import geolocation, monitor_login_events
from .utils import categorize_user_group, get_user_name

__all__ = [
    # Main entry points
    "run_hourly_audit",
    "run_daily_audit",
    # Individual functions
    "hourly_observe_user_querying_large_records",
    "expose_suspicious_records",
    "monitor_org_wide_sharing_settings",
    "monitor_forbidden_profile_assignments",
    "get_deployment_status",
    "monitor_login_events",
    "geolocation",
    # Utilities
    "get_user_name",
    "categorize_user_group",
    # Report exports
    "hourly_report_export_records",
]
