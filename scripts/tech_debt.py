"""
Technical Debt Monitoring Functions Module

This module contains all individual monitoring functions for identifying and tracking
technical debt in the Salesforce production org. Each function focuses on a specific
category of technical debt or code quality metric.

Monitoring Categories:

1. Permission Sets & Profiles:
    - unassigned_permission_sets: Permission sets with zero assignments
    - perm_sets_limited_users: Permission sets assigned to ≤10 users
    - profile_assignment_under5: Profiles with ≤5 active user assignments
    - profile_no_active_users: Profiles with zero active users
    - monitor_useless_permission_sets: Permission sets with no actual permissions

2. Code Quality & API Versions:
    - apex_classes_api_version: Local Apex classes on API v50 or below
    - apex_triggers_api_version: Local Apex triggers on API v50 or below
    - workflow_rules_monitoring: Legacy workflow rules inventory
    - monitor_pmd_code_smells: PMD static analysis violations from XML report

3. Security & Health:
    - security_health_check: Salesforce Security Health Check score and grade
    - salesforce_health_risks: Detailed security risks and misconfigurations

4. User Management:
    - dormant_salesforce_users: Salesforce licensed users inactive 90+ days
    - dormant_portal_users: Portal/Community users inactive 90+ days

5. Queue & Group Management:
    - total_queues_per_object: Queue distribution across objects
    - queues_with_no_members: Empty queues without assigned users
    - queues_with_zero_open_cases: Case queues with no open cases
    - public_groups_with_no_members: Public groups without members

6. Dashboard Management:
    - dashboards_with_inactive_users: Dashboards with inactive running users

Data Sources:
    - Standard Salesforce objects (PermissionSet, Profile, User, Queue, Group, Dashboard)
    - Tooling API (SecurityHealthCheck, SecurityHealthCheckRisks, WorkflowRule)
    - Local file reports (pmd-report.xml, useless-permission-sets-report.json)

All functions follow a consistent pattern:
    1. Clear existing Prometheus gauge
    2. Query Salesforce or parse local reports
    3. Process results and expose as labeled metrics
    4. Log summary statistics
"""
import json
import os
import xml.etree.ElementTree as ET
from collections import defaultdict
from logger import logger
from gauges import (unused_permissionsets, five_or_less_profile_assignees,
                    unassigned_profiles, limited_permissionsets,
                    deprecated_apex_class_gauge, deprecated_apex_trigger_gauge,
                    security_health_check_gauge, salesforce_health_risks_gauge, 
                    workflow_rules_gauge, pmd_code_smells_gauge,
                    dormant_salesforce_users_gauge, dormant_portal_users_gauge,
                    total_queues_per_object_gauge, queues_with_no_members_gauge,
                    queues_with_zero_open_cases_gauge, public_groups_with_no_members_gauge,
                    useless_permission_sets_gauge, dashboards_with_inactive_users_gauge)
from query import query_records_all, tooling_query_records_all

def unassigned_permission_sets(sf):
    """
    Query permission sets developed by FTE which are not assigned to any active users.
    """
    try:
        logger.info("Querying unassigned permission sets...")
        query = """
        SELECT Id, Name
        FROM PermissionSet
        WHERE Id NOT IN (
            SELECT PermissionSetId
            FROM PermissionSetAssignment
        )
        AND Id NOT IN (
            SELECT PermissionSetId
            FROM PermissionSetGroupComponent
        )
        AND NamespacePrefix = NULL
        AND IsOwnedByProfile = FALSE

        """
        results = query_records_all(sf, query)
        # Clear existing Prometheus gauge labels
        unused_permissionsets.clear()

        for record in results:
            unused_permissionsets.labels(
                name=record['Name'],
                id=record['Id']
            ).set(0)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching unassigned permission sets: %s", e)

def perm_sets_limited_users(sf):
    """
    Query permission sets developed by FTE assigned to 10 or less active users
    """
    try:
        logger.info("Querying permission sets assigned to 10 or less active users...")
        query = """
        SELECT PermissionSet.Id, PermissionSet.Name, Count(ID)
        FROM PermissionSetAssignment
        where PermissionSetId NOT IN (
            SELECT PermissionSetId
            FROM PermissionSetGroupComponent
        )
        AND PermissionSet.NamespacePrefix = NULL  
        GROUP BY PermissionSet.Id, PermissionSet.Name
        HAVING COUNT(Id) <= 10
        """
        results = query_records_all(sf, query)
        # Clear existing Prometheus gauge labels
        limited_permissionsets.clear()

        for record in results:
            limited_permissionsets.labels(
                name=record['Name'],
                id=record['Id']
            ).set(int(record['expr0']))
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching permission sets assigned to 10 or less active users: %s", e)

