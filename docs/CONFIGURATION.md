# SFMon configuration file

Optional JSON file that controls **which jobs run**, **when they run**, and some **user lists** for compliance-style metrics.

## Location

| Where | Value |
|-------|--------|
| Default path in container | `/app/sfmon/config.json` |
| Override | Environment variable `CONFIG_FILE_PATH` |

**Docker example** (mount your file to the default path):

```bash
-v /host/path/config.json:/app/sfmon/config.json
```

Or keep the file elsewhere and set:

```bash
-e CONFIG_FILE_PATH=/app/config/my-config.json
-v /host/path/my-config.json:/app/config/my-config.json
```

## Structure

```json
{
  "schedules": {
    "monitor_salesforce_limits": "*/5",
    "some_other_job": "disabled"
  },
  "exclude_users": ["Admin User"]
}
```

| Key | Type | Purpose |
|-----|------|---------|
| `schedules` | object | Job id → schedule string (see below). |
| `exclude_users` | array (optional) | Usernames excluded from certain compliance checks (e.g. suspicious audit activity). |
| `integration_user_names` | array (optional) | Parsed from config but **not used** by current collectors—set **`INTEGRATION_USER_NAMES`** (env) for integration-user labeling; see [ENVIRONMENT.md](ENVIRONMENT.md). |

---

## How scheduling behaves

| Situation | Behavior |
|-----------|----------|
| **No config file** | Every registered job with a **default schedule** runs (see tables below). Jobs marked **opt-in** have **no** default and do **not** run. |
| **Config file exists, `schedules` missing or `{}`** | Same as no file: defaults for jobs that have them; **opt-in** jobs stay off. |
| **Config file with a non-empty `schedules` object** | **Opt-in:** only jobs **listed** under `schedules` run. Jobs not listed are **not** run. |
| **Job value `"disabled"`** (or `none` / empty) | That job does **not** run (only applies when the job is listed under `schedules`). |

**Important:** As soon as you add **any** entry under `schedules`, you must list **every** job you want—including ones you only want at default cadence. Copy defaults from the table below or start from `config.example.json` and trim.

