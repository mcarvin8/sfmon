# Salesforce Monitoring (SFMon)

[![Docker Image Version](https://img.shields.io/docker/v/mcarvin8/sfmon?sort=date)](https://hub.docker.com/r/mcarvin8/sfmon)
[![Docker Pulls](https://img.shields.io/docker/pulls/mcarvin8/sfmon)](https://hub.docker.com/r/mcarvin8/sfmon)
[![Docker Image Size](https://img.shields.io/docker/image-size/mcarvin8/sfmon)](https://hub.docker.com/r/mcarvin8/sfmon)
[![PyPI Version](https://img.shields.io/pypi/v/sfmon)](https://pypi.org/project/sfmon/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/sfmon)](https://pypi.org/project/sfmon/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/sfmon)](https://pypi.org/project/sfmon/)
[![GitHub Marketplace](https://img.shields.io/badge/marketplace-Run%20Salesforce%20Monitoring-blue?logo=github)](https://github.com/marketplace/actions/run-salesforce-monitoring)
![Coverage](https://raw.githubusercontent.com/mcarvin8/sfmon/refs/heads/main/badges/coverage.svg)

SFMon watches your Salesforce orgs and exposes what it finds as Prometheus metrics on `:9001/metrics`, so Salesforce shows up in the same dashboards and alerts as the rest of your infrastructure. It's one process with no database and no UI: your Prometheus-compatible backend stores the history, and Grafana shows it.

It's built for SRE and DevOps teams that already run Prometheus (or Victoria Metrics, Grafana Cloud, an OTel Collector) and look after one or more Salesforce orgs.

> [!WARNING]
> **Upgrading from v3?** v4 renamed every metric to start with `sfmon_`. Values are unchanged. See the [migration guide](https://github.com/mcarvin8/sfmon/blob/main/docs/METRICS_MIGRATION.md) for the old → new names and optional rules that keep v3 queries working.

## What you get

| Area | What's measured |
|------|-----------------|
| **Governor limits** | Every org limit (API requests, bulk queries, data storage, ...) as used, max and % used, every 5 minutes |
| **Apex health** | Flex queue depth, long-running requests, concurrency errors, uncaught exceptions, async job status |
| **Bulk API** | Daily and hourly activity across Bulk API 1.0 and 2.0 |
| **Licenses** | User licenses, permission set licenses and usage-based entitlements: used vs. total |
| **Instance & Trust** | Your org's pod, active incidents from trust.salesforce.com, scheduled maintenance |
| **Security & compliance** | Forbidden profile assignments, logins, suspicious audit trail activity, report exports, large SOQL queries, org-wide sharing changes |
| **Tech debt** | Dormant users, deprecated Apex API versions, unused permission sets, workflow rules, empty queues and groups, PMD violations |
| **Deployments** | Deployment and validation status and timing |
| **SFMon itself** | Whether each job's last run succeeded, when it last succeeded, and how long it took |

All of these run on default schedules with no config file. The exceptions are PMD and minimal permission set reports, which need files you generate ([Advanced setup](https://github.com/mcarvin8/sfmon/blob/main/docs/ADVANCED.md)).

## Quick start

### 1. Get an auth URL for the org

Use a dedicated monitoring user with API access. Making it an **API Only User** whose password never expires stops it from being locked out. It needs read access to whatever you want monitored; step 5 shows how to spot anything it can't see.

Log in to the org as that user with the Salesforce CLI, then print its auth URL:

```bash
sf org login web --alias sfmon-prod
sf org auth show-sfdx-auth-url --target-org sfmon-prod --no-prompt
```

The URL (`force://...`) is a long-lived credential: store it as a secret. The CLI is only needed for this step; SFMon doesn't use it at runtime. The URL is only available for orgs logged in with `sf org login web`.

### 2. Run SFMon

Run the Docker image with the environment variables:

```bash
docker run -d --name sfmon -p 9001:9001 \
  -e SALESFORCE_AUTH_URL="force://..." \
  -e ORG_NAME="production" \
  mcarvin8/sfmon:latest
```

`ORG_NAME` becomes the `org` label on every metric.

Prefer not to use Docker? Install the package, set environment variables, and run the Python module:

```bash
pip install sfmon
SALESFORCE_AUTH_URL="force://PlatformCLI::..." 
ORG_NAME="production" 
python3 -m sfmon.salesforce_monitoring
```

Check it's up: `curl http://localhost:9001/metrics`

### 3. Scrape it

Add SFMon to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: sfmon
    static_configs:
      - targets: ["<host>:9001"]
```

No Prometheus to scrape with? Set `OTEL_EXPORTER_OTLP_ENDPOINT` and SFMon pushes metrics and logs over OTLP instead ([details](https://github.com/mcarvin8/sfmon/blob/main/docs/ENVIRONMENT.md#optional--otlp-push)).

### 4. Import the dashboards

Import the JSON files in [`grafana/`](https://github.com/mcarvin8/sfmon/tree/main/grafana) into Grafana and point them at your Prometheus data source. There are three: monitoring (limits, licenses, Apex, Bulk API, page times), audit, and tech debt.

### 5. Check every job can do its work

After the first run (a few minutes), any job that failed or couldn't run its queries reports `0` here:

```promql
sfmon_job_success == 0
```

The usual cause is the monitoring user lacking access to an object or event log. SFMon's logs show the job and the error Salesforce returned. Fix the permission and the next run reports `1`.

## Next steps

| To... | See |
|-------|-----|
| Alert in PromQL, alert on SFMon itself, or post to Slack without Alertmanager | [Alerting](https://github.com/mcarvin8/sfmon/blob/main/docs/ALERTING.md) |
| Monitor several orgs from one container | [Multiple orgs](https://github.com/mcarvin8/sfmon/blob/main/docs/MULTI_ORG.md) |
| Run once from a CI cron job or GitHub Action instead of a daemon | [One-shot mode](https://github.com/mcarvin8/sfmon/blob/main/docs/ONE_SHOT.md) |
| Add your own SOQL metrics (CPQ, custom objects) without building an image | [Custom metrics](https://github.com/mcarvin8/sfmon/blob/main/docs/CUSTOM_METRICS.md) |
| Run only some jobs (`ops`, `audit`, `tech-debt` presets) or change schedules | [Configuration](https://github.com/mcarvin8/sfmon/blob/main/docs/CONFIGURATION.md) |
| Tune thresholds and timeouts, or read the auth URL from AWS Secrets Manager | [Environment variables](https://github.com/mcarvin8/sfmon/blob/main/docs/ENVIRONMENT.md) |
| Add PMD and permission-set reports, or build your own image | [Advanced setup](https://github.com/mcarvin8/sfmon/blob/main/docs/ADVANCED.md) |
| Move dashboards and alerts from v3 metric names | [Migration guide](https://github.com/mcarvin8/sfmon/blob/main/docs/METRICS_MIGRATION.md) |

**Metrics vs. logs:** metrics answer "is something wrong right now" and keep labels low-cardinality. The per-record detail behind them (which user, which deployment, login coordinates) goes to stdout as JSON log lines under an `event` field, for Loki, CloudWatch Logs, Datadog or any JSON log pipeline.

## How it compares

| | SFMon | Salesforce proactive monitoring (paid) | sfdx-hardis org monitoring |
|--|-------|----------------------------------------|---------------------------|
| **Model** | Always-on process serving `/metrics`, or a scheduled CI job via `--once` | Salesforce TAM/CSM engagement + event log files | Scheduled CI jobs |
| **Output** | Time-series metrics | Salesforce reports and guided reviews | Git diffs, Slack/Teams notifications, pipeline artifacts |
| **Alerting** | PromQL + Alertmanager, or built-in Slack | Salesforce notifications and reviews | Slack/Teams from CI |
| **Data stays in your stack** | Yes | No | Partly |
| **Cost** | Free; you run the container or CI job | Paid add-on | Free; you run the CI job |
| **Best for** | Teams on Prometheus who want Salesforce as another scrape target | Teams buying Salesforce-managed oversight | Metadata backup and drift detection in CI |

SFMon and sfdx-hardis work well together: Hardis handles metadata backup and change detection, SFMon provides continuous time series.

## Authors

Originally developed by **Deep Suthar** and **Matt Carvin** (e.g. ECS / Kubernetes at Avalara).
