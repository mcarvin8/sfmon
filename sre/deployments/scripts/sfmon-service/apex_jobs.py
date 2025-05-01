"""
    Apex related jobs.
"""
from cloudwatch_logging import logger
from gauges import (async_job_status_gauge, run_time_metric, cpu_time_metric,
                    exec_time_metric, db_total_time_metric, callout_time_metric,
                    apex_exception_details_gauge, apex_exception_category_count_gauge,
                    top_apex_concurrent_errors_sorted_by_avg_runtime,
                    top_apex_concurrent_errors_sorted_by_count,
                    concurrent_errors_count_gauge, apex_entry_point_count,
                    apex_avg_runtime, apex_max_runtime,
                    apex_total_runtime, apex_avg_cputime,
                    apex_max_cputime, apex_runtime_gt_5s_count,
                    apex_runtime_gt_10s_count, apex_runtime_gt_5s_percentage)
from log_parser import parse_logs
import pandas as pd
import requests
from constants import QUERY_TIMEOUT_SECONDS


APEX_EXECUTION_EVENT_QUERY = (
    "SELECT Id FROM EventLogFile WHERE EventType = 'ApexExecution' and Interval = 'Hourly' "
    "ORDER BY LogDate DESC LIMIT 1"
)


def async_apex_job_status(sf):
    """
    Get async apex job status details from the org.
    """
    logger.info("Getting Async Job status...")
    query = """
        SELECT Id, Status, JobType, ApexClassId, MethodName, NumberOfErrors FROM AsyncApexJob 
        WHERE CreatedDate = TODAY
    """
    try:
        result = sf.query_all(query, timeout=QUERY_TIMEOUT_SECONDS)
    except requests.exceptions.Timeout:
        logger.error("Query timed out after : %s seconds.", QUERY_TIMEOUT_SECONDS)
        return None

    overall_status_counts = {}

    for record in result['records']:
        status = record['Status']
        job_type = record['JobType']
        method = record['MethodName']
        errors = record['NumberOfErrors']

        if (status, method, job_type, errors) not in overall_status_counts:
            overall_status_counts[(status, method, job_type, errors)] = 0
        overall_status_counts[(status, method, job_type, errors)] += 1

    for (status, method, job_type, errors), count in overall_status_counts.items():
        async_job_status_gauge.labels(status=status, method=method, job_type=job_type, number_of_errors=errors).set(count)


def monitor_apex_execution_time(sf):
    """
    Get apex job execution details from the org
    and expose run_time, cpu_time, execution_time, database_time, callout_time etc details.
    """
    logger.info("Getting Apex executions...")
    try:

        run_time_metric.clear()
        cpu_time_metric.clear()
        exec_time_metric.clear()
        db_total_time_metric.clear()
        callout_time_metric.clear()

        apex_execution_logs = parse_logs(sf, APEX_EXECUTION_EVENT_QUERY)

        df = pd.DataFrame(apex_execution_logs)

        for _, log_entry in df.iterrows():
            entry_point = log_entry['ENTRY_POINT']
            quiddity = log_entry['QUIDDITY']
            run_time = float(log_entry.get('RUN_TIME', 0))
            cpu_time = float(log_entry.get('CPU_TIME', 0))
            exec_time = float(log_entry.get('EXEC_TIME', 0))
            db_total_time = float(log_entry.get('DB_TOTAL_TIME', 0))
            callout_time = float(log_entry.get('CALLOUT_TIME', 0))

            run_time_metric.labels(entry_point=entry_point, quiddity=quiddity).set(run_time)
            cpu_time_metric.labels(entry_point=entry_point, quiddity=quiddity).set(cpu_time)
            exec_time_metric.labels(entry_point=entry_point, quiddity=quiddity).set(exec_time)
            db_total_time_metric.labels(entry_point=entry_point, quiddity=quiddity).set(db_total_time)
            callout_time_metric.labels(entry_point=entry_point, quiddity=quiddity).set(callout_time)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("An unexpected error occurred in monitor_apex_execution : %s", e)