def profile_assignment_under5(sf):
    """
    Query all profiles where 5 or less assignees.
    """
    try:
        logger.info("Querying all profiles with 5 or less assignees...")
        query = """
        SELECT ProfileId, Profile.Name, COUNT(Id) userCount
        FROM User
        WHERE IsActive = TRUE
        GROUP BY ProfileId, Profile.Name
        HAVING COUNT(Id) <= 5
        """
        results = query_records_all(sf, query)
        # Clear existing Prometheus gauge labels
        five_or_less_profile_assignees.clear()

        for record in results:
            five_or_less_profile_assignees.labels(
                profileId=record['ProfileId'],
                profileName=record['Name']
            ).set(int(record['userCount']))
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching profiles with under 5 assignees: %s", e)

def profile_no_active_users(sf):
    """
    Query all profiles with no active users.
    """
    try:
        logger.info("Querying all profiles with no active users...")
        query = """
        SELECT Name, Id
        FROM Profile
        WHERE Id NOT IN (
        SELECT ProfileId FROM User WHERE IsActive = TRUE
        )
        """
        results = query_records_all(sf, query)
        # Clear existing Prometheus gauge labels
        unassigned_profiles.clear()

        for record in results:
            unassigned_profiles.labels(
                profileId=record['Id'],
                profileName=record['Name']
            ).set(0)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching profiles with no active users: %s", e)

def apex_classes_api_version(sf):
    """
    Query all local apex classes running on outdated API versions.
    """
    try:
        logger.info("Querying all local apex classes running on outdated API versions...")
        query = """
        SELECT Id,Name,ApiVersion
        FROM ApexClass
        WHERE NamespacePrefix = null AND ApiVersion <= 50
        """
        results = query_records_all(sf, query)
        # Clear existing Prometheus gauge labels
        deprecated_apex_class_gauge.clear()

        for record in results:
            deprecated_apex_class_gauge.labels(
                id=record['Id'],
                name=record['Name']
            ).set(int(record['ApiVersion']))
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching local apex classes running on outdated API versions: %s", e)

def apex_triggers_api_version(sf):
    """
    Query all local apex triggers running on outdated API versions.
    """
    try:
        logger.info("Querying all local apex triggers running on outdated API versions...")
        query = """
        SELECT Id,Name,ApiVersion
        FROM ApexTrigger 
        WHERE NamespacePrefix = null AND ApiVersion <= 50
        """
        results = query_records_all(sf, query)
        # Clear existing Prometheus gauge labels
        deprecated_apex_trigger_gauge.clear()

        for record in results:
            deprecated_apex_trigger_gauge.labels(
                id=record['Id'],
                name=record['Name']
            ).set(int(record['ApiVersion']))
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching local apex triggers running on outdated API versions: %s", e)

def security_health_check(sf):
    """
    Query Salesforce Security Health Check score and grade.
    """
    try:
        logger.info("Querying Salesforce Security Health Check...")
        query = "Select Score, Id from SecurityHealthCheck"
        results = tooling_query_records_all(sf, query)

        # Clear existing Prometheus gauge labels
        security_health_check_gauge.clear()

        for record in results:
            score = int(record['Score'])

            # Determine grade based on score
            if score >= 90:
                grade = "Excellent"
            elif score >= 80:
                grade = "Very Good"
            elif score >= 70:
                grade = "Good"
            elif score >= 55:
                grade = "Poor"
            else:
                grade = "Very Poor"

            security_health_check_gauge.labels(grade=grade).set(score)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching Salesforce Security Health Check: %s", e)

def salesforce_health_risks(sf):
    """
    Query Salesforce Security Health Check Risks.
    """
    try:
        logger.info("Querying Salesforce Security Health Check Risks...")
        query = """Select Id, OrgValue, RiskType, Setting, SettingGroup, 
                   SettingRiskCategory, StandardValue, StandardValueRaw 
                   from SecurityHealthCheckRisks"""
        results = tooling_query_records_all(sf, query)
        
        # Clear existing Prometheus gauge labels
        salesforce_health_risks_gauge.clear()

        for record in results:
            org_value = record.get('OrgValue', '')
            standard_value = record.get('StandardValue', '')
            
            # Compare OrgValue and StandardValue to determine compliance status
            compliance_status = "match" if str(org_value) == str(standard_value) else "mismatch"
            
            salesforce_health_risks_gauge.labels(
                org_value=org_value,
                risk_type=record.get('RiskType', ''),
                setting=record.get('Setting', ''),
                setting_group=record.get('SettingGroup', ''),
                setting_risk_category=record.get('SettingRiskCategory', ''),
                standard_value=standard_value,
                compliance_status=compliance_status
            ).set(1)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching Salesforce Security Health Check Risks: %s", e)

