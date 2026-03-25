# Salesforce Monitoring (SFMon)

![Docker Image Version](https://img.shields.io/docker/v/mcarvin8/sfmon?sort=date)
![Docker Pulls](https://img.shields.io/docker/pulls/mcarvin8/sfmon)
![Docker Image Size](https://img.shields.io/docker/image-size/mcarvin8/sfmon)

SFMon runs in **Docker**, connects to your Salesforce org on a schedule, and exposes **Prometheus** metrics at `/metrics` so you can graph and alert in **Grafana**, **Alertmanager**, or any tool that already monitors the rest of your stack.

### Why use SFMon?

| You might use SFMon if… | Notes |
|-------------------------|--------|
| You already run **Prometheus / Grafana** (or similar) and want **Salesforce next to apps, DBs, and K8s** in one place. | Same alerting patterns, retention, and on-call workflows as the rest of infra. |
| You want **broad org signals** in one exporter: limits, Apex/async health, licenses, security/tech-debt style checks, compliance-oriented metrics, etc. | See **[docs/CONFIGURATION.md](https://github.com/mcarvin8/sfmon/blob/main/docs/CONFIGURATION.md)** for what runs by default. |
| You prefer **self-hosted, no extra Salesforce SKU** for this style of telemetry. | You pay for compute to run the container; no SFMon subscription. |

**Compared to Salesforce proactive monitoring / paid optimizer-style products** — Those are Salesforce-native, guided, and often tied to editions or add-ons. SFMon is for teams that want **metrics in *their* observability stack**, custom Grafana dashboards, and **programmable** PromQL alerts—not a replacement for every Salesforce product feature, but a different integration model.

**Compared to [sfdx-hardis](https://github.com/hardisgroupcom/sfdx-hardis)** — Its [org monitoring](https://sfdx-hardis.cloudity.com/salesforce-monitoring-home/) is built around **scheduled CI jobs** (e.g. nightly GitHub Actions): each run is **short-lived**, backs up metadata to Git, and surfaces results via **Slack / Microsoft Teams**, **pipeline artifacts**, and diffs in a monitoring repo. That is a different shape than a always-on metrics endpoint. Hardis docs show **Grafana** examples for some checks, but the default path is **not** a Prometheus **`/metrics` scrape target** like SFMon—you would wire Prometheus/Grafana yourself if you want that model. SFMon is a **long-running container** with **native Prom metrics** for the same “always graphable” alerting style as the rest of your stack. The two can complement each other (Hardis for metadata drift + CI checks, SFMon for continuous time-series in Prometheus).

---

## Run the published image

Image: **[mcarvin8/sfmon](https://hub.docker.com/r/mcarvin8/sfmon)**.

1. **Auth URL** — from your machine: `sf org display --url-only` (or legacy `sfdx force:org:display --urlonly`).
2. **Run:**

```bash
docker run -d \
  --name sfmon \
  -p 9001:9001 \
  -e SALESFORCE_AUTH_URL="force://PlatformCLI::..." \
  mcarvin8/sfmon:latest
```

3. **Prometheus** — scrape `http://<host>:9001/metrics` (match host/port to your publish mapping).
4. **Sanity check:** `curl http://localhost:9001/metrics`

No config file is required: all collectors run on **default schedules**. Optional tuning:

- **Environment variables** (timeouts, compliance lists, thresholds, log level, etc.) → **[docs/ENVIRONMENT.md](https://github.com/mcarvin8/sfmon/blob/main/docs/ENVIRONMENT.md)**
- **Config file** (schedules, disable jobs, `exclude_users`) → **[docs/CONFIGURATION.md](https://github.com/mcarvin8/sfmon/blob/main/docs/CONFIGURATION.md)** · template **`config.example.json`**

Example with a mounted config:

```bash
docker run -d --name sfmon -p 9001:9001 \
  -e SALESFORCE_AUTH_URL="force://..." \
  -v /path/on/host/config.json:/app/sfmon/config.json \
  mcarvin8/sfmon:latest
```

### PMD + minimal permission sets (optional, file-based)

The **published** `mcarvin8/sfmon` image does **not** include an Apex ruleset, `pmd-report.xml`, or `minimal-perm-sets.json` (they stay in your repo/CI only; see **`.dockerignore`**). Collectors **`monitor_pmd_code_smells`** and **`monitor_minimal_perm_sets`** need those files **inside the container** at fixed paths:

| File | In-container path |
|------|-------------------|
| PMD ruleset (XML) | Any path you choose; set **`PMD_RULESET_PATH`** to it |
| PMD report | **`/app/sfmon/tech_debt/pmd-report.xml`** |
| Minimal perm set report | **`/app/sfmon/tech_debt/minimal-perm-sets.json`** |

**Typical flow:**

1. **In your fork/clone** (with org access), enable **[`.github/workflows/update-local-reports.yml`](.github/workflows/update-local-reports.yml)** and set the **`SALESFORCE_AUTH_URL`** secret. Adjust **`manifest/package.xml`** and commit your **`src/sfmon/tech_debt/apexruleset.xml`**. The workflow retrieves metadata, runs PMD, runs **`scripts/determine_minimal_perm_sets.py`**, and **commits** updated reports under **`src/sfmon/tech_debt/`**.
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
