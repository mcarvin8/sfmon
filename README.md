# Salesforce Monitoring (SFMon)

![Docker Image Version (latest by date)](https://img.shields.io/docker/v/mcarvin8/sfmon?sort=date)
![Docker Pulls](https://img.shields.io/docker/pulls/mcarvin8/sfmon)
![Docker Image Size (latest by date)](https://img.shields.io/docker/image-size/mcarvin8/sfmon)

**SFMon** is a portable, custom-built Docker container that collects Salesforce org metrics and exposes them via an HTTP endpoint for scraping by **Prometheus**. It enables teams to gain visibility into Salesforce performance, usage, configuration, technical debt, and incidents—no matter what cloud platform they use.

> **SFMon can be deployed on any platform** that supports Docker and Prometheus, including GCP, Azure, or Kubernetes-based environments. It has been tested and verified on AWS ECS and Kubernetes.

Prebuilt **Grafana dashboards** are included to help you visualize metrics right away.

---

## 🚀 Quick Start

### Using the Pre-built Docker Image

The easiest way to get started is using the pre-built image from [Docker Hub](https://hub.docker.com/repository/docker/mcarvin8/sfmon/general):

```bash
docker run -d \
  --name sfmon \
  -p 9001:9001 \
  -e SALESFORCE_AUTH_URL="your-sfdx-auth-url-here" \
  mcarvin8/sfmon:latest
```

### Environment Variables

SFMon is configured via environment variables. Here are the available options:

#### Required

- **`SALESFORCE_AUTH_URL`**: SFDX authentication URL for your Salesforce org
  - Generate this using: `sf org display --url-only` or `sfdx force:org:display --urlonly`
  - Format: `force://PlatformCLI::...`

#### Optional - Core Settings

- **`METRICS_PORT`**: Port for Prometheus metrics endpoint (default: `9001`)
  - Example: `-e METRICS_PORT=9001`

- **`CONFIG_FILE_PATH`**: Path to JSON configuration file (default: `/app/sfmon/config.json`)
  - Example: `-e CONFIG_FILE_PATH=/app/config/my-config.json`
  - See [Configuration File](#configuration-file) section below for details

- **`QUERY_TIMEOUT_SECONDS`**: Timeout in seconds for Salesforce SOQL queries (default: `30`)
  - Example: `-e QUERY_TIMEOUT_SECONDS=60` (increase timeout to 60 seconds for large queries)

- **`REQUESTS_TIMEOUT_SECONDS`**: Timeout in seconds for external HTTP requests like EventLogFile downloads and Trust API calls (default: `300`)
  - Example: `-e REQUESTS_TIMEOUT_SECONDS=600` (increase for slow network conditions)

- **`LOG_LEVEL`**: Logging verbosity level (default: `INFO`)
  - Options: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
  - Example: `-e LOG_LEVEL=DEBUG` (for troubleshooting)

#### Optional - Compliance Monitoring

- **`INTEGRATION_USER_NAMES`**: Comma-separated list of integration user names for compliance filtering
  - Example: `-e INTEGRATION_USER_NAMES="Integration User,Service Account,API User"`
  - Users in this list will be categorized as "Integration User" in audit metrics

- **`FORBIDDEN_PROD_PROFILES`**: Comma-separated list of profile names that should not be assigned in production
  - Example: `-e FORBIDDEN_PROD_PROFILES="Admin-SoD-PreProd-Delivery,System Administrator - Sandbox"`
  - Active users with these profiles will trigger compliance alerts

- **`LARGE_QUERY_THRESHOLD`**: Number of rows that constitutes a "large query" for compliance alerts (default: `10000`)
  - Example: `-e LARGE_QUERY_THRESHOLD=50000` (alert only for queries > 50k rows)

#### Optional - Tech Debt Thresholds

- **`DORMANT_USER_DAYS`**: Number of days of inactivity to consider a user dormant (default: `90`)
  - Example: `-e DORMANT_USER_DAYS=60` (flag users inactive for 60+ days)

- **`DEPRECATED_API_VERSION`**: API versions at or below this are considered deprecated (default: `50`)
  - Example: `-e DEPRECATED_API_VERSION=55` (flag Apex code on API v55 or below)

- **`PERMSET_LIMITED_USERS_THRESHOLD`**: Permission sets with this many or fewer users are flagged (default: `10`)
  - Example: `-e PERMSET_LIMITED_USERS_THRESHOLD=5` (flag permission sets with ≤5 users)

- **`PROFILE_UNDER_USERS_THRESHOLD`**: Profiles with this many or fewer users are flagged (default: `5`)
  - Example: `-e PROFILE_UNDER_USERS_THRESHOLD=3` (flag profiles with ≤3 users)

#### Optional - Performance Thresholds

- **`LONG_RUNNING_APEX_MS`**: Milliseconds threshold for long-running Apex requests (default: `5000`)
  - Example: `-e LONG_RUNNING_APEX_MS=10000` (10 seconds threshold)

- **`VERY_LONG_RUNNING_APEX_MS`**: Milliseconds threshold for very long-running Apex requests (default: `10000`)
  - Example: `-e VERY_LONG_RUNNING_APEX_MS=30000` (30 seconds threshold)

#### Optional - Geolocation Settings

- **`GEOLOCATION_CHUNK_SIZE`**: Batch size for user lookups in geolocation queries (default: `100`)
  - Example: `-e GEOLOCATION_CHUNK_SIZE=200` (larger batches for faster processing)

- **`GEOLOCATION_LOOKBACK_HOURS`**: Number of hours to look back for geolocation data (default: `1`)
  - Example: `-e GEOLOCATION_LOOKBACK_HOURS=24` (look back 24 hours)

#### Optional - External API Settings

- **`SALESFORCE_STATUS_API_URL`**: Base URL for Salesforce Trust status API (default: `https://api.status.salesforce.com`)
  - Example: `-e SALESFORCE_STATUS_API_URL=https://proxy.example.com/salesforce-status` (use proxy)

### Complete Example

```bash
docker run -d \
  --name sfmon \
  -p 9001:9001 \
  -e SALESFORCE_AUTH_URL="force://PlatformCLI::..." \
  -e METRICS_PORT=9001 \
  -e LOG_LEVEL=INFO \
  -e QUERY_TIMEOUT_SECONDS=60 \
  -e INTEGRATION_USER_NAMES="Integration User,Service Account" \
  -e FORBIDDEN_PROD_PROFILES="Admin-SoD-PreProd-Delivery" \
  -e DORMANT_USER_DAYS=90 \
  -e LARGE_QUERY_THRESHOLD=10000 \
  -e DEPRECATED_API_VERSION=50 \
  mcarvin8/sfmon:latest
```

### Verify It's Working

Check that metrics are being exposed:

```bash
curl http://localhost:9001/metrics
```

You should see Prometheus-formatted metrics output.

---

## ☁️ Platform-Agnostic Design

The SFMon container can be deployed in any of the following environments:

- **AWS ECS**
- **Kubernetes**
- **Google Cloud Run or Compute Engine VMs** — with Prometheus agent or OpenTelemetry collector
- **Azure Container Instances / AKS**
- **Self-hosted Docker environments**

The core components that make this possible:

- **Pre-built Docker image** (`mcarvin8/sfmon`) exposing metrics on configurable port
- **Python monitoring scripts** that authenticate to your Salesforce org and run scheduled checks
- **Prometheus-compatible metrics format**

---

## 📦 Core Components

### Python Monitoring Scripts

Located in `src/sfmon`, these scripts:

- Authenticate to Salesforce using the CLI
- Schedule and run custom monitoring jobs
- Export Prometheus-formatted metrics

You can customize:

- Monitoring intervals
- Org-specific logic (via environment variables)
- Additional checks

### Dockerfile

Located in `docker`, it:

- Installs Python and dependencies
- Copies in the monitoring scripts
- Sets the entrypoint to run `salesforce_monitoring.py`
- Exposes configurable port for Prometheus scraping

---

## 🔨 Building the Docker Image (Advanced)

If you need to build the image yourself or customize it:

**Required build argument**: Salesforce org SFDX auth URL (`SALESFORCE_AUTH_URL`)

Example:

```bash
docker build \
  --file "./docker/Dockerfile" \
  --build-arg SALESFORCE_AUTH_URL=$SALESFORCE_AUTH_URL \
  --tag your-repo/sfmon:latest .

docker push your-repo/sfmon:latest
```

> **Note**: The pre-built image `mcarvin8/sfmon` is recommended for most users. Build your own only if you need to customize the code.

---

## ⚙️ Customization

### Configuration File

SFMon uses a JSON configuration file to manage monitoring schedules and user configurations. **The config file is optional** - SFMon works out of the box with sensible defaults.

> **📋 Scheduling Behavior**
> 
> - **No config file?** → All jobs run with their **default schedules** (works out of the box!)
> - **Config file with schedules?** → **OPT-IN mode** - only jobs listed in `schedules` will run
> - **Config file without schedules?** → All jobs run with default schedules
> 
> This means you can start using SFMon immediately without any configuration. Create a config file only when you want to customize which jobs run or change their schedules.

**Configuration File Location:**
- Default: `/app/sfmon/config.json` (inside container)
- Override with: `CONFIG_FILE_PATH` environment variable
- Mount as volume: `-v /path/to/config.json:/app/sfmon/config.json`

**Configuration File Format:**

```json
{
  "schedules": {
    "monitor_salesforce_limits": "*/5",
    "get_salesforce_instance": "*/5",
    "monitor_apex_flex_queue": "*/5",
    "daily_analyse_bulk_api": "hour=7,minute=30",
    "hourly_analyse_bulk_api": "minute=5",
    "get_salesforce_licenses": "minute=15"
  },
  "integration_user_names": [
    "Integration User 1",
    "Integration User 2",
    "Service Account"
  ],
  "exclude_users": [
    "Admin User",
    "Integration User",
    "Service Account"
  ]
}
```

**Configuration Options:**

- **`schedules`** (object, optional): Defines which monitoring jobs run and their schedules
  - Key: Job ID in lowercase with underscores (e.g., `monitor_salesforce_limits`)
  - Value: Cron schedule string or `"disabled"` to explicitly disable
  - **If `schedules` is provided**: Only jobs listed will run (opt-in mode)
  - **If `schedules` is empty or not provided**: All jobs run with default schedules
  - See [Customizing Job Schedules](#customizing-job-schedules) for schedule formats and available job IDs

- **`integration_user_names`** (array, optional): List of integration user names for compliance filtering
  - Users in this list will be categorized as "Integration User" in audit metrics

- **`exclude_users`** (array, optional): List of user names to exclude from compliance monitoring
  - These users will not trigger compliance alerts for audit trail changes
  - Default: empty array (all users monitored)

**Example Docker Run with Config File:**

```bash
# Create config file (or use config.example.json as a template)
# IMPORTANT: Only jobs listed in "schedules" will run!
cat > config.json << EOF
{
  "schedules": {
    "monitor_salesforce_limits": "*/5",
    "get_salesforce_instance": "*/5",
    "monitor_apex_flex_queue": "*/5",
    "hourly_analyse_bulk_api": "minute=5",
    "get_salesforce_licenses": "minute=15",
    "get_deployment_status": "minute=55",
    "daily_analyse_bulk_api": "hour=7,minute=30"
  },
  "integration_user_names": ["Integration User", "Service Account"],
  "exclude_users": ["Admin User", "Integration User"]
}
EOF

# Run with mounted config file
docker run -d \
  --name sfmon \
  -p 9001:9001 \
  -e SALESFORCE_AUTH_URL="..." \
  -v $(pwd)/config.json:/app/sfmon/config.json \
  mcarvin8/sfmon:latest
```

> **Note**: An example configuration file (`config.example.json`) is included in the repository with all available job IDs and their recommended schedules.

**Note:** Environment variables are used for core runtime settings and thresholds. The configuration file is optional and only needed when you want to customize which jobs run or their schedules.

### Customizing Job Schedules

**Default Behavior (No Config File):**
If you don't provide a config file, **all monitoring jobs will run with their default schedules**. This is the recommended approach for most users who want comprehensive monitoring out of the box.

**Custom Scheduling (With Config File):**
When you provide a config file with a `schedules` section, SFMon switches to **opt-in mode** - only jobs explicitly listed will run. This gives you complete control over resource usage and which monitoring functions are active.

**Key Points:**
- **No config file** → All jobs run with default schedules
- **Config file with `schedules`** → Only listed jobs run (opt-in mode)
- **Config file without `schedules`** → All jobs run with default schedules
- Jobs run once at startup, then follow their configured schedule
- Use `"disabled"` value to explicitly disable a specific job

**Supported Schedule Formats:**
- Simple: `"*/5"` - Every 5 minutes
- Parameter: `"minute=*/5"` or `"hour=7,minute=30"` - Specific parameters
- Standard cron: `"*/5 * * * *"` - Full cron expression
- JSON: `'{"minute": "*/5", "hour": "7"}'` - JSON object

**Available Job IDs and Recommended Schedules:**

Copy the jobs you need into your `config.json`. Use lowercase with underscores.

| Job ID | Recommended Schedule | Description |
|--------|---------------------|-------------|
| **Critical (Every 5 minutes)** |||
| `monitor_salesforce_limits` | `*/5` | Org limits and API usage |
| `get_salesforce_instance` | `*/5` | Instance health status |
| `monitor_apex_flex_queue` | `*/5` | Apex flex queue depth |
| **Hourly (staggered 5 mins off the hour)** |||
| `hourly_analyse_bulk_api` | `minute=5` | Bulk API job analysis |
| `get_salesforce_licenses` | `minute=15` | License usage |
| `hourly_observe_user_querying_large_records` | `minute=25` | Large query compliance |
| `monitor_forbidden_profile_assignments` | `minute=35` | Users with forbidden profiles |
| `hourly_report_export_records` | `minute=45` | Report export tracking |
| `get_deployment_status` | `minute=55` | Deployment status |
| **Daily - Performance & Apex (06:00-07:35)** |||
| `get_salesforce_ept_and_apt` | `hour=6,minute=0` | EPT/APT metrics |
| `monitor_login_events` | `hour=6,minute=15` | Login event analysis |
| `async_apex_job_status` | `hour=6,minute=30` | Async job status |
| `monitor_apex_execution_time` | `hour=6,minute=45` | Apex execution times |
| `async_apex_execution_summary` | `hour=7,minute=0` | Async execution summary |
| `concurrent_apex_errors` | `hour=7,minute=15` | Concurrent Apex errors |
| `expose_apex_exception_metrics` | `hour=7,minute=25` | Apex exceptions |
| `expose_concurrent_long_running_apex_errors` | `hour=7,minute=35` | Concurrent long-running Apex |
| **Daily - Business & Compliance (07:30-08:30)** |||
| `daily_analyse_bulk_api` | `hour=7,minute=30` | Daily bulk API summary |
| `geolocation` | `hour=8,minute=0` | Login geolocation |
| `expose_suspicious_records` | `hour=8,minute=15` | Suspicious audit trail records |
| `monitor_org_wide_sharing_settings` | `hour=8,minute=30` | OWD changes |
| **Daily - Tech Debt (02:00-06:00) OFF-PEAK** |||
| `unassigned_permission_sets` | `hour=2,minute=0` | Unused permission sets |
| `perm_sets_limited_users` | `hour=2,minute=15` | Low-usage permission sets |
| `profile_assignment_under5` | `hour=2,minute=30` | Profiles with <5 users |
| `profile_no_active_users` | `hour=2,minute=45` | Profiles with no users |
| `apex_classes_api_version` | `hour=3,minute=0` | Outdated Apex classes |
| `apex_triggers_api_version` | `hour=3,minute=15` | Outdated Apex triggers |
| `security_health_check` | `hour=3,minute=30` | Security health score |
| `salesforce_health_risks` | `hour=3,minute=45` | Security risks |
| `workflow_rules_monitoring` | `hour=4,minute=0` | Legacy workflow rules |
| `dormant_salesforce_users` | `hour=4,minute=15` | Dormant SF users |
| `dormant_portal_users` | `hour=4,minute=30` | Dormant portal users |
| `total_queues_per_object` | `hour=4,minute=45` | Queue distribution |
| `queues_with_no_members` | `hour=5,minute=0` | Empty queues |
| `queues_with_zero_open_cases` | `hour=5,minute=15` | Inactive case queues |
| `public_groups_with_no_members` | `hour=5,minute=30` | Empty public groups |
| `dashboards_with_inactive_users` | `hour=5,minute=45` | Dashboards with inactive users |
| `scheduled_apex_jobs_monitoring` | `hour=5,minute=55` | Scheduled Apex jobs |

**No Config Needed (Recommended for most users):**

Simply run SFMon without a config file to get all monitoring jobs with default schedules:

```bash
docker run -d \
  --name sfmon \
  -p 9001:9001 \
  -e SALESFORCE_AUTH_URL="..." \
  mcarvin8/sfmon:latest
```

**Minimal Example (Run only critical jobs):**

To run only specific jobs, create a config file with those jobs:

```json
{
  "schedules": {
    "monitor_salesforce_limits": "*/5",
    "get_salesforce_instance": "*/5",
    "monitor_apex_flex_queue": "*/5"
  }
}
```

**Full Example (All jobs with custom schedules):**

See `config.example.json` in the repository for a complete configuration with all jobs and their recommended schedules.

**Running with Custom Config:**

```bash
docker run -d \
  --name sfmon \
  -p 9001:9001 \
  -e SALESFORCE_AUTH_URL="..." \
  -v $(pwd)/config.json:/app/sfmon/config.json \
  mcarvin8/sfmon:latest
```

### Configuring Integration Users and Forbidden Profiles

SFMon uses environment variables to configure compliance monitoring:

**Integration User Names:**
Users listed in `INTEGRATION_USER_NAMES` are categorized as "Integration User" in audit metrics, allowing you to filter them in Grafana dashboards.

```bash
-e INTEGRATION_USER_NAMES="Integration User,Service Account,API User"
```

**Forbidden Production Profiles:**
Profiles listed in `FORBIDDEN_PROD_PROFILES` will trigger compliance alerts if assigned to active users.

```bash
-e FORBIDDEN_PROD_PROFILES="Admin-SoD-PreProd-Delivery,System Administrator - Sandbox"
```

> **Note**: If these environment variables are not set, the corresponding monitoring functions will skip their checks gracefully.

---

## 📊 Grafana Dashboard

Import the JSON files in `grafana` to get started with ready-to-use SFMon dashboards for general ops, auditing, and tech debt. Customize based on your Prometheus data source, orgs and alerting requirements.

---

## ✍️ Authors

Originally developed by **Deep Suthar** and **Matt Carvin** for ECS deployment and Kubernetes deployment at Avalara.

---