def workflow_rules_monitoring(sf):
    """
    Query all workflow rules using the Tooling API and check their active status.
    """
    try:
        logger.info("Querying all workflow rules using Tooling API...")
        # First query to get all workflow rule IDs
        initial_query = """
        SELECT Id, CreatedDate, NamespacePrefix
        FROM WorkflowRule
        """
        results = tooling_query_records_all(sf, initial_query)
        # Clear existing Prometheus gauge labels
        workflow_rules_gauge.clear()

        for record in results:
            workflow_id = record['Id']
            created_date = record.get('CreatedDate', 'Unknown')
            namespace_prefix = record.get('NamespacePrefix', 'None') or 'None'
            
            # Add all workflow rules to the gauge with a numeric value
            workflow_rules_gauge.labels(
                id=workflow_id,
                created_date=created_date,
                namespace_prefix=namespace_prefix
            ).set(1)
            logger.debug("Added workflow rule to gauge: %s", workflow_id)
                
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching workflow rules: %s", e)

def monitor_pmd_code_smells():
    """
    Parse PMD XML report and set Prometheus gauge for code smells.
    Runs once daily to monitor tech debt from PMD static analysis.
    """
    try:
        logger.info("Monitoring PMD code smells from XML report...")
        
        # PMD report file is in the same directory as this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        pmd_file_path = os.path.join(script_dir, 'pmd-report.xml')
        
        if not os.path.exists(pmd_file_path):
            logger.warning("PMD report file not found at: %s", pmd_file_path)
            return
        
        logger.info("Found PMD report at: %s", pmd_file_path)
        
        # Parse the XML file
        tree = ET.parse(pmd_file_path)
        root = tree.getroot()
        
        # Count violations by rule name (code smell type)
        code_smell_counts = defaultdict(int)
        
        # PMD XML has a namespace, so we need to handle it properly
        # Extract namespace from root tag if present
        namespace = ''
        if root.tag.startswith('{'):
            namespace = root.tag.split('}')[0] + '}'
        
        # PMD XML structure: <pmd><file><violation rule="RuleName">
        for file_element in root.findall(f'{namespace}file'):
            for violation in file_element.findall(f'{namespace}violation'):
                rule_name = violation.get('rule', 'Unknown')
                code_smell_counts[rule_name] += 1
                logger.debug("Found violation: %s", rule_name)
        
        # Clear existing Prometheus gauge labels
        pmd_code_smells_gauge.clear()
        
        # Set gauge values for each code smell type
        total_violations = 0
        for code_smell, count in code_smell_counts.items():
            pmd_code_smells_gauge.labels(code_smell=code_smell).set(count)
            total_violations += count
            logger.debug("PMD Code Smell - %s: %d violations", code_smell, count)
        
        # Also set a total count gauge
        if total_violations > 0:
            pmd_code_smells_gauge.labels(code_smell='TOTAL').set(total_violations)
        
        logger.info("PMD monitoring completed. Total violations: %d, Unique code smells: %d", 
                   total_violations, len(code_smell_counts))
        
    # pylint: disable=broad-except
    except ET.ParseError as e:
        logger.error("Error parsing PMD XML report: %s", e)
    except FileNotFoundError as e:
        logger.error("PMD report file not found: %s", e)
    except Exception as e:
        logger.error("Error monitoring PMD code smells: %s", e)

def dormant_salesforce_users(sf):
    """
    Query dormant Salesforce users - active users whose accounts are at least 90 days old 
    and who either haven't logged in during the last 90 days or have never logged in.
    """
    try:
        logger.info("Querying dormant Salesforce users...")
        query = """
        SELECT Id, Name, CreatedDate, Username, Email, IsActive, LastLoginDate, Profile.Name
        FROM User
        WHERE IsActive = true
        AND Profile.UserLicense.Name = 'Salesforce'
        AND (LastLoginDate < LAST_N_DAYS:90 OR LastLoginDate = Null)
        AND CreatedDate < LAST_N_DAYS:90
        ORDER BY LastLoginDate ASC
        """
        results = query_records_all(sf, query)
        
        # Clear existing Prometheus gauge labels
        dormant_salesforce_users_gauge.clear()

        for record in results:
            # Handle null LastLoginDate
            last_login = record.get('LastLoginDate', 'Never')
            if last_login is None:
                last_login = 'Never'
            
            dormant_salesforce_users_gauge.labels(
                user_id=record['Id'],
                username=record['Username'],
                email=record['Email'],
                profile_name=record['Profile']['Name'],
                created_date=record['CreatedDate'],
                last_login_date=last_login
            ).set(1)
            
        logger.info("Found %d dormant Salesforce users", len(results))
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching dormant Salesforce users: %s", e)

