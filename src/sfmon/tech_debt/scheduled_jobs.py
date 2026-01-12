"""
Scheduled Apex Jobs Monitoring Module

This module monitors scheduled Apex jobs in the Salesforce org to track:
- Total number of scheduled jobs
- Job states and scheduling patterns
- Jobs that may need cleanup or review

Data Sources:
    - CronTrigger object (with CronJobDetail relationship)
"""
from logger import logger
from gauges import scheduled_apex_jobs_gauge
from query import query_records_all


def scheduled_apex_jobs_monitoring(sf):
    """
    Query all scheduled Apex jobs (CronTrigger with JobType='7') to monitor
    technical debt related to scheduled job management.
    
    JobType '7' specifically identifies Scheduled Apex jobs.
    """
    try:
        logger.info("Querying scheduled Apex jobs...")
        query = """
        SELECT
            Id,
            CronJobDetail.Name,
            CronJobDetail.JobType,
            CronExpression,
            State,
            NextFireTime,
            PreviousFireTime,
            TimesTriggered,
            CreatedBy.Name,
            CreatedDate
        FROM CronTrigger
        WHERE CronJobDetail.JobType = '7' AND State != 'Deleted'
        ORDER BY NextFireTime
        """
        results = query_records_all(sf, query)
        
        # Clear existing Prometheus gauge labels
        scheduled_apex_jobs_gauge.clear()

        for record in results:
            # Safely extract nested fields
            cron_job_detail = record.get('CronJobDetail') or {}
            created_by = record.get('CreatedBy') or {}
            
            scheduled_apex_jobs_gauge.labels(
                job_id=record['Id'],
                job_name=cron_job_detail.get('Name', 'Unknown'),
                cron_expression=record.get('CronExpression', 'Unknown'),
                state=record.get('State', 'Unknown'),
                next_fire_time=record.get('NextFireTime') or 'None',
                previous_fire_time=record.get('PreviousFireTime') or 'None',
                created_by=created_by.get('Name', 'Unknown'),
                created_date=record.get('CreatedDate', 'Unknown')
            ).set(int(record.get('TimesTriggered', 0)))
            
        logger.info("Found %d scheduled Apex jobs", len(results))
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching scheduled Apex jobs: %s", e)