def expose_apex_exception_metrics(sf):
    """
    Processes list of Apex Unexpected Exception records and exposes two Prometheus metrics:
    1. Detailed metrics for each individual exception including 
        request ID, exception type, message, stack trace, and category fields.
    2. Metric that counts the total number of exceptions for each exception category.
    """
    apex_exception_details_gauge.clear()
    apex_exception_category_count_gauge.clear()

    logger.info("Getting Apex unexpected execeptions...")
    apex_unexpected_exception_query = (
        "SELECT Id FROM EventLogFile WHERE EventType = 'ApexUnexpectedException' and Interval = 'Hourly' "
        "ORDER BY LogDate DESC LIMIT 1")
    apex_unexpected_exception_records = list(parse_logs(sf, apex_unexpected_exception_query))

    exception_category_counts = {}

    for row in apex_unexpected_exception_records:
        try:
            category = row['EXCEPTION_CATEGORY']

            # Count the number of occurrences of each exception category
            if category in exception_category_counts:
                exception_category_counts[category] += 1
            else:
                exception_category_counts[category] = 1

            # Expose the details for each entry
            apex_exception_details_gauge.labels(
                request_id=row['REQUEST_ID'],
                exception_type=row['EXCEPTION_TYPE'],
                exception_message=row['EXCEPTION_MESSAGE'],
                stack_trace=row['STACK_TRACE'],
                timestamp=row['TIMESTAMP_DERIVED'],
                exception_category=category
            ).set(1)

        except KeyError as e:
            logger.error("Missing expected key: %s. Record: %s", e, row)
        except TypeError as e:
            logger.error("Type error encountered: %s. Record: %s", e, row)
        # pylint: disable=broad-except
        except Exception as e:
            logger.error("Unexpected error: %s. Record: %s", e, row)

    try:
        # Expose the metrics for each exception category
        for category, count in exception_category_counts.items():
            apex_exception_category_count_gauge.labels(exception_category=category).set(count)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error while exposing category count metrics: %s", e)


def expose_concurrent_errors_metrics_sorted_by_average_runtime(df_filtered):
    """
    Expose Top Long Running Requests by Average Runtime with Runtime > 5 seconds
    """
    try:
        top_apex_concurrent_errors_sorted_by_avg_runtime.clear()

        average_metrics = df_filtered.groupby('ENTRY_POINT').agg({
            'RUN_TIME': 'mean',
            'EXEC_TIME': 'mean',
            'DB_TOTAL_TIME': 'mean'
        }).reset_index()

        # Count occurrences
        entry_point_counts = df_filtered['ENTRY_POINT'].value_counts().reset_index()
        entry_point_counts.columns = ['ENTRY_POINT', 'OCCURRENCE_COUNT']

        # Merge counts with averages
        average_metrics = pd.merge(
            average_metrics,
            entry_point_counts,
            on='ENTRY_POINT',
            how='left',
            validate='one_to_one'
        )
        average_metrics = average_metrics.sort_values(by='RUN_TIME', ascending=False)

        for _, record in average_metrics.head(5).iterrows():
            top_apex_concurrent_errors_sorted_by_avg_runtime.labels(
                entry_point = record['ENTRY_POINT'],
                count = record['OCCURRENCE_COUNT'],
                avg_exec_time = record['EXEC_TIME'],
                avg_db_time = record['DB_TOTAL_TIME']
            ).set(record['RUN_TIME'])
    # pylint: disable=broad-except
    except KeyError as ke:
        logger.error("KeyError in calculate_average_metrics: %s", ke)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("An unexpected error occurred in calculate_average_metrics: %s", e)


def expose_concurrent_errors_metrics_sorted_by_request_count(df_filtered):
    """
    Expose Top Long Running Requests by Entry point Count with Runtime > 5 seconds
    """
    try:
        top_apex_concurrent_errors_sorted_by_count.clear()

        request_count = df_filtered.groupby('ENTRY_POINT').agg({
            'RUN_TIME': ['count', 'mean'],
            'EXEC_TIME': 'mean',
            'DB_TOTAL_TIME': 'mean'
        }).reset_index()

        # Rename columns for clarity
        request_count.columns = ['ENTRY_POINT', 'COUNT', 'AVG_RUN_TIME', 'AVG_EXEC_TIME', 'AVG_DB_TIME']
        request_count = request_count.sort_values(by='COUNT', ascending=False)

        for _, record in request_count.head(5).iterrows():
            top_apex_concurrent_errors_sorted_by_count.labels(
                entry_point = record['ENTRY_POINT'],
                avg_run_time = record['AVG_RUN_TIME'],
                avg_exec_time = record['AVG_EXEC_TIME'],
                avg_db_time = record['AVG_DB_TIME']
            ).set(record['COUNT'])

    except KeyError as ke:
        logger.error("KeyError in calculate_request_count: %s", ke)
    except Exception as e: # pylint: disable=broad-except
        logger.error("An unexpected error occurred in calculate_request_count: %s", e)


