# Salesforce Monitoring (SFMon)

![Docker Image Version (latest by date)](https://img.shields.io/docker/v/mcarvin8/sfmon?sort=date)
![Docker Pulls](https://img.shields.io/docker/pulls/mcarvin8/sfmon)
![Docker Image Size (latest by date)](https://img.shields.io/docker/image-size/mcarvin8/sfmon)

**SFMon** is a portable, custom-built Docker container that collects Salesforce org metrics and exposes them via an HTTP endpoint for scraping by **Prometheus**. It enables teams to gain visibility into Salesforce performance, usage, configuration, technical debt, and incidents—no matter what cloud platform they use.

> **SFMon can be deployed on any platform** that supports Docker and Prometheus, including GCP, Azure, or Kubernetes-based environments. It has been tested and verified on AWS ECS and Kubernetes.

A prebuilt **Grafana dashboard** is included to help you visualize metrics right away.

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

**Configuration File Location:**
- Default: `/app/sfmon/config.json` (inside container)
- Override with: `CONFIG_FILE_PATH` environment variable
- Mount as volume: `-v /path/to/config.json:/app/sfmon/config.json`

**Configuration File Format:**

```json
{
  "schedules": {
    "monitor_salesforce_limits": "*/10",
    "daily_analyse_bulk_api": "hour=8,minute=0",
    "geolocation": "disabled",
    "unassigned_permission_sets": "hour=9,minute=15"
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

- **`schedules`** (object, optional): Custom schedules for monitoring jobs
  - Key: Job ID in lowercase with underscores (e.g., `monitor_salesforce_limits`)
  - Value: Cron schedule string or `"disabled"` to skip the job
  - See [Customizing Job Schedules](#customizing-job-schedules) for schedule formats

- **`integration_user_names`** (array, optional): List of integration user names to monitor for password expiration
  - If not provided, password expiration monitoring will be skipped

- **`exclude_users`** (array, optional): List of user names to exclude from compliance monitoring
  - These users will not trigger compliance alerts for audit trail changes
  - Default: empty array (all users monitored)

**Example Docker Run with Config File:**

```bash
# Create config file (or use config.example.json as a template)
cat > config.json << EOF
{
  "schedules": {
    "monitor_salesforce_limits": "*/10",
    "geolocation": "disabled"
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

> **Note**: An example configuration file (`config.example.json`) is included in the repository with all available job IDs and their default schedules. Use it as a starting point for your own configuration.

**Note:** All scheduling and user configuration is managed through the configuration file. Environment variables are only used for core runtime settings (SALESFORCE_AUTH_URL, METRICS_PORT, QUERY_TIMEOUT_SECONDS, CONFIG_FILE_PATH).

### Customizing Job Schedules

You can customize when monitoring jobs run by configuring schedules in the `config.json` file. This allows you to:
- Change execution frequency (e.g., run every 10 minutes instead of 5)
- Change execution times (e.g., run daily jobs at different hours)
- Disable specific jobs you don't need

**Supported Schedule Formats:**
- Simple: `"*/5"` - Every 5 minutes
- Parameter: `"minute=*/5"` or `"hour=7,minute=30"` - Specific parameters
- Standard cron: `"*/5 * * * *"` - Full cron expression
- JSON: `'{"minute": "*/5", "hour": "7"}'` - JSON object

**Available Job IDs:**
- `MONITOR_SALESFORCE_LIMITS` (default: every 5 minutes)
- `GET_SALESFORCE_INSTANCE` (default: every 5 minutes)
- `MONITOR_APEX_FLEX_QUEUE` (default: every 5 minutes)
- `HOURLY_ANALYSE_BULK_API` (default: every hour at :00)
- `GET_SALESFORCE_LICENSES` (default: every hour at :10 and :50)
- `HOURLY_OBSERVE_USER_QUERYING_LARGE_RECORDS` (default: every hour at :20)
- `HOURLY_REPORT_EXPORT_RECORDS` (default: every hour at :40)
- `DAILY_ANALYSE_BULK_API` (default: daily at 7:30 AM)
- `GET_DEPLOYMENT_STATUS` (default: daily at 7:45 AM)
- `GEOLOCATION` (default: daily at 8:00 AM)
- `MONITOR_ORG_WIDE_SHARING_SETTINGS` (default: daily at 8:45 AM)
- `MONITOR_INTEGRATION_USER_PASSWORDS` (default: daily at 9:00 AM)
- `GET_SALESFORCE_EPT_AND_APT` (default: daily at 6:00 AM)
- `MONITOR_LOGIN_EVENTS` (default: daily at 6:15 AM)
- `ASYNC_APEX_JOB_STATUS` (default: daily at 6:30 AM)
- `MONITOR_APEX_EXECUTION_TIME` (default: daily at 6:45 AM)
- `ASYNC_APEX_EXECUTION_SUMMARY` (default: daily at 7:00 AM)
- `CONCURRENT_APEX_ERRORS` (default: daily at 7:15 AM)
- `EXPOSE_APEX_EXCEPTION_METRICS` (default: daily at 7:30 AM)
- `UNASSIGNED_PERMISSION_SETS` (default: daily at 9:15 AM)
- `PERM_SETS_LIMITED_USERS` (default: daily at 9:30 AM)
- `PROFILE_ASSIGNMENT_UNDER5` (default: daily at 9:45 AM)
- `PROFILE_NO_ACTIVE_USERS` (default: daily at 10:00 AM)
- `APEX_CLASSES_API_VERSION` (default: daily at 10:15 AM)
- `APEX_TRIGGERS_API_VERSION` (default: daily at 10:30 AM)
- `SECURITY_HEALTH_CHECK` (default: daily at 10:45 AM)
- `SALESFORCE_HEALTH_RISKS` (default: daily at 11:00 AM)
- `WORKFLOW_RULES_MONITORING` (default: daily at 11:15 AM)
- `DORMANT_SALESFORCE_USERS` (default: daily at 11:30 AM)
- `DORMANT_PORTAL_USERS` (default: daily at 11:45 AM)
- `TOTAL_QUEUES_PER_OBJECT` (default: daily at 12:00 PM)
- `QUEUES_WITH_NO_MEMBERS` (default: daily at 12:15 PM)
- `QUEUES_WITH_ZERO_OPEN_CASES` (default: daily at 12:30 PM)
- `PUBLIC_GROUPS_WITH_NO_MEMBERS` (default: daily at 12:45 PM)
- `DASHBOARDS_WITH_INACTIVE_USERS` (default: daily at 1:00 PM)

**Examples:**

Configure schedules in your `config.json`:

```json
{
  "schedules": {
    "monitor_salesforce_limits": "*/10",
    "daily_analyse_bulk_api": "hour=9,minute=0",
    "geolocation": "disabled"
  }
}
```

Then mount the config file when running the container:

```bash
docker run -d \
  --name sfmon \
  -p 9001:9001 \
  -e SALESFORCE_AUTH_URL="..." \
  -v $(pwd)/config.json:/app/sfmon/config.json \
  mcarvin8/sfmon:latest
```

### Excluding Users from Compliance Monitoring

By default, all users are monitored for compliance violations. To exclude specific admin or integration users, you'll need to modify the `EXCLUDE_USERS` constant in `src/sfmon/constants.py` before building your own image:

```python
# In src/sfmon/constants.py
EXCLUDE_USERS = ['Admin User 1', 'Integration User 2', 'Service Account']
```

> **Note**: If you're using the pre-built `mcarvin8/sfmon` image, you'll need to build your own customized image to modify `EXCLUDE_USERS`. This is a code-level configuration, not an environment variable.

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
