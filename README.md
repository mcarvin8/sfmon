# Salesforce Monitoring (SFMon)

[![Docker Image Version](https://img.shields.io/docker/v/mcarvin8/sfmon?sort=date)](https://hub.docker.com/r/mcarvin8/sfmon)
[![Docker Pulls](https://img.shields.io/docker/pulls/mcarvin8/sfmon)](https://hub.docker.com/r/mcarvin8/sfmon)
[![Docker Image Size](https://img.shields.io/docker/image-size/mcarvin8/sfmon)](https://hub.docker.com/r/mcarvin8/sfmon)
[![PyPI Version](https://img.shields.io/pypi/v/sfmon)](https://pypi.org/project/sfmon/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/sfmon)](https://pypi.org/project/sfmon/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/sfmon)](https://pypi.org/project/sfmon/)
![Coverage](https://raw.githubusercontent.com/mcarvin8/sfmon/refs/heads/main/badges/coverage.svg)

SFMon is a **long-running Python application** that connects to your Salesforce org(s) on a schedule and exposes a **standard `/metrics` endpoint** compatible with Prometheus — so you can monitor your orgs with the same tech stack as the rest of your infrastructure.

Metrics are instrumented with OpenTelemetry and structured logs are emitted as JSON; both can optionally **push** over OTLP instead of only being scraped/tailed — see [Metrics and logs](#metrics-and-logs).

- [How it works](#how-it-works)
- [Who is this for](#who-is-this-for)
- [What you get](#what-you-get)
- [Quick start](#quick-start)
  - [Alternative: pip install](#alternative-pip-install)
- [Multiple orgs](#multiple-orgs)
  - [Fleet mode (one container, several orgs)](#fleet-mode-one-container-several-orgs)
  - [One container per org (alternate)](#one-container-per-org-alternate)
- [Metrics and logs](#metrics-and-logs)
- [Alerting in PromQL](#alerting-in-promql)
  - [Built-in Slack alerting (optional, no Alertmanager required)](#built-in-slack-alerting-optional-no-alertmanager-required)
- [One-shot mode — run from a CI cron job instead of a daemon](#one-shot-mode--run-from-a-ci-cron-job-instead-of-a-daemon)
- [Presets — scope down without a full config](#presets--scope-down-without-a-full-config)
- [How it compares](#how-it-compares)
- [PMD + minimal permission sets (optional, file-based)](#pmd--minimal-permission-sets-optional-file-based)
- [When you need your own image](#when-you-need-your-own-image)
- [Grafana](#grafana)
- [Authors](#authors)

---

## How it works

One process, no database, no UI:

1. On startup SFMon authenticates to your org (OAuth2 refresh token flow) and starts an internal **APScheduler** cron loop.
2. Each collector job runs on its own schedule (every 5 minutes, hourly, or once daily off-peak — see [Presets](#presets--scope-down-without-a-full-config)), queries the org via SOQL/REST/Tooling API, and sets Prometheus gauges.
3. Those gauges are served on **`:9001/metrics`**, forever, until Prometheus (or whatever scrapes you) pulls them.

There's no persistence and no historical storage inside SFMon itself — your Prometheus-compatible backend owns the time series. Restarting it just re-authenticates and resumes the schedule.

---

## Who is this for

SFMon is aimed at **SRE and DevOps teams** who already operate a Prometheus-compatible observability stack (Prometheus, Victoria Metrics, Grafana Cloud, or an OTel Collector pipeline)  and are also responsible for one or more Salesforce orgs. If you define alerts in PromQL, route pages through Alertmanager, and want Salesforce signals to behave exactly like any other scrape target — this is for you. Don't run a scrape-based stack at all? Push metrics and logs over OTLP instead — see [Metrics and logs](#metrics-and-logs).

It is **not** a Salesforce admin tool. It has no UI of its own; all visibility comes from your existing observability stack.

---

## What you get

| Category | What is measured |
|----------|-----------------|
| **Governor limits** | All org limits (API requests, bulk queries, data storage, etc.) — usage %, used, and max, every 5 minutes |
| **Apex health** | Flex queue depth, long-running requests, concurrency errors, uncaught exceptions, async job status and summaries |
| **Bulk API** | Daily summaries and hourly in-flight activity across Bulk API 1.0 and 2.0 |
| **Licenses** | User licenses, permission set licenses, and usage-based entitlements — consumed vs. total, % used |
| **Instance & trust** | Your org's pod, active incidents from trust.salesforce.com, and scheduled maintenance windows |
| **Security & compliance** | Forbidden profile assignments, login volumes, geolocation anomalies, suspicious audit trail activity, report exports, large SOQL queries, org-wide sharing settings |
| **Tech debt** | Dormant users (Salesforce + portal), deprecated Apex API versions, unassigned/minimal permission sets, workflow rules, empty queues/groups, PMD static analysis violations |
| **Deployments** | In-flight metadata deployment status |

Everything runs on a default schedule with no config file required. See **[docs/CONFIGURATION.md](https://github.com/mcarvin8/sfmon/blob/main/docs/CONFIGURATION.md)** to scope down to a preset or tune individual jobs.

---

## Quick start

**Prerequisites:** 

On your local machine, you need to have the Salesforce CLI (`sf`) installed and logged in to the target org(s) via `sf org login web` in order to create the auth URLs. The monitoring user in each Salesforce org must have API access enabled and have the approriate permissions to monitor the various metrics. Preferably, the monitoring user should have the "Password Does Not Expire" and "Api Only User" system permissions granted either via a profile or permission set.

SFMon itself doesn't use the Salesforce CLI at runtime — it only needs the auth URLs that you will provide to the app either via enviornment variables or AWS secrets manager.

1. **Get your auth URL:** `sf org display --url-only`
2. **Run:**

```bash
docker run -d \
  --name sfmon \
  -p 9001:9001 \
  -e SALESFORCE_AUTH_URL="force://PlatformCLI::..." \
  -e ORG_NAME="production" \
  mcarvin8/sfmon:latest
```

3. **Verify:** `curl http://localhost:9001/metrics`
4. **Scrape** — add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: sfmon
    static_configs:
      - targets: ["<host>:9001"]
```

No config file is required: all collectors run on **default schedules** out of the box.

### Alternative: pip install

Prefer running on bare metal/VM instead of Docker, or want to import individual collectors in your own scripts? SFMon is also published to PyPI:

```bash
pip install sfmon
SALESFORCE_AUTH_URL="force://PlatformCLI::..." ORG_NAME="production" sfmon
```

The `sfmon` console script runs the same always-on daemon as the Docker image. `CONFIG_FILE_PATH` defaults to `/app/sfmon/config.json` (the Docker path) — set it explicitly for non-Docker installs. `sfmon` is also an importable library, e.g. `from sfmon.core.limits import salesforce_limits_descriptions`.

Optional tuning:
- **Environment variables** (timeouts, org label, compliance lists, thresholds, log level) → **[docs/ENVIRONMENT.md](https://github.com/mcarvin8/sfmon/blob/main/docs/ENVIRONMENT.md)**
- **Config file** (schedules, presets, disable jobs, `exclude_users`) → **[docs/CONFIGURATION.md](https://github.com/mcarvin8/sfmon/blob/main/docs/CONFIGURATION.md)** · template **`config.example.json`**
- **Secrets backend** — fetch `SALESFORCE_AUTH_URL`/`SALESFORCE_AUTH_URL_<NAME>` from AWS Secrets Manager instead of the environment (`SECRETS_BACKEND=aws`) → **[docs/ENVIRONMENT.md](https://github.com/mcarvin8/sfmon/blob/main/docs/ENVIRONMENT.md#optional--secrets-backend)**

---

## Multiple orgs

Two ways to monitor more than one org. Both label every metric with `org` so a single Prometheus-compatible backend can scrape and filter/aggregate across orgs in PromQL.

### Fleet mode (one container, several orgs)

Add an `orgs` array to `config.json` and the same container polls every org on its own schedule:

```json
{
  "orgs": ["prod", "sandbox-uat"],
  "schedules": { "monitor_salesforce_limits": "*/5" },
  "org_overrides": {
    "sandbox-uat": { "schedules": { "monitor_salesforce_limits": "*/15" } }
  }
}
```

Each name resolves to a `SALESFORCE_AUTH_URL_<NAME>` env var (uppercased, non-alphanumerics → `_`):

```bash
docker run -d \
  --name sfmon \
  -p 9001:9001 \
  -v /host/path/config.json:/app/sfmon/config.json \
  -e SALESFORCE_AUTH_URL_PROD="force://PlatformCLI::...@prod.my.salesforce.com" \
  -e SALESFORCE_AUTH_URL_SANDBOX_UAT="force://PlatformCLI::...@sandbox-uat.my.salesforce.com" \
  mcarvin8/sfmon:latest
```

`org_overrides` is optional and lets one org diverge from the fleet-wide `schedules`. An org whose credentials fail to authenticate is logged and skipped at startup — it doesn't block the rest of the fleet. `ORG_NAME` is ignored once `orgs` is set. See **[docs/CONFIGURATION.md](https://github.com/mcarvin8/sfmon/blob/main/docs/CONFIGURATION.md#fleet-mode--multiple-orgs)** · template **`config.example.fleet.json`**.

### One container per org (alternate)

Run a separate container per org, each with a distinct `ORG_NAME` and `SALESFORCE_AUTH_URL`:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: sfmon
    static_configs:
      - targets: ["sfmon-prod:9001"]
        labels: { org: "production" }
      - targets: ["sfmon-uat:9001"]
        labels: { org: "uat" }
```

Prefer this when you want full process/resource isolation per org (independent restarts, separate resource limits) rather than a shared scheduler.

---

## Metrics and logs

Two output shapes, matched to two different questions:

- **Metrics** (`:9001/metrics`) answer *"is something wrong right now"* — governor limit %, license usage, active incidents, aggregate counts of suspicious activity by action/section/user group. Low-cardinality labels only.
- **Logs** (stdout, JSON lines) answer *"who did it and what exactly happened"* — the per-record detail behind those aggregates: user, timestamp, display text, deployment IDs, login coordinates. Anything that would otherwise blow up metric cardinality goes here instead, under a structured `event` field. Pipe stdout to any log backend that reads JSON (Loki, Vector, Fluent Bit, CloudWatch Logs, Datadog Logs).

Both default to pull/tail with no extra setup: metrics are scraped from `/metrics`, logs are read from container stdout. If you'd rather **push** — no Prometheus in your stack, or the container sits somewhere scraping is awkward — set `OTEL_EXPORTER_OTLP_ENDPOINT` and both metrics and logs also push to an OTLP collector or backend (Datadog, Honeycomb, Grafana Alloy, an OTel Collector, ...) in addition to `/metrics` and stdout. Unset, behavior is unchanged. See **[docs/ENVIRONMENT.md](docs/ENVIRONMENT.md#optional--otlp-push)**.

No traces — there's no request-tracing use case here, so that OTel signal isn't used.

---

## Alerting in PromQL

Because metrics live in Prometheus, alerts are just PromQL rules — same toolchain as the rest of your stack:

```promql
# Daily API limit over 80 % consumed
sfmon_api_usage_percentage{limit_name="DailyApiRequests"} > 80

# Active incident on this org's pod
sfmon_incident_gauge{environment="production"} == 1

# User license saturation
sfmon_percent_user_licenses_used{license_name="Salesforce"} > 90
```

Route these through Alertmanager with the same receivers (PagerDuty, Slack, etc.) you use for every other service.

### Built-in Slack alerting (optional, no Alertmanager required)

For teams that don't run a full PromQL/Alertmanager stack, SFMon can also post directly to a Slack incoming webhook. Set `SLACK_WEBHOOK_URL` and it's on; leave it unset and there's no behavior change at all (no cache reads/writes, no HTTP calls).

Alerts are edge-triggered — a Slack message fires once when a breach opens and once when it resolves, not on every scheduler tick while it stays active — using an on-disk cache (`SLACK_ALERT_CACHE_DIR`) keyed per org so state survives both the long-lived daemon and `--once` CI-cron restarts.

Currently wired into governor limits (`LIMIT_ALERT_THRESHOLD_PERCENT`, default `80`), Salesforce Trust API incidents (an active incident on your org's pod posts on open and again on resolve), license seat usage (`LICENSE_ALERT_THRESHOLD_PERCENT`, default `90`), the org-wide Apex character limit (`APEX_CHARACTER_ALERT_THRESHOLD_PERCENT`, default `80`), and Apex Flex Queue depth (`FLEX_QUEUE_ALERT_THRESHOLD_PERCENT`, default `80`, `critical` once the queue actually hits its 100-job cap) — all `critical` at 95%+ except where noted. See **[docs/ENVIRONMENT.md](docs/ENVIRONMENT.md#optional--slack-alerting)**. The underlying `sync_alerts()` API is generic and other collectors can adopt it over time.

---

## One-shot mode — run from a CI cron job instead of a daemon

Don't want an always-on container? `sfmon --once` runs every enabled job a single time, prints the resulting Prometheus exposition text to stdout, and exits — the same model sfdx-hardis's org monitoring uses (a scheduled CI/CD pipeline instead of a long-running process). Works with either distribution:

```bash
# Docker
docker run --rm -e SALESFORCE_AUTH_URL="force://PlatformCLI::..." mcarvin8/sfmon:latest --once

# pip install
SALESFORCE_AUTH_URL="force://PlatformCLI::..." sfmon --once
```

- Exit code is `0` if every job that ran succeeded, `1` if any job (or the initial org connection) failed — so a scheduled pipeline goes red on a real problem, the same way a failed CI step would.
- Add `--job JOB_ID` to run exactly one job (its id from the tables in [docs/CONFIGURATION.md](https://github.com/mcarvin8/sfmon/blob/main/docs/CONFIGURATION.md)) instead of everything currently enabled — `--job` forces that job to run regardless of its opt-in/disabled state in `config.json`, useful for ad-hoc checks. `--job` requires `--once`.
- Without `--job`, `--once` respects the same config as the daemon (presets, opt-in `schedules`, `disabled` entries) — it runs whatever would run at container startup, just without then staying up to serve `/metrics` or wait for the next cron tick.
- Pipe the output wherever it's useful: archive it as a pipeline artifact, `curl --data-binary` it to a Pushgateway, or `grep` it for a threshold check.

---

## Presets — scope down without a full config

If you only want a focused slice of monitoring, set a preset in `config.json` instead of listing every job:

```json
{ "preset": "ops" }
```

| Preset | Focus |
|--------|-------|
| `ops` | Apex health, Bulk API, deployments, EPT/APT |
| `audit` | Login events, geolocation, suspicious activity, report exports, sharing settings |
| `tech-debt` | Dormant users, deprecated APIs, permission sets, workflow rules, queues, security health |

Governor limits, instance/trust health, and license metrics are **always on** regardless of preset — they are the baseline signals you always want without having to ask.

See **[docs/CONFIGURATION.md](https://github.com/mcarvin8/sfmon/blob/main/docs/CONFIGURATION.md)** for the full scheduling reference.

---

## How it compares

| | SFMon | Salesforce proactive monitoring (paid) | sfdx-hardis org monitoring |
|--|-------|----------------------------------------|---------------------------|
| **Model** | Always-on container/process (Prometheus `/metrics`), or a scheduled CI job via `--once` | Salesforce TAM/CSM engagement + event log files | Scheduled CI jobs (GitHub Actions / GitLab CI) |
| **Output** | Time-series metrics scraped by Prometheus | Salesforce-native reports and guided reviews | Git diffs, Slack/Teams notifications, pipeline artifacts |
| **Alerting** | PromQL + Alertmanager (same as rest of infra), or built-in Slack webhook alerting with no Alertmanager needed | Salesforce notifications and Success Plan reviews | Slack/Teams webhooks from CI |
| **Data stays in your stack** | Yes | No (Salesforce-hosted) | Partially (metadata to Git; notifications to Slack/Teams) |
| **Extra cost** | Compute to run the container | Salesforce edition / add-on fee | Free (open source) |
| **Best for** | SRE/DevOps teams already on Prometheus who want Salesforce as just another scrape target | Teams buying Salesforce-managed oversight and guidance | Teams wanting metadata drift detection and CI-integrated checks |

SFMon and sfdx-hardis are complementary, not competitors: Hardis handles metadata backup and change detection via CI; SFMon provides continuous time-series for the same signals your infrastructure monitoring already tracks.

---

## PMD + minimal permission sets (optional, file-based)

The **published** `mcarvin8/sfmon` image does **not** include an Apex ruleset, `pmd-report.xml`, or `minimal-perm-sets.json` (they stay in your repo/CI only; see **`.dockerignore`**). Collectors **`monitor_pmd_code_smells`** and **`monitor_minimal_perm_sets`** need those files **inside the container** at fixed paths:

| File | In-container path |
|------|-------------------|
| PMD ruleset (XML) | Any path you choose; set **`PMD_RULESET_PATH`** to it |
| PMD report | **`/app/sfmon/tech_debt/pmd-report.xml`** |
| Minimal perm set report | **`/app/sfmon/tech_debt/minimal-perm-sets.json`** |

**Typical flow:**

1. **In your fork/clone** (with org access), refresh reports in CI so **`pmd-report.xml`** and **`minimal-perm-sets.json`** are produced under **`src/sfmon/tech_debt/`** and pushed to your default branch. Maintain **`manifest/package.xml`** and **`apexruleset.xml`** in that folder.
   - **GitHub Actions:** Workflow **[`.github/workflows/update-local-reports.yml`](.github/workflows/update-local-reports.yml)** — repository secret **`SALESFORCE_AUTH_URL`** (SFDX URL). Optional `workflow_dispatch` input **`manifest_path`** (default **`manifest/package.xml`**).
   - **GitLab CI:** Example job **[`.gitlab/workflows/update-local-reports.yml`](.gitlab/workflows/update-local-reports.yml)** — include it from **`.gitlab-ci.yml`** (define a **`query`** stage). Create a **project access token** with at least **Developer** role (and repository write scope), then set **`SALESFORCE_AUTH_URL`**, **`GITLAB_PUSH_USERNAME`**, **`GITLAB_PUSH_EMAIL`**, and **`GITLAB_PUSH_TOKEN`**. The sample **`rules`** run only for a **scheduled** pipeline on the default branch when **`JOB_NAME`** is **`codeSmells`** (add that variable on the schedule in GitLab, or change **`rules`**). Adjust **`tags`** for your runners. Details: **[docs/ENVIRONMENT.md](docs/ENVIRONMENT.md#refreshing-reports-in-ci-github-or-gitlab)** and **GitLab — project access token** in the same section.
2. **Get those files into the runtime container** (pick one):
   - **Mounts (no image rebuild):** copy or sync the committed files to the host/CI artifact store, then **bind-mount** or use a **ConfigMap** / volume (watch size limits for very large `pmd-report.xml`). Set **`PMD_RULESET_PATH`** and redeploy the **same** public image tag when you refresh reports.
   - **Private image:** **`docker build -f docker/Dockerfile`** from a branch that contains the refreshed files and **remove or trim the `src/sfmon/tech_debt/*` lines in `.dockerignore`** so `COPY src/sfmon/` bakes them in; push to your registry and redeploy when reports change.

3. **Opt in via `config.json`:** These collectors have **no default schedule**. Add **`monitor_pmd_code_smells`** and **`monitor_minimal_perm_sets`** under **`schedules`** with a cron string (see **[docs/CONFIGURATION.md](docs/CONFIGURATION.md#opt-in-only--file-based-reports-no-default-schedule)**). If your file uses a **non-empty** `schedules` block, list every other job you still want as well.

If **`PMD_RULESET_PATH`** is unset or the ruleset file is missing, PMD metrics are skipped (quiet at INFO). If **`minimal-perm-sets.json`** is missing, that collector logs a warning and exits. More detail: **[docs/ENVIRONMENT.md](docs/ENVIRONMENT.md#pmd-and-minimal-permission-sets-optional)**.

---

## When you need your own image

The default image is meant for **standard** monitoring: env vars + optional JSON config. It also excludes org-specific PMD/perm-set files (see **`.dockerignore`**).

**Build and run your own image** if you need to change **application code** (new checks, different logic, pinned dependencies, private registry policy, anything not covered by env/config) or to **bake in** local report files after adjusting **`.dockerignore`**.

```bash
docker build \
  -f docker/Dockerfile \
  --build-arg SALESFORCE_AUTH_URL="$SALESFORCE_AUTH_URL" \
  -t your-registry/sfmon:latest .

docker push your-registry/sfmon:latest   # if using a registry
```

Then run `your-registry/sfmon:latest` the same way as above (`-e SALESFORCE_AUTH_URL=...`, ports, volumes).

---

## Grafana

Import the JSON dashboards under **`grafana/`** and point them at your Prometheus data source.

---

## Authors

Originally developed by **Deep Suthar** and **Matt Carvin** (e.g. ECS / Kubernetes at Avalara).