**File-based metrics (PMD + minimal permission sets):** `monitor_pmd_code_smells` and `monitor_minimal_perm_sets` have **no default schedule**. They run only if you add them under `schedules` with a cron expression (for example `hour=3,minute=10` and `hour=2,minute=20`). You must also provide the files and env described in **[ENVIRONMENT.md](ENVIRONMENT.md#pmd-and-minimal-permission-sets-optional)** (`PMD_RULESET_PATH`, `pmd-report.xml`, `minimal-perm-sets.json` at the documented paths), typically via volume mounts or a private image build.

---

## Schedule string formats

All of these are valid values for each job under `schedules`:

| Format | Example | Meaning |
|--------|---------|---------|
| Simple minute | `"*/5"` | Every 5 minutes (same as `minute=*/5`) |
| Key=value | `"hour=7,minute=30"` | Daily at 07:30 |
| Key=value | `"minute=5"` | Every hour at :05 past the hour |
| 5-field cron | `"5 * * * *"` | Standard cron (minute hour day month weekday) |
| JSON | `'{"hour": "6", "minute": "15"}'` | Same idea as key=value |
| Disable | `"disabled"` | Job does not run |

Unknown strings may log a warning and fall back in parser behavior—stick to the patterns above.

---

## Default schedules (built-in)

These are the schedules used when **no opt-in `schedules` block** applies. Times use the **container’s local timezone** (often UTC unless you configure the host).

### Every 5 minutes

| Job ID | Summary |
|--------|---------|
| `monitor_salesforce_limits` | Org API and governor limits usage vs. max. |
| `get_salesforce_instance` | Instance / trust-style health for the org’s pod. |
| `monitor_apex_flex_queue` | Depth of the Apex flex queue. |

### Daily (off-peak tech debt — 02:00–05:55)

| Job ID | Default time | Summary |
|--------|----------------|---------|
| `unassigned_permission_sets` | 02:00 | Permission sets not assigned to any user. |
| `perm_sets_limited_users` | 02:15 | Permission sets with very few users (threshold via env). |
| `profile_assignment_under5` | 02:30 | Profiles with fewer than N active users. |
| `profile_no_active_users` | 02:45 | Profiles with no active users. |
| `apex_classes_api_version` | 03:00 | Apex classes on old API versions (tech debt). |
| `apex_used_limits_monitoring` | 03:05 | Apex code footprint vs. org character limits. |
| `apex_triggers_api_version` | 03:15 | Triggers on deprecated/low API versions. |
| `security_health_check` | 03:30 | Security Health Check style findings as metrics. |
| `salesforce_health_risks` | 03:45 | Broader security / health risk signals. |
| `workflow_rules_monitoring` | 04:00 | Legacy workflow rule usage. |
| `dormant_salesforce_users` | 04:15 | Internal users inactive for N days. |
| `dormant_portal_users` | 04:30 | Portal/community users inactive for N days. |
| `total_queues_per_object` | 04:45 | Queue counts per object type. |
| `queues_with_no_members` | 05:00 | Queues with no members. |
| `queues_with_zero_open_cases` | 05:15 | Case queues with no open cases. |
| `public_groups_with_no_members` | 05:30 | Public groups with no members. |
| `dashboards_with_inactive_users` | 05:45 | Dashboards owned by or shared with inactive users. |
| `scheduled_apex_jobs_monitoring` | 05:55 | Scheduled Apex job inventory / health. |

### Opt-in only — file-based reports (no default schedule)

Add these under `schedules` only after you mount or bake in the files from **[ENVIRONMENT.md](ENVIRONMENT.md#pmd-and-minimal-permission-sets-optional)**. Suggested times match the former defaults.

| Job ID | Suggested time | Summary |
|--------|----------------|---------|
| `monitor_minimal_perm_sets` | `hour=2,minute=20` | Minimal permission sets from `minimal-perm-sets.json` (e.g. CI [workflow](../.github/workflows/update-local-reports.yml)). |
| `monitor_pmd_code_smells` | `hour=3,minute=10` | PMD violations from `pmd-report.xml` and `PMD_RULESET_PATH`. |

These jobs are **off** until you add them under `schedules`. That requires a **non-empty** `schedules` object (for example the full opt-in list from **`config.example.json`**, plus these entries). If you already use non-empty `schedules` for other reasons, append these two lines with your chosen cron strings.

### Daily performance & Apex (06:00–07:35)

| Job ID | Default time | Summary |
|--------|----------------|---------|
| `get_salesforce_ept_and_apt` | 06:00 | Experience / average page times where available. |
| `monitor_login_events` | 06:15 | Login event patterns and volumes. |
| `async_apex_job_status` | 06:30 | Batch/future/queueable job status. |
| `monitor_apex_execution_time` | 06:45 | Long-running Apex request signals. |
| `async_apex_execution_summary` | 07:00 | Aggregated async Apex execution. |
| `concurrent_apex_errors` | 07:15 | Concurrent Apex limit errors. |
| `expose_apex_exception_metrics` | 07:25 | Apex uncaught exception metrics. |
| `expose_concurrent_long_running_apex_errors` | 07:35 | Concurrent + long-running Apex error combo metrics. |

### Daily business & compliance (07:30–08:30)

| Job ID | Default time | Summary |
|--------|----------------|---------|
| `daily_analyse_bulk_api` | 07:30 | Daily Bulk API job analysis / summaries. |
| `geolocation` | 08:00 | Login geolocation metrics (lookback via env). |
| `expose_suspicious_records` | 08:15 | Suspicious audit / setup changes (exclusions via `exclude_users`). |
| `monitor_org_wide_sharing_settings` | 08:30 | Org-wide default sharing (OWD) drift. |

### Hourly (staggered)

| Job ID | Default | Summary |
|--------|---------|---------|
| `hourly_analyse_bulk_api` | Minute **5** each hour | Hourly Bulk API activity. |
| `get_salesforce_licenses` | Minute **15** | License consumption vs. purchased. |
| `hourly_observe_user_querying_large_records` | Minute **25** | Large SOQL row counts (compliance). |
| `monitor_forbidden_profile_assignments` | Minute **35** | Active users with forbidden profiles (env list). |
| `hourly_report_export_records` | Minute **45** | Report export volume tracking. |
| `get_deployment_status` | Minute **55** | In-flight deployment / metadata deploy status. |

---

## Customize schedules

**Change cadence for one job (opt-in mode):**

1. Add a `schedules` object.
2. List **every** job you still want to run.
3. Set custom cron strings for jobs you want at non-default times.

Example: only the three critical jobs every 5 minutes, plus licenses hourly:

```json
{
  "schedules": {
    "monitor_salesforce_limits": "*/5",
    "get_salesforce_instance": "*/5",
    "monitor_apex_flex_queue": "*/5",
    "get_salesforce_licenses": "minute=15"
  }
}
```

**Disable specific jobs (opt-in mode):**

List the job but set it to `disabled`:

```json
{
  "schedules": {
    "monitor_salesforce_limits": "*/5",
    "get_salesforce_instance": "*/5",
    "monitor_apex_flex_queue": "*/5",
    "geolocation": "disabled",
    "expose_suspicious_records": "disabled"
  }
}
```

> Listing a job as `disabled` only works when that job appears under `schedules`. Jobs **omitted** from `schedules` are also off—they are simply not scheduled.

**Reschedule without disabling:**

Use the same job id with a new expression, e.g. run tech-debt block at 09:00 instead of 02:00:

```json
"unassigned_permission_sets": "hour=9,minute=0"
```

---

## Reference template

See **`config.example.json`** in the repository for a large opt-in example. **Note:** example files may drift from code defaults; the **default schedule table above** matches `salesforce_monitoring.py` in this repo.

For environment-based tuning (timeouts, thresholds, compliance env vars), see **[ENVIRONMENT.md](ENVIRONMENT.md)**.
