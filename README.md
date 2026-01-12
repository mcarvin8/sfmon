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

#### Optional

- **`METRICS_PORT`**: Port for Prometheus metrics endpoint (default: `9001`)
  - Example: `-e METRICS_PORT=9001`

- **`CONFIG_FILE_PATH`**: Path to JSON configuration file (default: `/app/sfmon/config.json`)
  - Example: `-e CONFIG_FILE_PATH=/app/config/my-config.json`
  - See [Configuration File](#configuration-file) section below for details

- **`QUERY_TIMEOUT_SECONDS`**: Timeout in seconds for Salesforce SOQL queries (default: `30`)
  - Example: `-e QUERY_TIMEOUT_SECONDS=60` (increase timeout to 60 seconds for large queries)

- **`INTEGRATION_USER_NAMES`**: Comma-separated list of integration user names for compliance filtering
  - Example: `-e INTEGRATION_USER_NAMES="Integration User,Service Account,API User"`
  - Users in this list will be categorized as "Integration User" in audit metrics

- **`FORBIDDEN_PROD_PROFILES`**: Comma-separated list of profile names that should not be assigned in production
  - Example: `-e FORBIDDEN_PROD_PROFILES="Admin-SoD-PreProd-Delivery,System Administrator - Sandbox"`
  - Active users with these profiles will trigger compliance alerts

### Complete Example

```bash
docker run -d \
  --name sfmon \
  -p 9001:9001 \
  -e SALESFORCE_AUTH_URL="force://PlatformCLI::..." \
  -e METRICS_PORT=9001 \
  -e INTEGRATION_USER_NAMES="Integration User,Service Account" \
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

SFMon uses a JSON configuration file to manage all monitoring settings, schedules, and user configurations. This is the primary method for customizing SFMon behavior.

> **⚠️ IMPORTANT: OPT-IN Configuration**
> 
> SFMon uses an **opt-in approach** for job scheduling. Only jobs explicitly defined in the `schedules` section of your config file will run. Jobs not listed will be **skipped**. This gives you full control over which monitoring functions are active.

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
    "hourly_analyse_bulk_api": "minute=0",
    "get_salesforce_licenses": "minute=10,50"
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

- **`schedules`** (object, **required for jobs to run**): Defines which monitoring jobs run and their schedules
  - Key: Job ID in lowercase with underscores (e.g., `monitor_salesforce_limits`)
  - Value: Cron schedule string or `"disabled"` to explicitly disable
  - **Only jobs listed here will run** - unlisted jobs are skipped
  - See [Customizing Job Schedules](#customizing-job-schedules) for schedule formats and available job IDs

- **`integration_user_names`** (array, optional): List of integration user names to monitor for password expiration
  - If not provided, password expiration monitoring will be skipped

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
    "hourly_analyse_bulk_api": "minute=0",
    "get_salesforce_licenses": "minute=10,50",
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

> **Note**: An example configuration file (`config.example.json`) is included in the repository with all available job IDs and their recommended schedules. **Copy this file and customize it** - only jobs you include will run.

**Note:** All scheduling and user configuration is managed through the configuration file. Environment variables are only used for core runtime settings (SALESFORCE_AUTH_URL, METRICS_PORT, QUERY_TIMEOUT_SECONDS, CONFIG_FILE_PATH).

### Customizing Job Schedules

SFMon uses an **opt-in approach** - only jobs explicitly listed in your `config.json` will run. This gives you complete control over resource usage and which monitoring functions are active.

**Key Points:**
- **Only jobs in `schedules` will run** - unlisted jobs are skipped entirely
- Jobs run once at startup, then follow their configured schedule
- Use `"disabled"` value to explicitly document a disabled job

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
| **Hourly** |||
| `hourly_analyse_bulk_api` | `minute=0` | Bulk API job analysis |
| `get_salesforce_licenses` | `minute=10,50` | License usage |
| `hourly_observe_user_querying_large_records` | `minute=20` | Large query compliance |
| `hourly_report_export_records` | `minute=40` | Report export tracking |
| `monitor_forbidden_profile_assignments` | `minute=30` | Users with forbidden profiles |
| **Daily - Performance (06:00-07:30)** |||
| `get_salesforce_ept_and_apt` | `hour=6,minute=0` | EPT/APT metrics |
| `monitor_login_events` | `hour=6,minute=15` | Login event analysis |
| `async_apex_job_status` | `hour=6,minute=30` | Async job status |
| `monitor_apex_execution_time` | `hour=6,minute=45` | Apex execution times |
| `async_apex_execution_summary` | `hour=7,minute=0` | Async execution summary |
| `concurrent_apex_errors` | `hour=7,minute=15` | Concurrent Apex errors |
| `expose_apex_exception_metrics` | `hour=7,minute=30` | Apex exceptions |
| **Daily - Business (07:30-09:00)** |||
| `daily_analyse_bulk_api` | `hour=7,minute=30` | Daily bulk API summary |
| `get_deployment_status` | `hour=7,minute=45` | Deployment status |
| `geolocation` | `hour=8,minute=0` | Login geolocation |
| `expose_suspicious_records` | `hour=8,minute=30` | Suspicious audit trail records |
| `monitor_org_wide_sharing_settings` | `hour=8,minute=45` | OWD changes |
| **Daily - Tech Debt (09:15-13:15)** |||
| `unassigned_permission_sets` | `hour=9,minute=15` | Unused permission sets |
| `perm_sets_limited_users` | `hour=9,minute=30` | Low-usage permission sets |
| `profile_assignment_under5` | `hour=9,minute=45` | Profiles with <5 users |
| `profile_no_active_users` | `hour=10,minute=0` | Profiles with no users |
| `apex_classes_api_version` | `hour=10,minute=15` | Outdated Apex classes |
| `apex_triggers_api_version` | `hour=10,minute=30` | Outdated Apex triggers |
| `security_health_check` | `hour=10,minute=45` | Security health score |
| `salesforce_health_risks` | `hour=11,minute=0` | Security risks |
| `workflow_rules_monitoring` | `hour=11,minute=15` | Legacy workflow rules |
| `dormant_salesforce_users` | `hour=11,minute=30` | Dormant SF users |
| `dormant_portal_users` | `hour=11,minute=45` | Dormant portal users |
| `total_queues_per_object` | `hour=12,minute=0` | Queue distribution |
| `queues_with_no_members` | `hour=12,minute=15` | Empty queues |
| `queues_with_zero_open_cases` | `hour=12,minute=30` | Inactive case queues |
| `public_groups_with_no_members` | `hour=12,minute=45` | Empty public groups |
| `dashboards_with_inactive_users` | `hour=13,minute=0` | Dashboards with inactive users |
| `scheduled_apex_jobs_monitoring` | `hour=13,minute=15` | Scheduled Apex jobs |

**Minimal Example (Critical jobs only):**

```json
{
  "schedules": {
    "monitor_salesforce_limits": "*/5",
    "get_salesforce_instance": "*/5",
    "monitor_apex_flex_queue": "*/5"
  }
}
```

**Full Example (All recommended jobs):**

See `config.example.json` in the repository for a complete configuration with all jobs enabled.

**Running with Config:**

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

## 📊 Prometheus Configuration

To scrape metrics from SFMon, add the following to your Prometheus configuration:

```yaml
scrape_configs:
  - job_name: 'sfmon'
    static_configs:
      - targets: ['sfmon:9001']  # Adjust hostname/port as needed
    scrape_interval: 30s
    scrape_timeout: 10s
```

For Kubernetes deployments, use service discovery:

```yaml
scrape_configs:
  - job_name: 'sfmon'
    kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
            - default
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_name]
        regex: 'sfmon.*'
        action: keep
