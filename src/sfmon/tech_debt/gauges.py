"""Prometheus metric definitions for tech debt monitoring."""

from org_gauge import OrgAwareGauge

# Permission Sets
unused_permissionsets = OrgAwareGauge(
    "unused_permissionsets",
    "Permission sets not assigned to any users or groups",
    ["name", "id"],
)
limited_permissionsets = OrgAwareGauge(
    "limited_permissionsets",
    "Permission sets assigned to limited active users (threshold configurable via PERMSET_LIMITED_USERS_THRESHOLD)",
    ["name", "id"],
)

# Profiles
five_or_less_profile_assignees = OrgAwareGauge(
    "five_or_less_profile_assignees",
    "Profiles with limited assignees (threshold configurable via PROFILE_UNDER_USERS_THRESHOLD)",
    ["profileId", "profileName"],
)
unassigned_profiles = OrgAwareGauge(
    "unassigned_profiles", "Profiles with no active users", ["profileId", "profileName"]
)

# Code Quality - API Versions and Apex
deprecated_apex_class_gauge = OrgAwareGauge(
    "deprecated_apex_classes",
    "Apex classes running on deprecated API versions (threshold configurable via DEPRECATED_API_VERSION)",
    ["id", "name"],
)
deprecated_apex_trigger_gauge = OrgAwareGauge(
    "deprecated_apex_triggers",
    "Apex triggers running on deprecated API versions (threshold configurable via DEPRECATED_API_VERSION)",
    ["id", "name"],
)
apex_class_length_without_comments_gauge = OrgAwareGauge(
    "apex_class_length_without_comments",
    "Apex class character count excluding comments (Apex Used Limits). Custom classes only.",
    ["id", "name", "is_test"],
)
apex_trigger_length_without_comments_gauge = OrgAwareGauge(
    "apex_trigger_length_without_comments",
    "Apex trigger character count excluding comments (Apex Used Limits). Custom triggers only.",
    ["id", "name", "is_test"],
)
apex_character_limit_percentage_gauge = OrgAwareGauge(
    "apex_character_limit_percentage",
    "Percentage of Apex character limit (6M) used. Custom classes/triggers only, excludes @isTest classes.",
    [],
)

# Code Quality - Workflow Rules
workflow_rules_gauge = OrgAwareGauge(
    "workflow_rules",
    "Workflow rules in the org",
    ["id", "created_date", "namespace_prefix"],
)

# Security
security_health_check_gauge = OrgAwareGauge(
    "security_health_check_score", "Salesforce Security Health Check Score", ["grade"]
)
salesforce_health_risks_gauge = OrgAwareGauge(
    "salesforce_health_risks",
    "Salesforce Security Health Check Risks",
    [
        "org_value",
        "risk_type",
        "setting",
        "setting_group",
        "setting_risk_category",
        "standard_value",
        "compliance_status",
    ],
)

# Users
dormant_salesforce_users_gauge = OrgAwareGauge(
    "dormant_salesforce_users",
    "Dormant Salesforce users (threshold configurable via DORMANT_USER_DAYS)",
    ["user_id", "username", "email", "profile_name", "created_date", "last_login_date"],
)
dormant_portal_users_gauge = OrgAwareGauge(
    "dormant_portal_users",
    "Dormant Portal users (threshold configurable via DORMANT_USER_DAYS)",
    ["user_id", "username", "email", "profile_name", "created_date", "last_login_date"],
)

# Queues
total_queues_per_object_gauge = OrgAwareGauge(
    "total_queues_per_object", "Total queues per Salesforce object", ["sobject_type"]
)
queues_with_no_members_gauge = OrgAwareGauge(
    "queues_with_no_members", "Queues with no members", ["queue_id", "queue_name"]
)
queues_with_zero_open_cases_gauge = OrgAwareGauge(
    "queues_with_zero_open_cases",
    "Queues that can own Cases but have zero open Cases",
    ["queue_id", "queue_name"],
)

# Public Groups
public_groups_with_no_members_gauge = OrgAwareGauge(
    "public_groups_with_no_members",
    "Public Groups with no members",
    ["group_id", "group_name"],
)

# Dashboards
dashboards_with_inactive_users_gauge = OrgAwareGauge(
    "dashboards_with_inactive_users",
    "Dashboards with inactive running users",
    [
        "dashboard_id",
        "dashboard_title",
        "running_user_name",
        "created_date",
        "last_referenced_date",
    ],
)

# Scheduled Jobs
scheduled_apex_jobs_gauge = OrgAwareGauge(
    "scheduled_apex_jobs",
    "Scheduled Apex jobs in the org",
    [
        "job_id",
        "job_name",
        "cron_expression",
        "state",
        "next_fire_time",
        "previous_fire_time",
        "created_by",
        "created_date",
    ],
)

# PMD and Minimal Permission Sets
pmd_code_smells_gauge = OrgAwareGauge(
    "pmd_code_smells",
    "PMD code smells in the org",
    ["rule_name"],
)
pmd_apex_violations_gauge = OrgAwareGauge(
    "pmd_apex_violations",
    "PMD violations per Apex class/trigger broken down by rule, with comma-separated start lines",
    ["apex_name", "rule_name", "start_lines"],
)
minimal_permission_sets_gauge = OrgAwareGauge(
    "minimal_permission_sets",
    "Permission sets with 5 or fewer permissions",
    ["permission_set_name", "file_path", "permission_count"],
)
minimal_permission_sets_percentage_gauge = OrgAwareGauge(
    "minimal_permission_sets_percentage",
    "Percentage of minimal permission sets over total custom permission sets",
    [],
)
