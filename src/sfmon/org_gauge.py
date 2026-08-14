"""OrgAwareGauge: drop-in Prometheus-compatible gauge that auto-injects an 'org' label.

Backed by the OpenTelemetry metrics SDK instead of prometheus_client.Gauge
directly, but exposed through OTel's Prometheus exporter so `/metrics` stays
byte-compatible with the previous implementation — existing scrape configs
and dashboards need no changes. Moving the instrumentation layer to OTel
here (without yet adding an OTLP exporter) is groundwork for an optional
push path in a later change, without touching any of the ~80 call sites
across core/ops/audit/tech_debt that call .labels()/.set()/.inc()/.clear().

Each OrgAwareGauge registers one OTel ObservableGauge whose callback reads
from an in-process dict of {label-key: value}. That dict is exactly what
.labels(...).set()/.inc() write into and what .clear() empties — OTel has no
built-in way to "unset" a previously-reported label combination for a
synchronous instrument, so an Observable instrument (pull-based, callback
supplies only what's currently in the dict) is what makes .clear() semantics
possible at all here.

The org value comes from a per-job contextvar (set by the scheduler via
set_current_org() before each job runs), falling back to the ORG_NAME
environment variable when no contextvar has been set (e.g. single-org mode,
or direct calls outside the scheduler such as tests).

OTLP push (optional): if OTEL_EXPORTER_OTLP_ENDPOINT is set, metrics are also
pushed there periodically in addition to being scrapeable on /metrics — for
backends (Datadog, Honeycomb, ...) that don't run a Prometheus scrape target.
Unset, behavior is identical to Prometheus-only. See docs/ENVIRONMENT.md.
"""

import os
import threading
from contextvars import ContextVar

from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.metrics import Observation, get_meter, set_meter_provider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

_current_org: ContextVar = ContextVar("current_org", default=None)


def _build_metric_readers():
    """Prometheus reader is always on; OTLP push is added only when
    OTEL_EXPORTER_OTLP_ENDPOINT is set, so default behavior is unchanged."""
    readers = [
        # disable_target_info/scope_info_enabled off so the Prometheus text
        # output carries no extra otel_scope_*/target_info lines beyond what
        # prometheus_client.Gauge would have emitted directly. Registers into
        # prometheus_client's default REGISTRY, which is what
        # start_http_server() in salesforce_monitoring.py already serves —
        # no wiring changes needed there.
        PrometheusMetricReader(disable_target_info=True, scope_info_enabled=False)
    ]
    if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
        # pylint: disable=import-outside-toplevel
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
            OTLPMetricExporter,
        )

        readers.append(PeriodicExportingMetricReader(OTLPMetricExporter()))
    return readers


# One MeterProvider per process.
set_meter_provider(MeterProvider(metric_readers=_build_metric_readers()))
_meter = get_meter("sfmon")


def set_current_org(org_name):
    """Set the org label used by every OrgAwareGauge for the current job run.

    Called once per job invocation by the scheduler before it calls into a
    collector, so collectors themselves never need to know which org they're
    running against.
    """
    _current_org.set(org_name)


def get_current_org():
    """Return the org for the current job run (contextvar, falling back to
    ORG_NAME) — same lookup OrgAwareGauge uses to label metrics, exposed for
    non-gauge call sites like slack_notify that need to key/tag by org too."""
    org = _current_org.get()
    return org if org is not None else os.getenv("ORG_NAME", "")


class _Child:
    """Bound label-values handle returned by OrgAwareGauge.labels(...)."""

    __slots__ = ("_gauge", "_key")

    def __init__(self, gauge, key):
        self._gauge = gauge
        self._key = key

    def set(self, value):
        with self._gauge._lock:
            self._gauge._values[self._key] = float(value)

    def inc(self, amount=1):
        with self._gauge._lock:
            current = self._gauge._values.get(self._key, 0.0)
            self._gauge._values[self._key] = current + amount


class OrgAwareGauge:
    """OTel-backed gauge with an 'org' label auto-appended and auto-injected.

    Usage is identical to prometheus_client.Gauge — the 'org' label is
    appended automatically to the label list and injected on every .labels()
    call. For gauges that previously had no labels, .set() is forwarded
    through .labels(org=...).set() so existing call sites need no changes.
    """

    def __init__(self, name, documentation, labelnames=None):
        self._original_labelnames = list(labelnames or [])
        self._values = {}
        self._lock = threading.Lock()
        _meter.create_observable_gauge(
            name, callbacks=[self._collect], description=documentation
        )

    def _collect(self, options):
        with self._lock:
            snapshot = list(self._values.items())
        for key, value in snapshot:
            yield Observation(value, attributes=dict(key))

    def _org(self):
        return get_current_org()

    def labels(self, *args, **kwargs):
        if args:
            for label_name, value in zip(self._original_labelnames, args):
                kwargs[label_name] = value
        kwargs.setdefault("org", self._org())
        key = tuple(sorted((k, str(v)) for k, v in kwargs.items()))
        return _Child(self, key)

    def set(self, value):
        """Forward .set() to the org-labelled child for previously-unlabeled gauges."""
        return self.labels().set(value)

    def clear(self):
        with self._lock:
            self._values.clear()
