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

# Re-export main functions for clean imports
from .code_quality import (
    apex_classes_api_version,
    apex_triggers_api_version,
    apex_used_limits_monitoring,
    workflow_rules_monitoring,
)
from .dashboards import dashboards_with_inactive_users
from .permissions import (
    monitor_minimal_perm_sets,
    perm_sets_limited_users,
    profile_assignment_under5,
    profile_no_active_users,
    unassigned_permission_sets,
)
from .pmd import monitor_pmd_code_smells
from .queues_groups import (
    public_groups_with_no_members,
    queues_with_no_members,
    queues_with_zero_open_cases,
    total_queues_per_object,
)
from .scheduled_jobs import scheduled_apex_jobs_monitoring
from .security import salesforce_health_risks, security_health_check
from .users import dormant_portal_users, dormant_salesforce_users

__all__ = [
    # Code quality
    "apex_classes_api_version",
    "apex_triggers_api_version",
    "workflow_rules_monitoring",
    "apex_used_limits_monitoring",
    # Permissions
    "unassigned_permission_sets",
    "perm_sets_limited_users",
    "profile_assignment_under5",
    "profile_no_active_users",
    "monitor_minimal_perm_sets",
    # Security
    "security_health_check",
    "salesforce_health_risks",
    # Users
    "dormant_salesforce_users",
    "dormant_portal_users",
    # Queues & Groups
    "total_queues_per_object",
    "queues_with_no_members",
    "queues_with_zero_open_cases",
    "public_groups_with_no_members",
    # Dashboards
    "dashboards_with_inactive_users",
    # Scheduled jobs
    "scheduled_apex_jobs_monitoring",
    # PMD
    "monitor_pmd_code_smells",
]
