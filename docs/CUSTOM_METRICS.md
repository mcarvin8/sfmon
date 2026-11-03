# Custom SOQL metrics

Add your own metrics from `config.json` with no code and no custom image. Each entry runs one SOQL query on a schedule and puts the result in a gauge named `sfmon_custom_<name>`. Use it for managed-package objects (CPQ, Billing, FSL), your own custom objects, or any standard object sfmon doesn't already cover.

```json
{
  "custom_metrics": [
    {
      "name": "cpq_failed_calculations",
      "description": "CPQ quote calculation jobs in a failed state",
      "query": "SELECT COUNT() FROM SBQQ__RecordJob__c WHERE SBQQ__JobStatus__c = 'Failed'",
      "schedule": "*/15"
    },
    {
      "name": "cpq_primary_quotes_by_status",
      "description": "Primary CPQ quotes by status",
      "query": "SELECT SBQQ__Status__c status, COUNT(Id) total FROM SBQQ__Quote__c WHERE SBQQ__Primary__c = true GROUP BY SBQQ__Status__c",
      "schedule": "minute=10",
      "value_field": "total",
      "labels": { "status": "status" }
    }
  ]
}
```

That produces:

```text
sfmon_custom_cpq_failed_calculations{org="prod"} 3
sfmon_custom_cpq_primary_quotes_by_status{org="prod",status="Draft"} 41
sfmon_custom_cpq_primary_quotes_by_status{org="prod",status="Approved"} 12
```

## Fields

| Key | Required | Purpose |
|-----|----------|---------|
| `name` | yes | snake_case. The gauge is `sfmon_custom_<name>` and the job id is `custom_<name>`. Don't include `sfmon_` yourself. |
| `query` | yes | A SOQL `SELECT` statement. |
| `schedule` | yes | Any [schedule string format](CONFIGURATION.md#schedule-string-formats), or `"disabled"`. |
| `description` | no | Metric help text. |
| `value_field` | no | Field holding each row's value. Omit it to get one value: the query's record count. |
| `labels` | no | Object of `label_name` → field path. Needs `value_field`. `org` and `job` are reserved. |
| `api` | no | `"rest"` (default) or `"tooling"` for Tooling API objects such as `ApexClass` or `Flow`. |
| `orgs` | no | Fleet mode: only run against these orgs, e.g. where the package is installed. |
| `max_series` | no | Row cap, default 500. Extra rows are dropped with a warning. |

## How values are read

Custom metrics use the SOQL result directly; they do not run arbitrary code to transform the returned records. The query must return the metric value in a form sfmon supports: either a record count, or a numeric `value_field` for each returned row. Labels must also come from fields in those rows.

For example, calculating the percentage of Apex code characters may require retrieving Apex class bodies, filtering or counting characters, and calculating a percentage. If the SOQL query does not return that final value, a custom metric cannot perform those additional steps by itself. That calculation needs to be implemented in code, or—in cases where the query can provide suitable input values—done with a Prometheus recording rule.

- **No `value_field`:** one series per org, set to `totalSize`. That's the count for `SELECT COUNT() ...` and the row count for any other query.
- **With `value_field`:** one series per returned row. The value comes from `value_field` and each label from its field path.
  - Aggregate queries: alias the aggregate (`COUNT(Id) total`, `SUM(Amount) amount`) and use the alias. Without an alias Salesforce names it `expr0`, `expr1`, and so on.
  - Relationship paths work: `"owner": "Owner.Name"`.
  - Field names are matched case-insensitively.
  - Rows with a null value are skipped. Rows with a non-numeric value are skipped with a warning. Null label values become `""`.
  - If two rows produce the same labels, the last one wins. Use `GROUP BY` to avoid that.

Each run replaces that org's series for the metric, so values that disappear from the query result disappear from `/metrics`. A failed query clears the org's series instead of leaving stale numbers.

## Schedules, fleet mode, and `--once`

Custom metrics always run on their own `schedule`. Opt-in mode and presets don't affect them.

To change or disable one for a single org, use its job id in `org_overrides`, the same as any built-in job:

```json
{
  "orgs": ["prod", "sandbox-uat"],
  "custom_metrics": [
    { "name": "open_renewals", "query": "SELECT COUNT() FROM Opportunity WHERE Type = 'Renewal' AND IsClosed = false", "schedule": "minute=0" }
  ],
  "org_overrides": {
    "sandbox-uat": { "schedules": { "custom_open_renewals": "disabled" } }
  }
}
```

Use `"orgs": [...]` on the metric instead when the queried object only exists in some orgs.

One-shot mode runs custom metrics like any other job: `sfmon --once --job custom_open_renewals`. A metric with `orgs` set still only runs against those orgs.

Each custom job reports on the usual self-monitoring metrics with `job="custom_<name>"`, so `sfmon_job_success` catches a broken query.

## Validation

sfmon validates every custom metric at startup and exits with code 2, listing every problem, if any entry is invalid. That includes unknown keys, so a typo like `lables` fails rather than being silently ignored. A query that is valid JSON but bad SOQL (wrong field name, object not installed) is only caught when it runs: the error is logged and the job shows as failed.

## Things to keep in mind

- **API usage.** Each run is at least one API call per org. A query every 5 minutes is 288 calls a day per org. Watch `sfmon_org_limit_usage_percent{limit_name="DailyApiRequests"}` if you add many.
- **Cardinality.** Labelling by `Id`, `Name`, or anything else with lots of distinct values creates a series per record and can overload Prometheus. Aggregate with `GROUP BY`, and keep `max_series` low.
- **Data access.** The config file can query anything the integration user can read, including personal data, and label values are exported to Prometheus as plain text. Treat `config.json` like code: review changes and restrict who can edit it.
- **Derived values.** Ratios, thresholds and combinations of several queries belong in Prometheus recording or alert rules, not in sfmon. If you need Python logic on the query results, see [Building your own image](ADVANCED.md#building-your-own-image).
