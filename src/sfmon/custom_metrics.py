"""
Custom SOQL Metrics

Lets operators add metrics for objects sfmon doesn't know about (CPQ, Billing,
their own custom objects) from config.json instead of building their own
image. Each entry in the config's "custom_metrics" array runs one SOQL query
on its own schedule and stores the result in one gauge.

Config entry:
    {
        "name": "cpq_quotes_by_status",          # required, snake_case
        "description": "Primary CPQ quotes by status",
        "query": "SELECT SBQQ__Status__c status, COUNT(Id) total
                  FROM SBQQ__Quote__c GROUP BY SBQQ__Status__c",
        "schedule": "minute=0",                   # required, any schedule format
        "value_field": "total",                   # optional, see below
        "labels": {"status": "status"},           # optional, label -> field path
        "api": "rest",                            # optional, "rest" or "tooling"
        "orgs": ["prod"],                         # optional, fleet-mode org filter
        "max_series": 500                         # optional, row cap
    }

Gauge value:
    - No value_field: one series per org set to the query's totalSize, which is
      the count for SELECT COUNT() and the row count for any other query.
    - value_field: one series per returned row, valued from that field and
      labelled from the "labels" map. Field paths may follow relationships
      ("Account.Owner.Name"); lookups fall back to case-insensitive matching.

The gauge is always named sfmon_custom_<name> and gets the usual 'org' label.
The job id is custom_<name>: it shows up as the 'job' label on sfmon_job_*
self-metrics, works with --once --job, and can be overridden or set to
"disabled" per org through org_overrides.<org>.schedules.

Config errors are collected and raised together as CustomMetricConfigError at
startup so a typo stops the container instead of silently dropping a metric.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from apscheduler.triggers.cron import CronTrigger

from .config import _effective_schedules, load_config, parse_cron_schedule
from .logger import logger
from .org_gauge import OrgAwareGauge
from .query import query_result

METRIC_PREFIX = "sfmon_custom_"
JOB_PREFIX = "custom_"
DEFAULT_MAX_SERIES = 500
DISABLED_SCHEDULES = ("disabled", "none")

_SNAKE_CASE = re.compile(r"[a-z][a-z0-9_]*")
_RESERVED_LABELS = {"org", "job"}
_ALLOWED_KEYS = {
    "name",
    "description",
    "query",
    "schedule",
    "value_field",
    "labels",
    "api",
    "orgs",
    "max_series",
}

# One OTel instrument per metric name for the life of the process: the meter
# can't unregister an instrument, so reloading config reuses the gauge.
_gauges = {}
_metrics = None


class CustomMetricConfigError(ValueError):
    """Raised when the custom_metrics config block has one or more errors."""


@dataclass(frozen=True)
class CustomMetric:
    """One validated custom_metrics entry."""

    name: str
    query: str
    schedule: Optional[dict]  # None means disabled
    description: str = ""
    value_field: Optional[str] = None
    labels: dict = field(default_factory=dict)
    api: str = "rest"
    orgs: Optional[tuple] = None
    max_series: int = DEFAULT_MAX_SERIES

    @property
    def metric_name(self):
        return f"{METRIC_PREFIX}{self.name}"

    @property
    def job_id(self):
        return f"{JOB_PREFIX}{self.name}"

    @property
    def job_name(self):
        return f"Custom Metric {self.name}"

    def applies_to(self, org_name):
        return self.orgs is None or org_name in self.orgs

    def schedule_for(self, org_name, config=None):
        """CronTrigger kwargs for this org, or None if it shouldn't run there.

        An entry for the job id in the org's effective schedules (fleet-wide
        schedules plus org_overrides) wins over the metric's own schedule.
        """
        if not self.applies_to(org_name):
            return None
        config = load_config() if config is None else config
        schedules = _effective_schedules(config, org_name)
        if self.job_id in schedules:
            return parse_cron_schedule(schedules[self.job_id])
        return self.schedule

    def collect(self, sf):
        """Run the query and replace this org's series with the result."""
        result = query_result(sf, self.query, tooling=self.api == "tooling")
        gauge = _gauge(self)
        if result is None:
            # query.py already logged and counted the failure; drop stale
            # values so dashboards don't show old numbers as current.
            gauge.clear()
            return
        if self.value_field is None:
            records = result.get("records") or []
            total = result.get("totalSize", len(records))
            gauge.replace_org([({}, total)])
            return
        gauge.replace_org(self._series(result.get("records") or []))

    def _series(self, records):
        if len(records) > self.max_series:
            logger.warning(
                "Custom metric '%s' returned %d rows; keeping the first %d "
                "(raise max_series or aggregate with GROUP BY)",
                self.name,
                len(records),
                self.max_series,
            )
            records = records[: self.max_series]
        series = {}
        for record in records:
            raw = resolve_field(record, self.value_field)
            value = _to_float(raw)
            if value is None:
                if raw is not None:
                    logger.warning(
                        "Custom metric '%s': value_field '%s' is not numeric (%r); row skipped",
                        self.name,
                        self.value_field,
                        raw,
                    )
                continue
            labels = {
                label: _label_value(resolve_field(record, path))
                for label, path in self.labels.items()
            }
            key = tuple(sorted(labels.items()))
            if key in series:
                logger.warning(
                    "Custom metric '%s': duplicate labels %s; last row wins",
                    self.name,
                    labels,
                )
            series[key] = (labels, value)
        return list(series.values())


def resolve_field(record, path):
    """Follow a dotted field path through a SOQL record.

    Exact key match first, then case-insensitive, since Salesforce returns
    API-name casing that may not match how the query was written.
    """
    value = record
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        if part in value:
            value = value[part]
            continue
        lowered = part.lower()
        match = next((k for k in value if k.lower() == lowered), None)
        if match is None:
            return None
        value = value[match]
    return value


