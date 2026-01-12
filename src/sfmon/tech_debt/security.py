"""
Security & Health Monitoring Module

This module monitors security-related technical debt including:
- Salesforce Security Health Check score and grade
- Detailed security risks and misconfigurations

Data Sources:
    - SecurityHealthCheck (via Tooling API)
    - SecurityHealthCheckRisks (via Tooling API)
"""
from logger import logger
from gauges import (
    security_health_check_gauge,
    salesforce_health_risks_gauge,
)
from query import tooling_query_records_all


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

