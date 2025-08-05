# Salesforce Monitoring (SFMon)

**SFMon** is a portable, custom-built Docker container that collects Salesforce org metrics and exposes them via an HTTP endpoint for scraping by **Prometheus**. It enables teams to gain visibility into Salesforce performance, usage, configuration, and incidents—no matter what cloud platform they use.

> **SFMon can be deployed on any platform** that supports Docker and Prometheus, including GCP, Azure, or Kubernetes-based environments. It has been tested and verified on AWS ECS and Kubernetes.

A prebuilt **Grafana dashboard** is included to help you visualize metrics right away.

---

## ☁️ Platform-Agnostic Design

The SFMon container can be deployed in any of the following environments:

- **AWS ECS**
- **Kubernetes**
- **Google Cloud Run or Compute Engine VMs** — with Prometheus agent or OpenTelemetry collector
- **Azure Container Instances / AKS**
- **Self-hosted Docker environments**

The core components that make this possible:

- **Custom Dockerfile** exposing metrics on port `9001`
- **Python monitoring scripts** that authenticate to your Salesforce org and run scheduled checks
- **Prometheus-compatible metrics format**

---

## 📦 Core Components

### Python Monitoring Scripts

Located in `scripts`, these scripts:

- Authenticate to Salesforce using the CLI
- Schedule and run custom monitoring jobs
- Export Prometheus-formatted metrics

You can customize:

- Monitoring intervals
- Org-specific logic
- Additional checks

### Dockerfile

Located in `docker`, it:

- Installs Python and dependencies
- Copies in the monitoring scripts
- Sets the entrypoint to run `salesforce_monitoring.py`
- Exposes port `9001` for Prometheus scraping

---

## 🔨 Building the Docker Image

You'll need to build and push the image to your preferred container registry (e.g., ECR, GCR, Docker Hub).

**Required build argument**: Salesforce org SFDX auth URL (`SALESFORCE_AUTH_URL`)

Example:

```bash
docker build \
  --file "./sre/deployments/docker/sfmon-service/Dockerfile" \
  --build-arg SALESFORCE_AUTH_URL=$SALESFORCE_AUTH_URL \
  --tag your-repo/sfmon:latest .

docker push your-repo/sfmon:latest
```

---

## 📊 Grafana Dashboard

Import the JSON file in `grafana` to get started with a ready-to-use SFMon dashboard. Customize based on your orgs and alerting requirements.

---

## 🔐 Security Notes

- Never commit your **SFDX auth URLs**.
- Use secrets management systems (e.g., AWS Secrets Manager, GCP Secret Manager, or Kubernetes Secrets).
- Ensure your Prometheus server can access port `9001` of the SFMon container.

---

## ✍️ Authors

Originally developed by **Deep Suthar** and **Matt Carvin** for ECS deployment and Kubernetes deployment at Avalara.

---