def _to_float(value):
    if value is None or isinstance(value, (dict, list)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _label_value(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _gauge(metric):
    gauge = _gauges.get(metric.metric_name)
    if gauge is None:
        gauge = OrgAwareGauge(
            metric.metric_name,
            metric.description or f"Custom SOQL metric {metric.name}",
            sorted(metric.labels),
        )
        _gauges[metric.metric_name] = gauge
    return gauge


def _check_schedule(value, where, errors):
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{where}: 'schedule' is required (e.g. \"minute=0\")")
        return None
    if value.strip().lower() in DISABLED_SCHEDULES:
        return None
    parsed = parse_cron_schedule(value)
    try:
        if parsed is None:
            raise ValueError("unrecognised format")
        CronTrigger(**parsed)
    except (TypeError, ValueError) as e:
        errors.append(f"{where}: invalid schedule {value!r}: {e}")
        return None
    return parsed


def _check_labels(labels, where, errors):
    if labels is None:
        return {}
    if not isinstance(labels, dict):
        errors.append(f"{where}: 'labels' must be an object of label -> field path")
        return {}
    for label, path in labels.items():
        if not _SNAKE_CASE.fullmatch(label):
            errors.append(f"{where}: label {label!r} must be snake_case")
        elif label in _RESERVED_LABELS:
            errors.append(f"{where}: label {label!r} is reserved")
        if not isinstance(path, str) or not path.strip():
            errors.append(f"{where}: label {label!r} needs a field path")
    return labels


def _check_entry(index, entry, seen, errors):
    """Validate one entry, appending problems to errors. Returns a
    CustomMetric, or None if the entry was too broken to build."""
    where = f"custom_metrics[{index}]"
    if not isinstance(entry, dict):
        errors.append(f"{where}: must be an object")
        return None
    start = len(errors)

    name = entry.get("name")
    if isinstance(name, str) and name:
        where = f"custom_metrics[{index}] ({name})"
    unknown = sorted(set(entry) - _ALLOWED_KEYS)
    if unknown:
        errors.append(f"{where}: unknown keys {unknown}")

    if not isinstance(name, str) or not _SNAKE_CASE.fullmatch(name):
        errors.append(f"{where}: 'name' is required and must be snake_case")
    elif name.startswith("sfmon_"):
        errors.append(f"{where}: drop the 'sfmon_' prefix; metrics are named {METRIC_PREFIX}<name>")
    elif name in seen:
        errors.append(f"{where}: duplicate name")
    else:
        seen.add(name)

    query = entry.get("query")
    if not isinstance(query, str) or not query.strip().lower().startswith("select"):
        errors.append(f"{where}: 'query' must be a SOQL SELECT statement")

    schedule = _check_schedule(entry.get("schedule"), where, errors)

    api = entry.get("api", "rest")
    if api not in ("rest", "tooling"):
        errors.append(f'{where}: \'api\' must be "rest" or "tooling"')

    value_field = entry.get("value_field")
    if value_field is not None and (not isinstance(value_field, str) or not value_field.strip()):
        errors.append(f"{where}: 'value_field' must be a field name")
    labels = _check_labels(entry.get("labels"), where, errors)
    if labels and value_field is None:
        errors.append(f"{where}: 'labels' needs 'value_field' (one series per row)")

    orgs = entry.get("orgs")
    if orgs is not None and (
        not isinstance(orgs, list) or not all(isinstance(o, str) for o in orgs)
    ):
        errors.append(f"{where}: 'orgs' must be a list of org names")

    max_series = entry.get("max_series", DEFAULT_MAX_SERIES)
    if isinstance(max_series, bool) or not isinstance(max_series, int) or max_series < 1:
        errors.append(f"{where}: 'max_series' must be a positive integer")

    description = entry.get("description", "")
    if not isinstance(description, str):
        errors.append(f"{where}: 'description' must be a string")

    if len(errors) > start:
        return None
    return CustomMetric(
        name=name,
        query=query.strip(),
        schedule=schedule,
        description=description,
        value_field=value_field,
        labels=dict(labels),
        api=api,
        orgs=tuple(orgs) if orgs is not None else None,
        max_series=max_series,
    )


def parse_custom_metrics(entries):
    """Validate a custom_metrics config block.

    Returns a list of CustomMetric. Raises CustomMetricConfigError listing
    every problem found, so all typos surface in one startup attempt.
    """
    if entries is None:
        return []
    if not isinstance(entries, list):
        raise CustomMetricConfigError("custom_metrics must be a list")
    errors = []
    seen = set()
    metrics = [_check_entry(i, entry, seen, errors) for i, entry in enumerate(entries)]
    if errors:
        raise CustomMetricConfigError(
            "Invalid custom_metrics config:\n  - " + "\n  - ".join(errors)
        )
    return metrics


def load_custom_metrics(force_reload=False):
    """Load, validate and cache custom metrics from config.json, creating
    their gauges. Raises CustomMetricConfigError on invalid config."""
    global _metrics
    if _metrics is not None and not force_reload:
        return _metrics
    config = load_config()
    metrics = parse_custom_metrics(config.get("custom_metrics"))
    known_orgs = set(config.get("orgs") or [])
    for metric in metrics:
        _gauge(metric)
        if known_orgs and metric.orgs:
            for org in set(metric.orgs) - known_orgs:
                logger.warning(
                    "Custom metric '%s' lists org '%s', which is not in 'orgs'",
                    metric.name,
                    org,
                )
    if metrics:
        logger.info("Loaded %d custom metrics from config", len(metrics))
    _metrics = metrics
    return _metrics
