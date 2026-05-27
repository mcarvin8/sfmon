"""OrgAwareGauge: drop-in Prometheus Gauge wrapper that auto-injects an 'org' label.

The org value is read from the ORG_NAME environment variable at metric-record time,
so all call sites that use .labels() or .set() continue to work unchanged.
"""

import os

from prometheus_client import Gauge


class OrgAwareGauge:
    """Wraps prometheus_client.Gauge to auto-append an 'org' label from ORG_NAME.

    Usage is identical to prometheus_client.Gauge — the 'org' label is appended
    automatically to the label list and injected on every .labels() call.  For
    gauges that previously had no labels, .set() is forwarded through
    .labels(org=ORG_NAME).set() so existing call sites need no changes.
    """

    def __init__(self, name, documentation, labelnames=None, **kwargs):
        if labelnames is None:
            labelnames = []
        self._original_labelnames = list(labelnames)
        self._gauge = Gauge(
            name, documentation, self._original_labelnames + ["org"], **kwargs
        )

    def _org(self):
        return os.getenv("ORG_NAME", "")

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
