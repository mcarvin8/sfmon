# Alerting

Because metrics live in Prometheus, alerts are just PromQL rules — same toolchain as the rest of your stack:

```promql
# Daily API limit over 80 % consumed
sfmon_org_limit_usage_percent{limit_name="DailyApiRequests"} > 80

# Active Trust incident on the pod an org runs on
sfmon_trust_incidents == 1

# User license saturation
sfmon_user_license_usage_percent{license_name="Salesforce"} > 90
```

Route these through Alertmanager with the same receivers (PagerDuty, Slack, etc.) you use for every other service.

# Alerting on SFMon itself

Every job run also records metrics about the run, labelled with `job` (the job id used in `config.json`) and `org`:

| Metric | Meaning |
|--------|---------|
| `sfmon_job_success` | `1` if the last run finished with no exception and no failed queries, else `0` |
| `sfmon_job_last_success_timestamp_seconds` | Unix time of the last successful run (absent until the first one) |
| `sfmon_job_last_run_timestamp_seconds` | Unix time the last run finished, successful or not |
| `sfmon_job_duration_seconds` | How long the last run took |
| `sfmon_job_query_errors` | Salesforce queries that failed during the last run |

A failed query doesn't stop the job or the service: the collector carries on with the rest of its queries and the next run is scheduled as normal. The failure is counted in `sfmon_job_query_errors` and the run reports `sfmon_job_success 0`, so a job that quietly returns empty results is still visible.

```promql
# A job hasn't succeeded in 2 hours (catches expired credentials, missing permissions, API outages)
time() - sfmon_job_last_success_timestamp_seconds > 7200

# A job is running but has never succeeded since SFMon started
sfmon_job_success == 0 unless sfmon_job_last_success_timestamp_seconds

# SFMon stopped reporting entirely (pod down, scrape broken, org failed to connect at startup)
absent(sfmon_job_success{job="monitor_salesforce_limits"})
```

With `--once`, a run with failed queries also exits `1`, so CI notices the same failures.

# Built-in Slack alerting (optional, no Alertmanager required)

For teams that don't run a full PromQL/Alertmanager stack, SFMon can also post directly to a Slack incoming webhook. Set `SLACK_WEBHOOK_URL` and it's on; leave it unset and there's no behavior change at all (no cache reads/writes, no HTTP calls).

Alerts are edge-triggered — a Slack message fires once when a breach opens and once when it resolves, not on every scheduler tick while it stays active — using an on-disk cache (`SLACK_ALERT_CACHE_DIR`) keyed per org so state survives both the long-lived daemon and `--once` CI-cron restarts.

Currently wired into governor limits (`LIMIT_ALERT_THRESHOLD_PERCENT`, default `80`), Salesforce Trust API incidents (an active incident on your org's pod posts on open and again on resolve), license seat usage (`LICENSE_ALERT_THRESHOLD_PERCENT`, default `90`), the org-wide Apex character limit (`APEX_CHARACTER_ALERT_THRESHOLD_PERCENT`, default `80`), and Apex Flex Queue depth (`FLEX_QUEUE_ALERT_THRESHOLD_PERCENT`, default `80`, `critical` once the queue actually hits its 100-job cap) — all `critical` at 95%+ except where noted. See **[docs/ENVIRONMENT.md](ENVIRONMENT.md#optional--slack-alerting)**. 

The underlying `sync_alerts()` API is generic and other collectors can adopt it over time. Please create a GitHub issue to request any new alerts.
