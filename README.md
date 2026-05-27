# Salesforce Monitoring (SFMon)

![Docker Image Version](https://img.shields.io/docker/v/mcarvin8/sfmon?sort=date)
![Docker Pulls](https://img.shields.io/docker/pulls/mcarvin8/sfmon)
![Docker Image Size](https://img.shields.io/docker/image-size/mcarvin8/sfmon)
![Coverage](https://raw.githubusercontent.com/mcarvin8/sfmon/refs/heads/main/badges/coverage.svg)

SFMon is a **long-running Docker container** that connects to your Salesforce org on a schedule and exposes a **standard `/metrics` endpoint** compatible with Prometheus, Victoria Metrics, Grafana Cloud, Mimir, and any OpenTelemetry Collector pipeline — so your Salesforce org lives in the same Grafana dashboards, PromQL alerts, and on-call runbooks as the rest of your infrastructure.

---

## Who is this for

SFMon is aimed at **SRE and DevOps teams** who already operate a Prometheus-compatible observability stack (Prometheus, Victoria Metrics, Grafana Cloud, or an OTel Collector pipeline)  and are also responsible for one or more Salesforce orgs. If you define alerts in PromQL, route pages through Alertmanager, and want Salesforce signals to behave exactly like any other scrape target — this is for you.

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

Optional tuning:
- **Environment variables** (timeouts, org label, compliance lists, thresholds, log level) → **[docs/ENVIRONMENT.md](https://github.com/mcarvin8/sfmon/blob/main/docs/ENVIRONMENT.md)**
- **Config file** (schedules, presets, disable jobs, `exclude_users`) → **[docs/CONFIGURATION.md](https://github.com/mcarvin8/sfmon/blob/main/docs/CONFIGURATION.md)** · template **`config.example.json`**

---

## Multiple orgs

Run one container per org, each with a distinct `ORG_NAME`. All metrics carry the `org` label, so a single Prometheus-compatible backend can scrape all of them and you can filter or aggregate across orgs in PromQL.

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

Or simply set `ORG_NAME` on each container — the `org` label is injected into every metric automatically.

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
| **Model** | Always-on container, Prometheus `/metrics` endpoint | Salesforce TAM/CSM engagement + event log files | Scheduled CI jobs (GitHub Actions / GitLab CI) |
| **Output** | Time-series metrics scraped by Prometheus | Salesforce-native reports and guided reviews | Git diffs, Slack/Teams notifications, pipeline artifacts |
| **Alerting** | PromQL + Alertmanager — same as rest of infra | Salesforce notifications and Success Plan reviews | Slack/Teams webhooks from CI |
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