def dormant_portal_users(sf):
    """
    Query dormant Portal users - active users whose accounts are at least 90 days old 
    and who either haven't logged in during the last 90 days or have never logged in.
    """
    try:
        logger.info("Querying dormant Portal users...")
        query = """
        SELECT Id, Name, CreatedDate, Username, Email, IsActive, LastLoginDate, Profile.Name
        FROM User
        WHERE IsActive = true
        AND Profile.UserLicense.Name != 'Salesforce'
        AND (LastLoginDate < LAST_N_DAYS:90 OR LastLoginDate = Null)
        AND CreatedDate < LAST_N_DAYS:90
        ORDER BY LastLoginDate ASC
        """
        results = query_records_all(sf, query)
        
        # Clear existing Prometheus gauge labels
        dormant_portal_users_gauge.clear()

        for record in results:
            # Handle null LastLoginDate
            last_login = record.get('LastLoginDate', 'Never')
            if last_login is None:
                last_login = 'Never'
            
            dormant_portal_users_gauge.labels(
                user_id=record['Id'],
                username=record['Username'],
                email=record['Email'],
                profile_name=record['Profile']['Name'],
                created_date=record['CreatedDate'],
                last_login_date=last_login
            ).set(1)
            
        logger.info("Found %d dormant Portal users", len(results))
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching dormant Portal users: %s", e)

def total_queues_per_object(sf):
    """
    Query total queues per Salesforce object to identify queue distribution.
    """
    try:
        logger.info("Querying total queues per object...")
        query = """
        SELECT SobjectType, COUNT_DISTINCT(QueueId)
        FROM QueueSobject
        GROUP BY SobjectType
        ORDER BY COUNT_DISTINCT(QueueId) DESC
        """
        results = query_records_all(sf, query)
        
        # Clear existing Prometheus gauge labels
        total_queues_per_object_gauge.clear()

        for record in results:
            total_queues_per_object_gauge.labels(
                sobject_type=record['SobjectType']
            ).set(int(record['expr0']))
            
        logger.info("Found queues for %d different object types", len(results))
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching total queues per object: %s", e)

def queues_with_no_members(sf):
    """
    Query queues that have no members assigned to them.
    """
    try:
        logger.info("Querying queues with no members...")
        query = """
        SELECT Id, Name
        FROM Group
        WHERE Type = 'Queue'
        AND Id NOT IN (SELECT GroupID FROM GroupMember)
        """
        results = query_records_all(sf, query)
        
        # Clear existing Prometheus gauge labels
        queues_with_no_members_gauge.clear()

        for record in results:
            queues_with_no_members_gauge.labels(
                queue_id=record['Id'],
                queue_name=record['Name']
            ).set(1)
            
        logger.info("Found %d queues with no members", len(results))
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching queues with no members: %s", e)

def queues_with_zero_open_cases(sf):
    """
    Query queues that can own Cases but have zero open Cases.
    """
    try:
        logger.info("Querying queues with zero open cases...")
        query = """
        SELECT Id, Name
        FROM Group
        WHERE Type = 'Queue'
        AND Id IN (
          SELECT QueueId FROM QueueSobject WHERE SobjectType = 'Case'
        )
        AND Id NOT IN (
          SELECT OwnerId FROM Case WHERE IsClosed = false
        )
        """
        results = query_records_all(sf, query)
        
        # Clear existing Prometheus gauge labels
        queues_with_zero_open_cases_gauge.clear()

        for record in results:
            queues_with_zero_open_cases_gauge.labels(
                queue_id=record['Id'],
                queue_name=record['Name']
            ).set(1)
            
        logger.info("Found %d queues with zero open cases", len(results))
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching queues with zero open cases: %s", e)

