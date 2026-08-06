"""OrgAwareGauge: drop-in Prometheus Gauge wrapper that auto-injects an 'org' label.

The org value comes from a per-job contextvar (set by the scheduler via
set_current_org() before each job runs), falling back to the ORG_NAME
environment variable when no contextvar has been set (e.g. single-org mode,
or direct calls outside the scheduler such as tests). All call sites that use
.labels() or .set() continue to work unchanged.
"""

import os
from contextvars import ContextVar

from prometheus_client import Gauge

_current_org: ContextVar = ContextVar("current_org", default=None)


def set_current_org(org_name):
    """Set the org label used by every OrgAwareGauge for the current job run.

    Called once per job invocation by the scheduler before it calls into a
    collector, so collectors themselves never need to know which org they're
    running against.
    """
    _current_org.set(org_name)


class OrgAwareGauge:
    """Wraps prometheus_client.Gauge to auto-append an 'org' label.

    Usage is identical to prometheus_client.Gauge — the 'org' label is appended
    automatically to the label list and injected on every .labels() call.  For
    gauges that previously had no labels, .set() is forwarded through
    .labels(org=...).set() so existing call sites need no changes.
    """

    def __init__(self, name, documentation, labelnames=None, **kwargs):
        if labelnames is None:
            labelnames = []
        self._original_labelnames = list(labelnames)
        self._gauge = Gauge(
            name, documentation, self._original_labelnames + ["org"], **kwargs
        )

    def _org(self):
        org = _current_org.get()
        return org if org is not None else os.getenv("ORG_NAME", "")

    def labels(self, *args, **kwargs):
        if args:
            for label_name, value in zip(self._original_labelnames, args):
                kwargs[label_name] = value
        kwargs.setdefault("org", self._org())
        return self._gauge.labels(**kwargs)

    def set(self, value):
        """Forward .set() to the org-labelled child for previously-unlabeled gauges."""
        return self._gauge.labels(org=self._org()).set(value)

    def clear(self):
        return self._gauge.clear()

    def __getattr__(self, name):
        return getattr(self._gauge, name)
