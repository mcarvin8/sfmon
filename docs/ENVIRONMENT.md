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
