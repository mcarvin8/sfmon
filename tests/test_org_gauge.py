"""Unit tests for org_gauge.OrgAwareGauge"""

import os
import pytest
from unittest.mock import patch
from prometheus_client import CollectorRegistry


def make_gauge(name, documentation, labelnames=None, **kwargs):
    from org_gauge import OrgAwareGauge
    kwargs.setdefault("registry", CollectorRegistry())
    if labelnames is not None:
        return OrgAwareGauge(name, documentation, labelnames, **kwargs)
    return OrgAwareGauge(name, documentation, **kwargs)


def collect_samples(gauge):
    return list(gauge._gauge.collect()[0].samples)


class TestOrgAwareGaugeLabels:
    def test_org_appended_to_label_list(self):
        gauge = make_gauge("g_lbl_1", "doc", ["foo", "bar"])
        assert gauge._original_labelnames == ["foo", "bar"]
        assert gauge._gauge._labelnames == ("foo", "bar", "org")

    def test_no_labelnames_defaults_to_org_only(self):
        gauge = make_gauge("g_lbl_2", "doc")
        assert gauge._original_labelnames == []
        assert gauge._gauge._labelnames == ("org",)

    def test_empty_labelnames_gets_org_only(self):
        gauge = make_gauge("g_lbl_3", "doc", [])
        assert gauge._gauge._labelnames == ("org",)

    def test_labels_injects_org_from_env(self):
        gauge = make_gauge("g_lbl_4", "doc", ["foo"])
        with patch.dict(os.environ, {"ORG_NAME": "prod-org"}):
            gauge.labels(foo="v").set(5)
        sample = next(s for s in collect_samples(gauge) if s.value == 5)
        assert sample.labels["org"] == "prod-org"
        assert sample.labels["foo"] == "v"

    def test_labels_defaults_org_to_empty_string_when_env_unset(self):
        gauge = make_gauge("g_lbl_5", "doc", ["foo"])
        env = {k: v for k, v in os.environ.items() if k != "ORG_NAME"}
        with patch.dict(os.environ, env, clear=True):
            gauge.labels(foo="bar").set(3)
        sample = next(s for s in collect_samples(gauge) if s.value == 3)
        assert sample.labels["org"] == ""

    def test_caller_provided_org_is_not_overridden(self):
        gauge = make_gauge("g_lbl_6", "doc", ["foo"])
        with patch.dict(os.environ, {"ORG_NAME": "env-org"}):
            gauge.labels(foo="val", org="custom-org").set(9)
        sample = next(s for s in collect_samples(gauge) if s.value == 9)
        assert sample.labels["org"] == "custom-org"


class TestOrgAwareGaugePositionalArgs:
    def test_positional_args_converted_to_kwargs(self):
        gauge = make_gauge("g_pos_1", "doc", ["entry_point", "quiddity"])
        with patch.dict(os.environ, {"ORG_NAME": "myorg"}):
            gauge.labels("MyApex.method", "future").set(7)
        sample = next(s for s in collect_samples(gauge) if s.value == 7)
        assert sample.labels["entry_point"] == "MyApex.method"
        assert sample.labels["quiddity"] == "future"
        assert sample.labels["org"] == "myorg"

    def test_mixed_positional_and_keyword_args(self):
        gauge = make_gauge("g_pos_2", "doc", ["a", "b", "c"])
        with patch.dict(os.environ, {"ORG_NAME": "org1"}):
            gauge.labels("x", "y", c="z").set(2)
        sample = next(s for s in collect_samples(gauge) if s.value == 2)
        assert sample.labels["a"] == "x"
        assert sample.labels["b"] == "y"
        assert sample.labels["c"] == "z"
        assert sample.labels["org"] == "org1"


class TestOrgAwareGaugeDirectSet:
    def test_set_on_unlabeled_gauge_uses_org(self):
        gauge = make_gauge("g_set_1", "doc")
        with patch.dict(os.environ, {"ORG_NAME": "myorg"}):
            gauge.set(42)
        sample = collect_samples(gauge)[0]
        assert sample.value == 42
        assert sample.labels["org"] == "myorg"

    def test_set_on_empty_labelnames_uses_org(self):
        gauge = make_gauge("g_set_2", "doc", [])
        with patch.dict(os.environ, {"ORG_NAME": "another-org"}):
            gauge.set(99)
        sample = collect_samples(gauge)[0]
        assert sample.value == 99
        assert sample.labels["org"] == "another-org"


class TestOrgAwareGaugeClear:
    def test_clear_removes_all_child_metrics(self):
        gauge = make_gauge("g_clr_1", "doc", ["foo"])
        with patch.dict(os.environ, {"ORG_NAME": "org1"}):
            gauge.labels(foo="x").set(1)
            gauge.labels(foo="y").set(2)
        gauge.clear()
        assert collect_samples(gauge) == []

    def test_clear_called_on_underlying_gauge(self):
        from unittest.mock import MagicMock
        from org_gauge import OrgAwareGauge
        reg = CollectorRegistry()
        gauge = OrgAwareGauge("g_clr_2", "doc", ["foo"], registry=reg)
        gauge._gauge = MagicMock()
        gauge.clear()
        gauge._gauge.clear.assert_called_once()


class TestOrgAwareGaugeAttributeDelegation:
    def test_getattr_delegates_to_underlying_gauge(self):
        gauge = make_gauge("g_attr_1", "doc", ["foo"])
        # _labelnames is an attribute of the underlying Gauge
        assert hasattr(gauge._gauge, "_labelnames")
        assert gauge._labelnames == ("foo", "org")
