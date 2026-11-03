"""Unit tests for custom_metrics (config-defined SOQL gauges)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from sfmon import custom_metrics as cm
from sfmon import salesforce_monitoring as sm
from sfmon.org_gauge import set_current_org


def entry(metric_name, **overrides):
    base = {"name": metric_name, "query": "SELECT COUNT() FROM Account", "schedule": "minute=0"}
    base.update(overrides)
    return base


def parse_one(name, **overrides):
    return cm.parse_custom_metrics([entry(name, **overrides)])[0]


def series(metric, org="default"):
    """{labels-without-org: value} for one org of a metric's gauge."""
    out = {}
    for key, value in cm._gauge(metric)._values.items():
        labels = dict(key)
        if labels.pop("org") == org:
            out[tuple(sorted(labels.items()))] = value
    return out


def write_config(tmp_path, monkeypatch, config):
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setenv("CONFIG_FILE_PATH", str(path))


class TestParse:
    def test_none_and_empty_mean_no_metrics(self):
        assert cm.parse_custom_metrics(None) == []
        assert cm.parse_custom_metrics([]) == []

    def test_minimal_entry_defaults(self):
        metric = parse_one("p_minimal")
        assert metric.metric_name == "sfmon_custom_p_minimal"
        assert metric.job_id == "custom_p_minimal"
        assert metric.schedule == {"minute": "0"}
        assert metric.api == "rest"
        assert metric.value_field is None
        assert metric.labels == {}
        assert metric.orgs is None
        assert metric.max_series == cm.DEFAULT_MAX_SERIES

    def test_full_entry(self):
        metric = parse_one(
            "p_full",
            description="d",
            query="  SELECT Status s, COUNT(Id) n FROM Case GROUP BY Status  ",
            value_field="n",
            labels={"status": "s"},
            api="tooling",
            orgs=["prod"],
            max_series=10,
            schedule="*/5",
        )
        assert metric.query.startswith("SELECT")
        assert metric.labels == {"status": "s"}
        assert metric.orgs == ("prod",)
        assert metric.schedule == {"minute": "*/5"}

    def test_disabled_schedule_is_valid(self):
        assert parse_one("p_disabled", schedule="disabled").schedule is None

    def test_not_a_list(self):
        with pytest.raises(cm.CustomMetricConfigError, match="must be a list"):
            cm.parse_custom_metrics({"name": "x"})

    @pytest.mark.parametrize(
        "bad, message",
        [
            ({"name": "Bad-Name"}, "snake_case"),
            ({"name": "sfmon_thing"}, "drop the 'sfmon_' prefix"),
            ({"query": "DELETE FROM Account"}, "SOQL SELECT"),
            ({"query": None}, "SOQL SELECT"),
            ({"schedule": None}, "'schedule' is required"),
            ({"schedule": "every tuesday"}, "invalid schedule"),
            ({"schedule": "minute=99"}, "invalid schedule"),
            ({"api": "graphql"}, "'api' must be"),
            ({"lables": {}}, "unknown keys"),
            ({"value_field": ""}, "'value_field' must be"),
            ({"labels": ["status"], "value_field": "n"}, "'labels' must be an object"),
            ({"labels": {"Status": "s"}, "value_field": "n"}, "must be snake_case"),
            ({"labels": {"org": "s"}, "value_field": "n"}, "is reserved"),
            ({"labels": {"status": ""}, "value_field": "n"}, "needs a field path"),
            ({"labels": {"status": "s"}}, "needs 'value_field'"),
            ({"orgs": "prod"}, "'orgs' must be a list"),
            ({"max_series": 0}, "positive integer"),
            ({"max_series": True}, "positive integer"),
            ({"description": 5}, "'description' must be"),
        ],
    )
    def test_invalid_entries(self, bad, message):
        with pytest.raises(cm.CustomMetricConfigError, match=message):
            cm.parse_custom_metrics([entry("p_invalid", **bad)])

    def test_non_object_entry(self):
        with pytest.raises(cm.CustomMetricConfigError, match="must be an object"):
            cm.parse_custom_metrics(["nope"])

    def test_duplicate_names(self):
        with pytest.raises(cm.CustomMetricConfigError, match="duplicate name"):
            cm.parse_custom_metrics([entry("p_dup"), entry("p_dup")])

    def test_reports_every_error_at_once(self):
        with pytest.raises(cm.CustomMetricConfigError) as exc:
            cm.parse_custom_metrics(
                [entry("p_err_a", api="x"), entry("p_err_b", schedule=None)]
            )
        assert "p_err_a" in str(exc.value) and "p_err_b" in str(exc.value)


