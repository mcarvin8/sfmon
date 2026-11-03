"""Metrics about sfmon itself: per-job success, timing and query errors.

Every job run goes through salesforce_monitoring._run_job(), which calls
start_job_run() before the collector and record_job_result() after it. The
org label comes from OrgAwareGauge's per-job contextvar like every other
metric, and the job label is the job id used in config.json.

A collector that catches its own errors still reports success to _run_job,
and query.py turns failed queries into empty results so collectors keep
going. To keep those failures visible, query.py calls record_query_error(),
and a run with any query errors counts as failed.
"""

import time
from contextvars import ContextVar

from .org_gauge import OrgAwareGauge

job_success_gauge = OrgAwareGauge(
    "sfmon_job_success",
    "1 if the job's last run finished with no exception and no query errors, else 0",
    ["job"],
)
job_last_run_gauge = OrgAwareGauge(
    "sfmon_job_last_run_timestamp_seconds",
    "Unix time the job's last run finished",
    ["job"],
)
job_last_success_gauge = OrgAwareGauge(
    "sfmon_job_last_success_timestamp_seconds",
    "Unix time the job last finished successfully",
    ["job"],
)
job_duration_gauge = OrgAwareGauge(
    "sfmon_job_duration_seconds",
    "Wall-clock duration of the job's last run in seconds",
    ["job"],
)
job_query_errors_gauge = OrgAwareGauge(
    "sfmon_job_query_errors",
    "Number of Salesforce queries that failed during the job's last run",
    ["job"],
)

# Holds a one-item list counting query errors for the job running in this
# context; None outside a job run (e.g. tests calling collectors directly).
_query_errors = ContextVar("query_errors", default=None)


def start_job_run():
    """Start counting query errors for a job run. Returns the start time."""
    _query_errors.set([0])
    return time.monotonic()


def record_query_error():
    """Count one failed query against the job running in this context."""
    errors = _query_errors.get()
    if errors is not None:
        errors[0] += 1


def query_error_count():
    """Return the number of query errors counted since start_job_run()."""
    errors = _query_errors.get()
    return errors[0] if errors is not None else 0


def record_job_result(job_id, started, success):
    """Set the job's self-monitoring gauges for the run that just finished."""
    finished = time.time()
    job_success_gauge.labels(job=job_id).set(1 if success else 0)
    job_last_run_gauge.labels(job=job_id).set(finished)
    job_duration_gauge.labels(job=job_id).set(time.monotonic() - started)
    job_query_errors_gauge.labels(job=job_id).set(query_error_count())
    if success:
        job_last_success_gauge.labels(job=job_id).set(finished)
