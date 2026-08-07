"""Unit tests for org_gauge.OrgAwareGauge"""

import os
from unittest.mock import patch

import prometheus_client


def make_gauge(name, documentation, labelnames=None):
    from org_gauge import OrgAwareGauge

    if labelnames is not None:
        return OrgAwareGauge(name, documentation, labelnames)
    return OrgAwareGauge(name, documentation)


class TestOrgAwareGaugeLabels:
    def test_original_labelnames_stored(self):
        gauge = make_gauge("g_lbl_1", "doc", ["foo", "bar"])
        assert gauge._original_labelnames == ["foo", "bar"]

    def test_no_labelnames_defaults_to_empty(self):
        gauge = make_gauge("g_lbl_2", "doc")
        assert gauge._original_labelnames == []

    def test_empty_labelnames_stays_empty(self):
        gauge = make_gauge("g_lbl_3", "doc", [])
        assert gauge._original_labelnames == []

    def test_labels_injects_org_from_env(self):
        gauge = make_gauge("g_lbl_4", "doc", ["foo"])
        with patch.dict(os.environ, {"ORG_NAME": "prod-org"}):
            child = gauge.labels(foo="v")
            child.set(5)
        assert gauge._values[child._key] == 5
        assert dict(child._key)["org"] == "prod-org"
        assert dict(child._key)["foo"] == "v"

    def test_labels_defaults_org_to_empty_string_when_env_unset(self):
        gauge = make_gauge("g_lbl_5", "doc", ["foo"])
        env = {k: v for k, v in os.environ.items() if k != "ORG_NAME"}
        with patch.dict(os.environ, env, clear=True):
            child = gauge.labels(foo="bar")
            child.set(3)
        assert dict(child._key)["org"] == ""

    def test_caller_provided_org_is_not_overridden(self):
        gauge = make_gauge("g_lbl_6", "doc", ["foo"])
        with patch.dict(os.environ, {"ORG_NAME": "env-org"}):
            child = gauge.labels(foo="val", org="custom-org")
            child.set(9)
        assert dict(child._key)["org"] == "custom-org"


class TestOrgAwareGaugePositionalArgs:
    def test_positional_args_converted_to_kwargs(self):
        gauge = make_gauge("g_pos_1", "doc", ["entry_point", "quiddity"])
        with patch.dict(os.environ, {"ORG_NAME": "myorg"}):
            child = gauge.labels("MyApex.method", "future")
            child.set(7)
        key = dict(child._key)
        assert key["entry_point"] == "MyApex.method"
        assert key["quiddity"] == "future"
        assert key["org"] == "myorg"

    def test_mixed_positional_and_keyword_args(self):
        gauge = make_gauge("g_pos_2", "doc", ["a", "b", "c"])
        with patch.dict(os.environ, {"ORG_NAME": "org1"}):
            child = gauge.labels("x", "y", c="z")
            child.set(2)
        key = dict(child._key)
        assert key["a"] == "x"
        assert key["b"] == "y"
        assert key["c"] == "z"
        assert key["org"] == "org1"


class TestOrgAwareGaugeDirectSet:
    def test_set_on_unlabeled_gauge_uses_org(self):
        gauge = make_gauge("g_set_1", "doc")
        with patch.dict(os.environ, {"ORG_NAME": "myorg"}):
            gauge.set(42)
        assert list(gauge._values.values()) == [42]
        (key,) = gauge._values.keys()
        assert dict(key)["org"] == "myorg"

    def test_set_on_empty_labelnames_uses_org(self):
        gauge = make_gauge("g_set_2", "doc", [])
        with patch.dict(os.environ, {"ORG_NAME": "another-org"}):
            gauge.set(99)
        assert list(gauge._values.values()) == [99]


class TestOrgAwareGaugeInc:
    def test_inc_defaults_to_one(self):
        gauge = make_gauge("g_inc_1", "doc", ["foo"])
        with patch.dict(os.environ, {"ORG_NAME": "org1"}):
            gauge.labels(foo="x").inc()
            gauge.labels(foo="x").inc()
        assert list(gauge._values.values()) == [2]

    def test_inc_accepts_amount(self):
        gauge = make_gauge("g_inc_2", "doc", ["foo"])
        with patch.dict(os.environ, {"ORG_NAME": "org1"}):
            gauge.labels(foo="x").inc(5)
        assert list(gauge._values.values()) == [5]