class TestResolveField:
    def test_exact_case_insensitive_and_relationship(self):
        record = {"Name": "Acme", "Owner": {"Profile": {"Name": "Admin"}}}
        assert cm.resolve_field(record, "Name") == "Acme"
        assert cm.resolve_field(record, "name") == "Acme"
        assert cm.resolve_field(record, "owner.profile.name") == "Admin"

    def test_missing_and_null_relationship(self):
        assert cm.resolve_field({"Owner": None}, "Owner.Name") is None
        assert cm.resolve_field({}, "Nope") is None


class TestCollect:
    def test_count_query_uses_total_size(self, mock_sf):
        set_current_org("default")
        mock_sf.query_all.return_value = {"records": [], "totalSize": 42}
        metric = parse_one("c_count")
        metric.collect(mock_sf)
        assert series(metric) == {(): 42.0}
        mock_sf.query_all.assert_called_once()

    def test_tooling_api(self, mock_sf):
        set_current_org("default")
        mock_sf.toolingexecute.return_value = {"records": [{}, {}], "totalSize": 2}
        metric = parse_one("c_tooling", api="tooling", query="SELECT Id FROM ApexClass")
        metric.collect(mock_sf)
        assert series(metric) == {(): 2.0}
        mock_sf.query_all.assert_not_called()

    def test_grouped_rows_become_labelled_series(self, mock_sf):
        set_current_org("default")
        mock_sf.query_all.return_value = {
            "totalSize": 3,
            "records": [
                {"attributes": {}, "status": "Draft", "total": 4},
                {"attributes": {}, "status": "Approved", "total": "7"},
                {"attributes": {}, "status": None, "total": 1},
            ],
        }
        metric = parse_one(
            "c_grouped", value_field="total", labels={"status": "status"}
        )
        metric.collect(mock_sf)
        assert series(metric) == {
            (("status", "Draft"),): 4.0,
            (("status", "Approved"),): 7.0,
            (("status", ""),): 1.0,
        }

    def test_non_numeric_and_null_values_are_skipped(self, mock_sf):
        set_current_org("default")
        mock_sf.query_all.return_value = {
            "records": [
                {"s": "a", "n": "abc"},
                {"s": "b", "n": None},
                {"s": "c", "n": True},
            ]
        }
        metric = parse_one("c_skip", value_field="n", labels={"s": "s"})
        metric.collect(mock_sf)
        assert series(metric) == {(("s", "c"),): 1.0}

    def test_duplicate_labels_last_row_wins(self, mock_sf):
        set_current_org("default")
        mock_sf.query_all.return_value = {"records": [{"s": "a", "n": 1}, {"s": "a", "n": 2}]}
        metric = parse_one("c_dupe_rows", value_field="n", labels={"s": "s"})
        metric.collect(mock_sf)
        assert series(metric) == {(("s", "a"),): 2.0}

    def test_max_series_truncates(self, mock_sf):
        set_current_org("default")
        mock_sf.query_all.return_value = {
            "records": [{"s": str(i), "n": i} for i in range(5)]
        }
        metric = parse_one("c_cap", value_field="n", labels={"s": "s"}, max_series=2)
        metric.collect(mock_sf)
        assert len(series(metric)) == 2

    def test_stale_series_removed_on_next_run(self, mock_sf):
        set_current_org("default")
        metric = parse_one("c_stale", value_field="n", labels={"s": "s"})
        mock_sf.query_all.return_value = {"records": [{"s": "a", "n": 1}]}
        metric.collect(mock_sf)
        mock_sf.query_all.return_value = {"records": [{"s": "b", "n": 2}]}
        metric.collect(mock_sf)
        assert series(metric) == {(("s", "b"),): 2.0}

    def test_failed_query_clears_org_series(self, mock_sf):
        set_current_org("default")
        metric = parse_one("c_fail")
        mock_sf.query_all.return_value = {"records": [], "totalSize": 5}
        metric.collect(mock_sf)
        mock_sf.query_all.side_effect = RuntimeError("boom")
        metric.collect(mock_sf)
        assert series(metric) == {}

    def test_one_org_run_keeps_other_orgs_series(self, mock_sf):
        metric = parse_one("c_fleet")
        set_current_org("prod")
        mock_sf.query_all.return_value = {"records": [], "totalSize": 1}
        metric.collect(mock_sf)
        set_current_org("uat")
        mock_sf.query_all.return_value = {"records": [], "totalSize": 2}
        metric.collect(mock_sf)
        assert series(metric, "prod") == {(): 1.0}
        assert series(metric, "uat") == {(): 2.0}


