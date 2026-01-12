"""
Technical Debt Monitoring Package

This package contains modules for monitoring technical debt in the Salesforce org,
including:
- Code quality (Apex API versions, workflow rules, PMD analysis)
- Permission sets and profiles management
- Security health checks
- User management (dormant users)
- Queue and group management
- Dashboard management
- Scheduled Apex jobs

Main monitoring functions are re-exported for clean imports.
"""
import sys
import os

# Add parent directory to path for importing shared modules
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# Re-export main functions for clean imports
from .code_quality import (
    apex_classes_api_version,
    apex_triggers_api_version,
    workflow_rules_monitoring
)
from .permissions import (
    unassigned_permission_sets,
    perm_sets_limited_users,
    profile_assignment_under5,
    profile_no_active_users
)
from .security import (
    security_health_check,
    salesforce_health_risks
)
from .users import (
    dormant_salesforce_users,
    dormant_portal_users
)
from .queues_groups import (
    total_queues_per_object,
    queues_with_no_members,
    queues_with_zero_open_cases,
    public_groups_with_no_members
)
from .dashboards import dashboards_with_inactive_users
from .scheduled_jobs import scheduled_apex_jobs_monitoring

__all__ = [
    # Code quality
    'apex_classes_api_version',
    'apex_triggers_api_version',
    'workflow_rules_monitoring',
    # Permissions
    'unassigned_permission_sets',
    'perm_sets_limited_users',
    'profile_assignment_under5',
    'profile_no_active_users',
    # Security
    'security_health_check',
    'salesforce_health_risks',
    # Users
    'dormant_salesforce_users',
    'dormant_portal_users',
    # Queues & Groups
    'total_queues_per_object',
    'queues_with_no_members',
    'queues_with_zero_open_cases',
    'public_groups_with_no_members',
    # Dashboards
    'dashboards_with_inactive_users',
    # Scheduled jobs
    'scheduled_apex_jobs_monitoring',
]
