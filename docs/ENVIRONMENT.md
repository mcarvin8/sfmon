# SFMon environment variables

## Required

| Variable | Description |
|----------|-------------|
| `SALESFORCE_AUTH_URL` | SFDX auth URL (`sf org display --url-only`). Format: `force://PlatformCLI::...`. Not used in fleet mode — see below. |

## Optional — runtime

| Variable | Default | Description |
|----------|---------|-------------|
| `METRICS_PORT` | `9001` | Prometheus scrape port inside the container |
| `CONFIG_FILE_PATH` | `/app/sfmon/config.json` | JSON config path (optional; mount file + set path if needed). Default only exists inside the Docker image — pip installs (`sfmon` console script) must set this explicitly, e.g. `/etc/sfmon/config.json` |
| `QUERY_TIMEOUT_SECONDS` | `30` | SOQL query timeout |
| `REQUESTS_TIMEOUT_SECONDS` | `300` | HTTP timeout (Event Log, Trust API, etc.) |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `ORG_NAME` | `""` | Value injected as the `org` label on **every** Prometheus metric. Set this to a human-readable identifier for your Salesforce org (e.g. `production`, `sandbox-uat`) so you can filter or aggregate across multiple SFMon instances in the same Prometheus/Grafana setup. If unset, the label is present but empty. **Ignored in fleet mode** — org names there come from `config.json`'s `orgs` list instead. |
| `SCHEDULER_MAX_WORKERS` | `min(orgs * 2, 20)` | Size of the APScheduler thread pool. Raise this if you run many orgs and see jobs queueing behind each other at shared cron ticks. |

## Optional — secrets backend

By default, auth URLs come straight from the environment (`SALESFORCE_AUTH_URL` / `SALESFORCE_AUTH_URL_<NAME>`). Setting `SECRETS_BACKEND` fetches them from a secrets manager instead, using the same name as the secret identifier — so switching backends doesn't change how orgs are named anywhere else (fleet mode, `config.json`, logs).

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRETS_BACKEND` | unset | Set to `aws` to fetch auth URLs from AWS Secrets Manager instead of the environment. Any other non-empty value fails fast with a clear error rather than silently falling back to the environment. |
| `AWS_SECRETS_PREFIX` | `""` | Prepended to the secret name looked up in AWS Secrets Manager, e.g. `sfmon/` turns `SALESFORCE_AUTH_URL_PROD` into `sfmon/SALESFORCE_AUTH_URL_PROD`. Only used when `SECRETS_BACKEND=aws`. |

**AWS Secrets Manager (`SECRETS_BACKEND=aws`):**
- Requires the `boto3` package. The Docker image includes it by default; pip installs need `pip install "sfmon[aws]"`. If it's missing, SFMon raises a clear error naming the fix instead of an opaque `ModuleNotFoundError`.
- Store the secret's value as a **SecretString** — the raw SFDX auth URL (`force://...`), not JSON. Binary secrets aren't supported.
- Region and credentials come from boto3's standard resolution chain (`AWS_REGION`/`AWS_DEFAULT_REGION`, an IAM role, `~/.aws/credentials`, etc.) — no SFMon-specific wiring.
- Minimum IAM permission: `secretsmanager:GetSecretValue` on the secret(s) SFMon reads.
- Secrets are fetched fresh on every connect/reconnect (startup and the session-expiry retry path in `query.py`), not cached across the process lifetime — so rotating a secret takes effect on the next reauthentication without a restart.

## Optional — OTLP push

Metrics and logs are always available the same way as before: metrics on `/metrics` (Prometheus scrape format), logs as JSON lines on stdout. Setting `OTEL_EXPORTER_OTLP_ENDPOINT` additionally **pushes** both to an OTLP-compatible collector or backend (Datadog, Honeycomb, Grafana Alloy, an OTel Collector, ...) — useful when you don't want to run a Prometheus scrape target, or your log pipeline ingests OTLP directly instead of tailing container stdout. Leaving it unset keeps today's behavior exactly as-is.

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | unset | Base URL of an OTLP/HTTP collector, e.g. `http://otel-collector:4318`. When set, metrics push on a periodic interval (default 60s) in addition to being scrapeable, and log records push in addition to stdout. |