def concurrent_apex_errors(sf):
    """
    Expose metrics for Concurrent Apex errors, 
    display two metrics
    one based on entry points who used avg run time the most
    second based maximum request count from top entry point
    """
    try:
        apex_execution_logs = parse_logs(sf, APEX_EXECUTION_EVENT_QUERY)

        df = pd.DataFrame(apex_execution_logs)

        df['RUN_TIME'] = pd.to_numeric(df['RUN_TIME'], errors='coerce')
        df['IS_LONG_RUNNING_REQUEST'] = pd.to_numeric(df['IS_LONG_RUNNING_REQUEST'], errors='coerce')
        df['EXEC_TIME'] = pd.to_numeric(df['EXEC_TIME'], errors='coerce')
        df['DB_TOTAL_TIME'] = pd.to_numeric(df['DB_TOTAL_TIME'], errors='coerce')

        df_filtered = df[(df['IS_LONG_RUNNING_REQUEST'] == 1) & (df['RUN_TIME'] > 5000)]

        if df_filtered.empty:
            logger.info("No long-running requests found in the logs.")
            return

        expose_concurrent_errors_metrics_sorted_by_average_runtime(df_filtered)
        expose_concurrent_errors_metrics_sorted_by_request_count(df_filtered)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("An unexpected error occurred in concurrent_apex_errors: %s", e)


def expose_concurrent_long_running_apex_errors(sf):
    """
    Count and expose total requests made from ConcurrentLongRunningApexLimit log
    """
    try:
        log_query = (
            "SELECT Id FROM EventLogFile WHERE EventType = 'ConcurrentLongRunningApexLimit' AND Interval = 'Daily' "
            "AND LogDate = TODAY ORDER BY LogDate DESC LIMIT 1")

        concurrent_long_running_apex_logs = parse_logs(sf, log_query)

        if not concurrent_long_running_apex_logs:
            logger.info("No concurrent long running apex error occurred yesterday")
            return

        df = pd.DataFrame(concurrent_long_running_apex_logs)
        requests_made = df['REQUEST_ID'].dropna().shape[0]
        event_type = df['EVENT_TYPE'].iloc[0] if not df.empty else 'ConcurrentLongRunningApexLimit'
        concurrent_errors_count_gauge.labels(event_type=event_type).set(requests_made)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("An unexpected error occurred in exposing concurrent_longrunning_apex_limits: %s", e)


def async_apex_execution_summary(sf):
    """
    Fetch apex job execution details from the org, calculate metrics, and expose them via Prometheus.
    """

    logger.info("Getting Apex executions summary...")
    try:
        apex_execution_logs = parse_logs(sf, APEX_EXECUTION_EVENT_QUERY)

        df = pd.DataFrame(apex_execution_logs)

        valid_quiddities = ['F', 'S', 'Q', 'BA', 'C', 'K', 'QTXF', 'B']
        df = df[df['QUIDDITY'].isin(valid_quiddities)]

        df['RUN_TIME'] = pd.to_numeric(df['RUN_TIME'])
        df['CPU_TIME'] = pd.to_numeric(df['CPU_TIME'])

        grouped = df.groupby(['ENTRY_POINT', 'QUIDDITY']).agg(
            count=('RUN_TIME', 'size'),
            total_runtime=('RUN_TIME', 'sum'),
            avg_runtime=('RUN_TIME', 'mean'),
            max_runtime=('RUN_TIME', 'max'),
            total_cputime=('CPU_TIME', 'sum'),
            avg_cputime=('CPU_TIME', 'mean'),
            max_cputime=('CPU_TIME', 'max'),
            runtime_gt_5s=('RUN_TIME', lambda x: (x > 5000).sum()),
            runtime_gt_10s=('RUN_TIME', lambda x: (x > 10000).sum())
        ).reset_index()

        grouped['runtime_gt_5s_percentage'] = (grouped['runtime_gt_5s'] / grouped['count']) * 100

        for _, row in grouped.iterrows():
            entry_point = row['ENTRY_POINT']
            quiddity = row['QUIDDITY']

            apex_entry_point_count.labels(entry_point, quiddity).inc(row['count'])
            apex_avg_runtime.labels(entry_point, quiddity).set(row['avg_runtime'])
            apex_max_runtime.labels(entry_point, quiddity).set(row['max_runtime'])
            apex_total_runtime.labels(entry_point, quiddity).set(row['total_runtime'])
            apex_avg_cputime.labels(entry_point, quiddity).set(row['avg_cputime'])
            apex_max_cputime.labels(entry_point, quiddity).set(row['max_cputime'])
            apex_runtime_gt_5s_count.labels(entry_point, quiddity).inc(row['runtime_gt_5s'])
            apex_runtime_gt_10s_count.labels(entry_point, quiddity).inc(row['runtime_gt_10s'])
            apex_runtime_gt_5s_percentage.labels(entry_point, quiddity).set(row['runtime_gt_5s_percentage'])
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error fetching async_apex_execution_summary : %s", e)