```

---

## 📊 Grafana Dashboard

Import the JSON file in `grafana` to get started with a ready-to-use SFMon dashboard. Customize based on your orgs and alerting requirements.

---

## 🔐 Security Notes

- Never commit your **SFDX auth URLs**.
- Use secrets management systems (e.g., AWS Secrets Manager, GCP Secret Manager, or Kubernetes Secrets).
- Ensure your Prometheus server can access the metrics port (default: `9001`) of the SFMon container.
- Store sensitive environment variables securely and pass them at runtime, not in Dockerfiles.

### Using Secrets with Docker

```bash
# Using Docker secrets or environment files
docker run -d \
  --name sfmon \
  -p 9001:9001 \
  --env-file .env \
  mcarvin8/sfmon:latest
```

### Kubernetes Example

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: sfmon
spec:
  containers:
  - name: sfmon
    image: mcarvin8/sfmon:latest
    ports:
    - containerPort: 9001
    env:
    - name: SALESFORCE_AUTH_URL
      valueFrom:
        secretKeyRef:
          name: sfmon-secrets
          key: salesforce-auth-url
    - name: METRICS_PORT
      value: "9001"
    - name: INTEGRATION_USER_NAMES
      valueFrom:
        secretKeyRef:
          name: sfmon-secrets
          key: integration-users
```

---

## ✍️ Authors

Originally developed by **Deep Suthar** and **Matt Carvin** for ECS deployment and Kubernetes deployment at Avalara.

---