Standard OTel SDK environment variables (`OTEL_EXPORTER_OTLP_HEADERS` for auth, `OTEL_METRIC_EXPORT_INTERVAL` to change the push interval, `OTEL_EXPORTER_OTLP_TIMEOUT`, etc.) are read automatically by the underlying SDK — no SFMon-specific wiring needed for those. See the [OpenTelemetry SDK environment variable spec](https://opentelemetry.io/docs/specs/otel/configuration/sdk-environment-variables/) for the full list.

The structured `event` payload on log records (see [logger.py](../src/sfmon/logger.py)) survives as a nested log attribute over OTLP — unlike Prometheus metric labels, OTLP log attributes support nested values, so no data is lost in the push path.

## Fleet mode — monitoring multiple orgs from one container

Add an `orgs` array to `config.json` to monitor several Salesforce orgs from a single SFMon container instead of running one container per org:

```json
{
  "orgs": ["prod", "sandbox-uat"],
  "schedules": { "monitor_salesforce_limits": "*/5" },
  "org_overrides": {
    "sandbox-uat": {
      "schedules": { "monitor_salesforce_limits": "*/15" }
    }
  }
}
```

Each name in `orgs` resolves to a `SALESFORCE_AUTH_URL_<NAME>` environment variable (uppercased, non-alphanumeric characters replaced with `_`) — e.g. `"prod"` → `SALESFORCE_AUTH_URL_PROD`, `"sandbox-uat"` → `SALESFORCE_AUTH_URL_SANDBOX_UAT`. Every metric is labeled `org="prod"` / `org="sandbox-uat"` accordingly. `org_overrides` is optional and lets one org's schedule diverge from the fleet-wide `schedules` block. An org whose credentials fail to authenticate is logged and skipped at startup — it doesn't block the rest of the fleet. See [CONFIGURATION.md](CONFIGURATION.md) for the full schedule format.

Omitting `orgs` (or leaving it empty) keeps today's single-org behavior unchanged, driven by `SALESFORCE_AUTH_URL` and `ORG_NAME`.

## Optional — compliance

| Variable | Description |
|----------|-------------|
| `INTEGRATION_USER_NAMES` | Comma-separated names → categorized as integration users in audit metrics |
| `FORBIDDEN_PROD_PROFILES` | Comma-separated profile names that should not be active in prod |
| `LARGE_QUERY_THRESHOLD` | Row count threshold for “large query” alerts (default `10000`) |

## Optional — tech debt thresholds

| Variable | Default |
|----------|---------|
| `DORMANT_USER_DAYS` | `90` |
| `DEPRECATED_API_VERSION` | `50` |
| `PERMSET_LIMITED_USERS_THRESHOLD` | `10` |
| `PROFILE_UNDER_USERS_THRESHOLD` | `5` |
| `APEX_CHARACTER_LIMIT` | `6000000` |

## PMD and minimal permission sets (optional)

These collectors use **files on disk** inside the container and are **not scheduled by default**. Enable **`monitor_pmd_code_smells`** and **`monitor_minimal_perm_sets`** under **`schedules`** in **`config.json`** (non-empty `schedules`); see **[CONFIGURATION.md](CONFIGURATION.md#opt-in-only--file-based-reports-no-default-schedule)**.

The files are **not** included in the **published** Docker image: **`.dockerignore`** omits **`apexruleset.xml`**, **`pmd-report.xml`**, and **`minimal-perm-sets.json`** under **`src/sfmon/tech_debt/`**. Generate them in **your** repo using CI (see **[Refreshing reports in CI (GitHub or GitLab)](#refreshing-reports-in-ci-github-or-gitlab)** below), then **mount** them or **rebuild a private image** after removing those lines from **`.dockerignore`**.

| Variable | Required | Description |
|----------|----------|-------------|
| `PMD_RULESET_PATH` | Yes, for PMD metrics | Absolute path inside the container to your Apex ruleset XML. If unset or missing, **`monitor_pmd_code_smells`** exits quietly (DEBUG only). |

**Fixed paths in code**

| Collector | File | Path inside container |
|-----------|------|------------------------|
| PMD | Report XML | **`/app/sfmon/tech_debt/pmd-report.xml`** |
| Minimal permission sets | JSON | **`/app/sfmon/tech_debt/minimal-perm-sets.json`** |

These paths aren't a configurable constant — both collectors resolve them at runtime relative to their own module file (`tech_debt/pmd.py`'s and `tech_debt/permissions.py`'s own directory). In the Docker image that directory is `/app/sfmon/tech_debt/`, matching the table above. **pip installs** resolve this to wherever `pip` put the package — typically `<venv>/lib/pythonX.Y/site-packages/sfmon/tech_debt/` — so you'd need to drop the report files directly into site-packages, which isn't a normal workflow. These two file-based collectors are effectively Docker/container-only; pip installs are better suited to the other collectors that only need `SALESFORCE_AUTH_URL` and env vars.

### Refreshing reports in CI (GitHub or GitLab)

Both examples retrieve with **`manifest/package.xml`**, run PMD on **`force-app/main/default/classes`** and **`triggers`**, run **`scripts/determine_minimal_perm_sets.py`**, and commit **`src/sfmon/tech_debt/pmd-report.xml`** and **`minimal-perm-sets.json`**. You must commit **`src/sfmon/tech_debt/apexruleset.xml`** yourself (ruleset is not generated).

| | **GitHub Actions** | **GitLab CI** |
|--|-------------------|---------------|
| **Template** | [`.github/workflows/update-local-reports.yml`](../.github/workflows/update-local-reports.yml) | [`.gitlab/workflows/update-local-reports.yml`](../.gitlab/workflows/update-local-reports.yml) |
| **Auth URL** | Repository secret **`SALESFORCE_AUTH_URL`** | CI variable **`SALESFORCE_AUTH_URL`** (mask/protect); use any name if you change the `echo` line in the job |
| **Git push** | `GITHUB_TOKEN` (**`permissions: contents: write`**) | **Project access token** (see below) exposed as **`GITLAB_PUSH_USERNAME`**, **`GITLAB_PUSH_EMAIL`**, **`GITLAB_PUSH_TOKEN`** |
| **Schedule** | `cron` + `workflow_dispatch` | **`rules`**: scheduled pipeline on default branch; example expects schedule variable **`JOB_NAME=codeSmells`** (change **`rules`** or your schedule to match) |
| **Include** | workflow file lives under `.github/workflows/` | Add **`include: local: '.gitlab/workflows/update-local-reports.yml'`** and a **`query`** stage in **`.gitlab-ci.yml`** |

**GitLab — project access token for `git push`**

Create a [**project access token**](https://docs.gitlab.com/ee/user/project/settings/project_access_tokens.html) on the same project (**Settings → Access tokens**). Use role **Developer** or higher (e.g. **Maintainer**) so the token may push commits. Enable the scopes your GitLab version requires for repository write access (for example **`write_repository`**; some versions also expect **`api`**).

Store these as **CI/CD variables** (mask **`GITLAB_PUSH_TOKEN`**, protect if you only run on protected branches):

| Variable | Purpose |
|----------|---------|
| **`GITLAB_PUSH_USERNAME`** | HTTPS username for `git push` (GitLab shows this with the token—often the token **name** or a fixed value such as `oauth2` per your host’s docs). Also used as `git config user.name`. |
| **`GITLAB_PUSH_EMAIL`** | Full address for `git config user.email` (e.g. `report-bot@example.com` or your org’s noreply pattern). |
| **`GITLAB_PUSH_TOKEN`** | Secret token value (password segment in the HTTPS push URL). |

If the default branch is **protected**, allow this token (or a bot user) to push per your **Protected branches** / **Push rules** settings.

For GitHub branch-protection bypass or PAT substitution, see comments in the GitHub workflow file.

**Operational loop**

1. Run **CI** in the repo you deploy from so refreshed reports land on the default branch (or copy artifacts out).
2. **Redeploy without rebuilding** the app image: update volumes/ConfigMaps (or host bind mounts) with the new files, then roll the Pod so it picks up changes. Set **`PMD_RULESET_PATH`** to the mounted ruleset path (for example **`/app/sfmon/config/apexruleset.xml`**).
3. **Or** rebuild and redeploy your **own** image from source that includes those files (fork removes the tech_debt file entries from **`.dockerignore`** so `COPY src/sfmon/` embeds them).

**Docker example** — published image + bind mounts:

```bash
docker run -d --name sfmon -p 9001:9001 \
  -e SALESFORCE_AUTH_URL="force://..." \
  -e ORG_NAME="production" \
  -e PMD_RULESET_PATH=/app/sfmon/config/apexruleset.xml \
  -v /host/path/apexruleset.xml:/app/sfmon/config/apexruleset.xml:ro \
  -v /host/path/pmd-report.xml:/app/sfmon/tech_debt/pmd-report.xml:ro \
  -v /host/path/minimal-perm-sets.json:/app/sfmon/tech_debt/minimal-perm-sets.json:ro \
  mcarvin8/sfmon:latest
```

Very large reports may exceed **Kubernetes ConfigMap** size limits; use a **Secret**, **PVC**, **CSI**, or an **initContainer** that fetches from object storage if needed.

## Optional — performance

| Variable | Default |
|----------|---------|
| `LONG_RUNNING_APEX_MS` | `5000` |
| `VERY_LONG_RUNNING_APEX_MS` | `10000` |

## Optional — geolocation

| Variable | Default |
|----------|---------|
| `GEOLOCATION_CHUNK_SIZE` | `100` |
| `GEOLOCATION_LOOKBACK_HOURS` | `1` |

## Optional — external API

| Variable | Default |
|----------|---------|
| `SALESFORCE_STATUS_API_URL` | `https://api.status.salesforce.com` |

## Optional — Slack alerting

Threshold/compliance breaches can optionally post to a Slack channel via an [incoming webhook](https://api.slack.com/messaging/webhooks). Alerts are edge-triggered: a Slack message fires when an alert item first appears ("opened") and again when it disappears ("resolved"), never on every scheduler tick while it stays active. State is cached to disk per `(org, category)` so this dedup works across restarts and `--once` CI-cron invocations, not just within one long-lived process. Leaving `SLACK_WEBHOOK_URL` unset disables alerting entirely — no cache reads/writes, no HTTP calls.

| Variable | Default | Description |
|----------|---------|-------------|
| `SLACK_WEBHOOK_URL` | unset | Slack incoming webhook URL. Unset = alerting disabled. |
| `SLACK_ALERT_CACHE_DIR` | `./sfmon_alert_cache` | Directory for the on-disk alert state cache (one JSON file per org/category). Relative paths resolve against the current working directory. Mount a persistent volume here if you want `--once`/cron runs to dedup across invocations; an ephemeral/ container-local path just means the first alert after every restart re-fires once. |
| `LIMIT_ALERT_THRESHOLD_PERCENT` | `80` | Usage percentage at/above which a Salesforce limit (from `monitor_salesforce_limits`) triggers a Slack alert. Limits at 95%+ are flagged `critical`, otherwise `warning`. |
| `LICENSE_ALERT_THRESHOLD_PERCENT` | `90` | Usage percentage at/above which a user, permission set, or usage-based entitlement license (from `get_salesforce_licenses`) triggers a Slack alert. 95%+ is `critical`. Default is higher than the limits threshold since license usage typically runs close to the purchased seat count by design. |
| `APEX_CHARACTER_ALERT_THRESHOLD_PERCENT` | `80` | Usage percentage of `APEX_CHARACTER_LIMIT` (from `apex_used_limits_monitoring`) at/above which a Slack alert triggers. 95%+ is `critical`. Lower default than the license threshold since this is a hard compile-time wall — deployments start failing at 100%, so earlier warning matters more than noise. |
| `FLEX_QUEUE_LIMIT` | `100` | Max jobs the Apex Flex Queue can hold at once (from `monitor_apex_flex_queue`). Fixed Salesforce platform constant — not exposed via SOQL or `/limits`, so this is a hardcoded default like `APEX_CHARACTER_LIMIT`, not a live lookup. |
| `FLEX_QUEUE_ALERT_THRESHOLD_PERCENT` | `80` | Usage percentage of `FLEX_QUEUE_LIMIT` at/above which a Slack alert triggers. Depth at/above the limit itself (100%) is `critical` — that's the actual hard cap where new jobs get rejected, not just an early-warning tier. |

Currently wired into `monitor_salesforce_limits` (governor limit breaches), `get_salesforce_incidents` (active Salesforce Trust API incidents on your org's pod), `get_salesforce_licenses` (license seat usage), `apex_used_limits_monitoring` (org-wide Apex character limit), and `monitor_apex_flex_queue` (flex queue depth); the underlying `sync_alerts()` API in [`slack_notify.py`](../src/sfmon/slack_notify.py) is generic and intended to be reused by other collectors over time.
