# Salesforce Monitoring (SFMon)

**SFMon** is a portable, custom-built Docker container that collects Salesforce org metrics and exposes them via an HTTP endpoint for scraping by **Prometheus**. It enables teams to gain visibility into Salesforce performance, usage, configuration, and incidents—no matter what cloud platform they use.

> **SFMon can be deployed on any platform** that supports Docker and Prometheus, including GCP, Azure, or Kubernetes-based environments. It has been tested and verified on AWS ECS and Kubernetes.

A prebuilt **Grafana dashboard** is included to help you visualize metrics right away.

---

## 🚀 Quick Start

### Using the Pre-built Docker Image

The easiest way to get started is using the pre-built image from Docker Hub:

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

- **`INTEGRATION_USER_NAMES`**: Comma-separated list of integration user names to monitor for password expiration
  - Example: `-e INTEGRATION_USER_NAMES="Integration User 1,Integration User 2,Service Account"`
  - If not provided, password expiration monitoring will be skipped

- **`SCHEDULE_<JOB_ID>`**: Custom cron schedule for any monitoring job (optional)
  - Format: `minute=*/5`, `hour=7,minute=30`, `*/5 * * * *`, or JSON `{"minute": "*/5"}`
  - Set to `disabled` or empty to skip a job
  - Example: `-e SCHEDULE_MONITOR_SALESFORCE_LIMITS="*/10"` (run every 10 minutes instead of 5)
  - Example: `-e SCHEDULE_DAILY_ANALYSE_BULK_API="hour=8,minute=0"` (run at 8:00 AM instead of 7:30 AM)
  - Example: `-e SCHEDULE_GEOLOCATION="disabled"` (disable geolocation monitoring)

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

### Customizing Job Schedules

You can customize when monitoring jobs run using environment variables with the pattern `SCHEDULE_<JOB_ID>`. This allows you to:
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

**Examples:**

```bash
# Run limits check every 10 minutes instead of 5
docker run -d \
  --name sfmon \
  -p 9001:9001 \
  -e SALESFORCE_AUTH_URL="..." \
  -e SCHEDULE_MONITOR_SALESFORCE_LIMITS="*/10" \
  mcarvin8/sfmon:latest

# Change daily bulk API analysis to run at 9:00 AM instead of 7:30 AM
docker run -d \
  --name sfmon \
  -p 9001:9001 \
  -e SALESFORCE_AUTH_URL="..." \
  -e SCHEDULE_DAILY_ANALYSE_BULK_API="hour=9,minute=0" \
  mcarvin8/sfmon:latest

# Disable geolocation monitoring
docker run -d \
  --name sfmon \
  -p 9001:9001 \
  -e SALESFORCE_AUTH_URL="..." \
  -e SCHEDULE_GEOLOCATION="disabled" \
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
