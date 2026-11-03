"""Guards for metric naming: one sfmon_ prefix, snake_case labels, and no
dashboard, docs PromQL example or compat rule pointing at a metric that doesn't exist."""

import importlib
import json
import pathlib
import re

import pytest

from sfmon.org_gauge import OrgAwareGauge

ROOT = pathlib.Path(__file__).resolve().parent.parent
GAUGE_MODULES = [
    "sfmon.core.gauges",
    "sfmon.audit.gauges",
    "sfmon.ops.gauges",
    "sfmon.tech_debt.gauges",
    "sfmon.self_metrics",
]
SNAKE_CASE = re.compile(r"[a-z][a-z0-9_]*")
SFMON_NAME = re.compile(r"(?<![A-Za-z0-9_])sfmon_(?:[a-z0-9_]|\$\{interval\})+")
INTERVALS = ("hourly", "daily")


def _gauges():
    gauges = []
    for module_name in GAUGE_MODULES:
        module = importlib.import_module(module_name)
        gauges += [v for v in vars(module).values() if isinstance(v, OrgAwareGauge)]
    return gauges


GAUGES = _gauges()
DEFINED = {g.name for g in GAUGES}


def _referenced(text):
    """sfmon_ metric names in text, expanding Grafana's ${interval} variable."""
    names = set()
    for match in SFMON_NAME.findall(text):
        if "${interval}" in match:
            names |= {match.replace("${interval}", i) for i in INTERVALS}
        else:
            names.add(match)
    return names


def _dashboard_queries(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("expr", "query", "definition") and isinstance(value, str):
                yield value
            else:
                yield from _dashboard_queries(value)
    elif isinstance(node, list):
        for value in node:
            yield from _dashboard_queries(value)


def test_gauge_modules_define_every_gauge():
    assert len(GAUGES) == len(DEFINED) >= 80


@pytest.mark.parametrize("gauge", GAUGES, ids=lambda g: g.name)
def test_gauge_name_has_sfmon_prefix(gauge):
    assert gauge.name.startswith("sfmon_")
    assert SNAKE_CASE.fullmatch(gauge.name)


@pytest.mark.parametrize("gauge", GAUGES, ids=lambda g: g.name)
def test_gauge_labels_are_snake_case(gauge):
    bad = [label for label in gauge._original_labelnames if not SNAKE_CASE.fullmatch(label)]
    assert not bad


@pytest.mark.parametrize(
    "dashboard", sorted((ROOT / "grafana").glob("*.json")), ids=lambda p: p.name
)
def test_dashboard_queries_use_defined_metrics(dashboard):
    queries = _dashboard_queries(json.loads(dashboard.read_text(encoding="utf-8")))
    referenced = set().union(*(_referenced(q) for q in queries))
    assert referenced, "dashboard has no sfmon_ queries"
    assert referenced <= DEFINED, sorted(referenced - DEFINED)


@pytest.mark.parametrize(
    "doc",
    [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))],
    ids=lambda p: p.name,
)
def test_promql_examples_use_defined_metrics(doc):
    blocks = re.findall(r"```promql(.*?)```", doc.read_text(encoding="utf-8"), re.S)
    referenced = set().union(set(), *(_referenced(b) for b in blocks))
    assert referenced <= DEFINED, sorted(referenced - DEFINED)


def test_docs_have_promql_examples():
    docs = [ROOT / "README.md", *(ROOT / "docs").glob("*.md")]
    assert any("```promql" in d.read_text(encoding="utf-8") for d in docs)


def test_compat_rules_record_from_defined_metrics():
    rules = (ROOT / "prometheus" / "sfmon-v3-compat.rules.yml").read_text(encoding="utf-8")
    records = re.findall(r"- record: (\S+)", rules)
    exprs = re.findall(r"expr: '(.*)'", rules)
    assert len(records) == len(exprs) == len(DEFINED - {g.name for g in GAUGES if g.name.startswith("sfmon_job_")})
    assert set().union(*(_referenced(e) for e in exprs)) <= DEFINED
    assert not set(records) & DEFINED