class TestOrgAwareGaugeClear:
    def test_clear_removes_all_values(self):
        gauge = make_gauge("g_clr_1", "doc", ["foo"])
        with patch.dict(os.environ, {"ORG_NAME": "org1"}):
            gauge.labels(foo="x").set(1)
            gauge.labels(foo="y").set(2)
        gauge.clear()
        assert gauge._values == {}


class TestOrgAwareGaugeContextVar:
    """Fleet mode: set_current_org() takes priority over ORG_NAME for the
    duration it's set, letting the scheduler label each org's jobs correctly
    without threading org through every collector call site."""

    def test_context_org_takes_priority_over_env(self):
        from org_gauge import set_current_org

        gauge = make_gauge("g_ctx_1", "doc", ["foo"])
        with patch.dict(os.environ, {"ORG_NAME": "env-org"}):
            set_current_org("fleet-org")
            child = gauge.labels(foo="v")
            child.set(1)
        assert dict(child._key)["org"] == "fleet-org"

    def test_sequential_org_contexts_do_not_bleed_into_each_other(self):
        from org_gauge import set_current_org

        gauge = make_gauge("g_ctx_2", "doc", ["foo"])
        set_current_org("org-a")
        child_a = gauge.labels(foo="a")
        child_a.set(1)
        set_current_org("org-b")
        child_b = gauge.labels(foo="b")
        child_b.set(2)

        assert dict(child_a._key)["org"] == "org-a"
        assert dict(child_b._key)["org"] == "org-b"

    def test_falls_back_to_env_when_context_unset(self):
        from org_gauge import _current_org

        gauge = make_gauge("g_ctx_3", "doc", ["foo"])
        token = _current_org.set(None)
        try:
            with patch.dict(os.environ, {"ORG_NAME": "legacy-org"}):
                child = gauge.labels(foo="v")
                child.set(1)
        finally:
            _current_org.reset(token)
        assert dict(child._key)["org"] == "legacy-org"


class TestBuildMetricReaders:
    def test_only_prometheus_reader_when_otlp_unset(self):
        from org_gauge import _build_metric_readers
        from opentelemetry.exporter.prometheus import PrometheusMetricReader

        env = {k: v for k, v in os.environ.items() if k != "OTEL_EXPORTER_OTLP_ENDPOINT"}
        with patch.dict(os.environ, env, clear=True):
            readers = _build_metric_readers()
        assert len(readers) == 1
        assert isinstance(readers[0], PrometheusMetricReader)

    def test_adds_otlp_reader_when_endpoint_set(self):
        from org_gauge import _build_metric_readers

        with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector:4318"}), \
             patch("opentelemetry.exporter.otlp.proto.http.metric_exporter.OTLPMetricExporter") as mock_exporter:
            readers = _build_metric_readers()
        try:
            assert len(readers) == 2
            mock_exporter.assert_called_once()
        finally:
            readers[1].shutdown()


class TestOrgAwareGaugePrometheusExport:
    """Confirms the OTel wiring actually reaches prometheus_client's default
    registry in the exposition format /metrics scrapers expect."""

    def test_gauge_appears_in_prometheus_exposition_format(self):
        gauge = make_gauge("g_export_1", "A test gauge", ["foo"])
        with patch.dict(os.environ, {"ORG_NAME": "export-org"}):
            gauge.labels(foo="bar").set(123)
        output = prometheus_client.generate_latest(prometheus_client.REGISTRY).decode()
        assert "# TYPE g_export_1 gauge" in output
        assert 'g_export_1{foo="bar",org="export-org"} 123.0' in output

    def test_cleared_gauge_disappears_from_exposition_format(self):
        gauge = make_gauge("g_export_2", "A test gauge", ["foo"])
        with patch.dict(os.environ, {"ORG_NAME": "export-org"}):
            gauge.labels(foo="bar").set(1)
        gauge.clear()
        output = prometheus_client.generate_latest(prometheus_client.REGISTRY).decode()
        assert "g_export_2" not in output
