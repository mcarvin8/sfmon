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

The files are **not** included in the **published** Docker image: **`.dockerignore`** omits **`apexruleset.xml`**, **`pmd-report.xml`**, and **`minimal-perm-sets.json`** under **`src/sfmon/tech_debt/`**. Generate them in **your** repo using CI (see **[Refreshing reports in CI (GitHub or GitLab)](#refreshing-reports-in-ci-github-or-gitlab)** below), then **mount** them or **rebuild a private image** after removing those lines from **`.dockerignore`**.

| Variable | Required | Description |
|----------|----------|-------------|
| `PMD_RULESET_PATH` | Yes, for PMD metrics | Absolute path inside the container to your Apex ruleset XML. If unset or missing, **`monitor_pmd_code_smells`** exits quietly (DEBUG only). |

**Fixed paths in code**

| Collector | File | Path inside container |
|-----------|------|------------------------|
| PMD | Report XML | **`/app/sfmon/tech_debt/pmd-report.xml`** |
| Minimal permission sets | JSON | **`/app/sfmon/tech_debt/minimal-perm-sets.json`** |

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
