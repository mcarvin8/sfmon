"""
Dashboard Management Monitoring Module

This module monitors dashboard-related technical debt including:
- Dashboards with inactive running users

Data Sources:
    - Dashboard object with RunningUser relationship
"""
from logger import logger
from gauges import dashboards_with_inactive_users_gauge
from query import query_records_all


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

