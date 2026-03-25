# SFMon environment variables

## Required

| Variable | Description |
|----------|-------------|
| `SALESFORCE_AUTH_URL` | SFDX auth URL (`sf org display --url-only`). Format: `force://PlatformCLI::...` |

## Optional — runtime

| Variable | Default | Description |
|----------|---------|-------------|
| `METRICS_PORT` | `9001` | Prometheus scrape port inside the container |
| `CONFIG_FILE_PATH` | `/app/sfmon/config.json` | JSON config path (optional; mount file + set path if needed) |
| `QUERY_TIMEOUT_SECONDS` | `30` | SOQL query timeout |
| `REQUESTS_TIMEOUT_SECONDS` | `300` | HTTP timeout (Event Log, Trust API, etc.) |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |

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

The files are **not** included in the **published** Docker image: **`.dockerignore`** omits **`apexruleset.xml`**, **`pmd-report.xml`**, and **`minimal-perm-sets.json`** under **`src/sfmon/tech_debt/`**. Generate them in **your** repo (typically **[`.github/workflows/update-local-reports.yml`](../.github/workflows/update-local-reports.yml)** plus secret **`SALESFORCE_AUTH_URL`**), then **mount** them or **rebuild a private image** after removing those lines from **`.dockerignore`**.

| Variable | Required | Description |
|----------|----------|-------------|
| `PMD_RULESET_PATH` | Yes, for PMD metrics | Absolute path inside the container to your Apex ruleset XML. If unset or missing, **`monitor_pmd_code_smells`** exits quietly (DEBUG only). |

**Fixed paths in code**

| Collector | File | Path inside container |
|-----------|------|------------------------|
| PMD | Report XML | **`/app/sfmon/tech_debt/pmd-report.xml`** |
| Minimal permission sets | JSON | **`/app/sfmon/tech_debt/minimal-perm-sets.json`** |

**Operational loop**

1. Run the **GitHub workflow** in the same repository you use for deployments (or publish artifacts and copy files out). It commits refreshed **`pmd-report.xml`** and **`minimal-perm-sets.json`** (and you maintain **`apexruleset.xml`** in **`src/sfmon/tech_debt/`**).
2. **Redeploy without rebuilding** the app image: update volumes/ConfigMaps (or host bind mounts) with the new files, then roll the Pod so it picks up changes. Set **`PMD_RULESET_PATH`** to the mounted ruleset path (for example **`/app/sfmon/config/apexruleset.xml`**).
3. **Or** rebuild and redeploy your **own** image from source that includes those files (fork removes the tech_debt file entries from **`.dockerignore`** so `COPY src/sfmon/` embeds them).

**Docker example** — published image + bind mounts:

```bash
docker run -d --name sfmon -p 9001:9001 \
  -e SALESFORCE_AUTH_URL="force://..." \
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
