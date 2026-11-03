# Monitoring multiple orgs

Two ways to monitor more than one org. Both label every metric with `org` so a single Prometheus-compatible backend can scrape and filter/aggregate across orgs in PromQL.

# Fleet mode (one container, several orgs)

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

`org_overrides` is optional and lets one org diverge from the fleet-wide `schedules`. An org whose credentials fail to authenticate is logged and skipped at startup — it doesn't block the rest of the fleet. `ORG_NAME` is ignored once `orgs` is set. See **[docs/CONFIGURATION.md](CONFIGURATION.md#fleet-mode--multiple-orgs)** · template **`config.example.fleet.json`**.

# One container per org (alternate)

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
