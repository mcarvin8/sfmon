# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

SFMon is a long-running service that monitors a Salesforce org and exposes metrics via a Prometheus `/metrics` endpoint (port 9001). It uses APScheduler for cron-based job scheduling and `simple_salesforce` for SOQL queries and Salesforce API calls. Distributed two ways: a Docker image (`mcarvin8/sfmon`) and a PyPI package (`sfmon`, console script + importable library).

## Commands

```bash
# Run all tests with coverage
pytest tests/ -v --cov=src/sfmon --cov-report=xml --cov-report=term-missing

# Run a single test file
pytest tests/test_orgs.py -v

# Run a single test
pytest tests/test_config.py::test_load_config_with_preset -v

# Install deps (matches CI exactly)
pip install pytest pytest-cov pytest-mock responses simple_salesforce prometheus_client apscheduler pandas cffi opentelemetry-sdk opentelemetry-exporter-prometheus opentelemetry-exporter-otlp-proto-http opentelemetry-instrumentation-logging boto3 genbadge[coverage]

# Build the sdist/wheel locally
pip install build && python -m build
```

There is no build step for running tests — this is pure Python, and pytest's `pythonpath = ["src"]` (see `pyproject.toml`) makes `sfmon` importable without installing it. The Docker image is built from `docker/Dockerfile`; the PyPI package is built/published from `pyproject.toml` via `.github/workflows/release-please.yml`.

## Architecture

### Entry point

`src/sfmon/salesforce_monitoring.py` (`sfmon.salesforce_monitoring:main`) — initializes APScheduler, registers all jobs, starts the Prometheus HTTP server, and blocks forever. Invoked as `python -m sfmon.salesforce_monitoring` (Docker `ENTRYPOINT`) or via the `sfmon` console script (PyPI install). `main()` first parses CLI args: `--once` runs `run_once()` instead — every enabled job (or one job via `--job JOB_ID`) a single time, prints Prometheus exposition text to stdout, exits with 0/1/2 — for CI/cron-triggered checks instead of the daemon. `ALWAYS_ON_JOBS`/`SCHEDULED_JOBS` (module-level) are the single source of truth for the job list, shared by `schedule_tasks()` and `run_once()`.

All internal imports are package-qualified (`from .logger import logger`, `from ..core.gauges import ...`) — `sfmon/` is a real installable package (`src/sfmon/__init__.py`), not a flat script directory. Docker still copies the package to `/app/sfmon/` and runs it with `WORKDIR /app`, so absolute in-container paths like `/app/sfmon/config.json` are unchanged.

### Module layout

| Directory | Purpose |
|-----------|---------|
| `src/sfmon/core/` | Always-on jobs: governor limits, instance/trust health, license usage |
| `src/sfmon/ops/` | Operational metrics: Apex flex queue, async jobs, Bulk API, EPT/APT |
| `src/sfmon/audit/` | Compliance/audit metrics: suspicious activity, deployments, login events, geolocation, sharing, large queries, report exports, forbidden profiles |
| `src/sfmon/tech_debt/` | Tech debt metrics: PMD violations, permission sets, dormant users, Apex API versions, security health, queues/groups, scheduled Apex, dashboards |

### Key shared classes and modules

- `src/sfmon/org_gauge.py` — `OrgGauge` base class. All metrics are Prometheus `Gauge`s with an `org` label. Every collector inherits or instantiates from this.
- `src/sfmon/connection_sf.py` — Salesforce auth (SFDX auth URL) and SOQL execution. All collectors receive a shared connection object.
- `src/sfmon/orgs.py` — resolves org names and their auth URLs (`resolve_auth_url`); plain env var by default, or a secrets backend (`SECRETS_BACKEND=aws` → `src/sfmon/secrets_manager.py`, lazily imported so `boto3` stays optional for non-AWS users).
- `src/sfmon/config.py` — Loads `config.json` (optional), resolves presets, merges `schedules` overrides. Determines which jobs run and at what cadence.
- `src/sfmon/query.py` — Shared SOQL query strings.
- `src/sfmon/constants.py` — Shared constants.

### Scheduling model

Three jobs always run regardless of config: `monitor_salesforce_limits`, `get_salesforce_instance`, `get_salesforce_licenses`.

As soon as a non-empty `schedules` block appears in `config.json`, the app switches to **opt-in mode** — only explicitly listed jobs run. Presets (`ops`, `audit`, `tech-debt`) are a shorthand for listing a focused set of jobs.

File-based collectors (`monitor_pmd_code_smells`, `monitor_minimal_perm_sets`) are always opt-in and require files mounted at specific paths inside the container. They are excluded from the published Docker image via `.dockerignore`.

### Configuration

- Required env: `SALESFORCE_AUTH_URL` (SFDX auth URL from `sf org display --url-only`)
- Optional env: see `docs/ENVIRONMENT.md` — covers port, timeouts, thresholds, compliance lists, PMD paths
- Optional config file: `config.json` mounted at `/app/sfmon/config.json` — see `docs/CONFIGURATION.md` and `config.example.json`

### Testing

All tests live in `tests/`. `conftest.py` provides mock Salesforce connection fixtures. HTTP calls are mocked with the `responses` library. Tests mock the Salesforce connection — there is no live org required for testing. Coverage target is 97%.

### CI

- `unit-tests.yml` — runs pytest + generates `badges/coverage.svg` on push/PR to main
- `update-local-reports.yml` — manually or on schedule, retrieves PMD and minimal perm set reports from a live Salesforce org and commits them to `src/sfmon/tech_debt/` (GitHub and GitLab variants)
- `claude.yml` — Claude Code integration triggered by `@claude` mentions in issues/PRs