class TestScheduleFor:
    def test_uses_own_schedule(self):
        metric = parse_one("s_own")
        assert metric.schedule_for("default", config={"schedules": {}}) == {"minute": "0"}

    def test_orgs_filter(self):
        metric = parse_one("s_orgs", orgs=["prod"])
        config = {"schedules": {}}
        assert metric.schedule_for("prod", config=config) == {"minute": "0"}
        assert metric.schedule_for("uat", config=config) is None

    def test_org_override_can_disable_or_reschedule(self):
        metric = parse_one("s_override")
        config = {
            "schedules": {},
            "org_overrides": {
                "uat": {"schedules": {"custom_s_override": "disabled"}},
                "dev": {"schedules": {"custom_s_override": "*/30"}},
            },
        }
        assert metric.schedule_for("uat", config=config) is None
        assert metric.schedule_for("dev", config=config) == {"minute": "*/30"}
        assert metric.schedule_for("prod", config=config) == {"minute": "0"}


class TestLoad:
    def test_loads_from_config_and_caches(self, tmp_path, monkeypatch):
        write_config(tmp_path, monkeypatch, {"custom_metrics": [entry("l_cached")]})
        first = cm.load_custom_metrics()
        assert [m.name for m in first] == ["l_cached"]
        assert cm.load_custom_metrics() is first
        assert "sfmon_custom_l_cached" in cm._gauges

    def test_no_config_file_means_no_metrics(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CONFIG_FILE_PATH", str(tmp_path / "missing.json"))
        assert cm.load_custom_metrics() == []

    def test_invalid_config_raises(self, tmp_path, monkeypatch):
        write_config(tmp_path, monkeypatch, {"custom_metrics": [entry("l_bad", api="x")]})
        with pytest.raises(cm.CustomMetricConfigError):
            cm.load_custom_metrics()

    def test_warns_on_org_not_in_fleet(self, tmp_path, monkeypatch):
        write_config(
            tmp_path,
            monkeypatch,
            {"orgs": ["prod"], "custom_metrics": [entry("l_warn", orgs=["prd"])]},
        )
        with patch.object(cm.logger, "warning") as warn:
            cm.load_custom_metrics()
        assert "prd" in warn.call_args[0]


class TestRunOnceIntegration:
    def test_custom_job_runs_when_scheduled(self, tmp_path, monkeypatch):
        write_config(
            tmp_path,
            monkeypatch,
            {"schedules": {"get_salesforce_instance": "disabled"},
             "custom_metrics": [entry("r_sched")]},
        )
        with patch("sfmon.orgs.build_connections", return_value={"default": MagicMock()}), \
             patch.object(sm, "get_always_on_config", return_value=None), \
             patch.object(sm, "get_schedule_config", return_value=None), \
             patch.object(sm, "_run_job", return_value=True) as mock_run:
            assert sm.run_once() == 0
        assert [c[0][4] for c in mock_run.call_args_list] == ["custom_r_sched"]

    def test_job_filter_selects_custom_job_and_respects_orgs(self, tmp_path, monkeypatch):
        write_config(
            tmp_path,
            monkeypatch,
            {"custom_metrics": [entry("r_filter", schedule="disabled", orgs=["prod"])]},
        )
        conns = {"prod": MagicMock(), "uat": MagicMock()}
        with patch("sfmon.orgs.build_connections", return_value=conns), \
             patch.object(sm, "_run_job", return_value=True) as mock_run:
            assert sm.run_once(job_filter="custom_r_filter") == 0
        assert [c[0][0] for c in mock_run.call_args_list] == ["prod"]

    def test_invalid_config_returns_2_without_connecting(self, tmp_path, monkeypatch):
        write_config(tmp_path, monkeypatch, {"custom_metrics": [{"name": "r_bad"}]})
        with patch("sfmon.orgs.build_connections") as mock_build:
            assert sm.run_once() == 2
        mock_build.assert_not_called()

    def test_failed_custom_job_returns_1(self, tmp_path, monkeypatch):
        write_config(tmp_path, monkeypatch, {"custom_metrics": [entry("r_failed")]})
        with patch("sfmon.orgs.build_connections", return_value={"default": MagicMock()}), \
             patch.object(sm, "get_always_on_config", return_value=None), \
             patch.object(sm, "get_schedule_config", return_value=None), \
             patch.object(sm, "_run_job", return_value=False):
            assert sm.run_once() == 1