def public_groups_with_no_members(sf):
    """
    Query dormant Public Groups with no members.
    """
    try:
        logger.info("Querying public groups with no members...")
        query = """
        SELECT Id, Name
        FROM Group
        WHERE Type = 'Regular'
        AND Id NOT IN (SELECT GroupId FROM GroupMember)
        ORDER BY Name
        """
        results = query_records_all(sf, query)
        
        # Clear existing Prometheus gauge labels
        public_groups_with_no_members_gauge.clear()

        for record in results:
            public_groups_with_no_members_gauge.labels(
                group_id=record['Id'],
                group_name=record['Name']
            ).set(1)
            
        logger.info("Found %d public groups with no members", len(results))
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching public groups with no members: %s", e)

def monitor_useless_permission_sets():
    """
    Parse useless permission sets report and set Prometheus gauge.
    Runs once daily to monitor tech debt from permission set analysis.
    Similar to PMD code smells monitoring - reads from a pre-generated report file.
    """
    try:
        logger.info("Monitoring useless permission sets from report file...")
        
        # Report file is in the same directory as this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        report_file_path = os.path.join(script_dir, 'useless-permission-sets-report.json')
        
        if not os.path.exists(report_file_path):
            logger.warning("Useless permission sets report file not found at: %s", report_file_path)
            logger.info("This file should be generated by a scheduled pipeline that retrieves metadata from production")
            return
        
        logger.info("Found useless permission sets report at: %s", report_file_path)
        
        # Clear existing Prometheus gauge labels
        useless_permission_sets_gauge.clear()
        
        # Read and parse the JSON report
        
        with open(report_file_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
        
        # Expected JSON structure:
        # {
        #   "scan_date": "2024-01-01T00:00:00Z",
        #   "total_permission_sets": 672,
        #   "useless_permission_sets": [
        #     {
        #       "name": "Permission Set Name",
        #       "file_path": "filename.permissionset-meta.xml",
        #       "description": "Optional description"
        #     }
        #   ]
        # }
        
        useless_permission_sets = report_data.get('useless_permission_sets', [])
        total_permission_sets = report_data.get('total_permission_sets', 0)
        scan_date = report_data.get('scan_date', 'Unknown')
        
        # Set gauge values for each useless permission set
        for perm_set in useless_permission_sets:
            permission_set_name = perm_set.get('name', 'Unknown')
            file_path = perm_set.get('file_path', 'Unknown')
            
            useless_permission_sets_gauge.labels(
                permission_set_name=permission_set_name,
                file_path=file_path
            ).set(1)
            
            logger.debug("Found useless permission set: %s (%s)", permission_set_name, file_path)
        
        logger.info("Useless permission sets monitoring completed. Found %d useless permission sets out of %d total (scan date: %s)", 
                   len(useless_permission_sets), total_permission_sets, scan_date)
        
    # pylint: disable=broad-except
    except json.JSONDecodeError as e:
        logger.error("Error parsing useless permission sets JSON report: %s", e)
    except FileNotFoundError as e:
        logger.error("Useless permission sets report file not found: %s", e)
    except Exception as e:
        logger.error("Error monitoring useless permission sets: %s", e)

def dashboards_with_inactive_users(sf):
    """
    Query dashboards where the running user is inactive.
    This identifies dashboards that may fail or show incorrect data due to inactive user context.
    """
    try:
        logger.info("Querying dashboards with inactive running users...")
        query = """
        SELECT Id, Title, RunningUser.Name, LastReferencedDate, RunningUser.IsActive, CreatedDate 
        FROM Dashboard 
        WHERE RunningUser.IsActive = false
        """
        results = query_records_all(sf, query)
        
        # Clear existing Prometheus gauge labels
        dashboards_with_inactive_users_gauge.clear()
        
        dashboard_count = len(results)
        
        for record in results:
            dashboard_id = record.get('Id', 'Unknown')
            dashboard_title = record.get('Title', 'Unknown')
            running_user_name = record.get('RunningUser', {}).get('Name', 'Unknown') if record.get('RunningUser') else 'Unknown'
            created_date = record.get('CreatedDate', 'Unknown')
            last_referenced_date = record.get('LastReferencedDate', 'Never')
            
            # Set gauge to 1 (inactive) for each dashboard with inactive user
            dashboards_with_inactive_users_gauge.labels(
                dashboard_id=dashboard_id,
                dashboard_title=dashboard_title,
                running_user_name=running_user_name,
                created_date=created_date,
                last_referenced_date=last_referenced_date if last_referenced_date else 'Never'
            ).set(1)
        
        logger.info("Dashboards with inactive users monitoring completed. Found %d dashboards with inactive running users", dashboard_count)
        
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error querying dashboards with inactive users: %s", e)
