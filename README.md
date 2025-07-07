# Salesforce Monitoring (SFMon)

**SFMon** is a portable, custom-built Docker container that collects Salesforce org metrics and exposes them via an HTTP endpoint for scraping by **Prometheus**. It enables teams to gain visibility into Salesforce performance, usage, configuration, and incidents—no matter what cloud platform they use.

> While this repository provides configuration for AWS ECS, **SFMon can be deployed on any platform** that supports Docker and Prometheus, including GCP, Azure, or Kubernetes-based environments.

A prebuilt **Grafana dashboard** is included to help you visualize metrics right away.

---

## ☁️ Platform-Agnostic Design

The SFMon container can be deployed in any of the following environments:

- **AWS ECS (default example in this repo)**
- **Google Kubernetes Engine (GKE)** — using `PodMonitor` or scraping annotations
- **Google Cloud Run or Compute Engine VMs** — with Prometheus agent or OpenTelemetry collector
- **Azure Container Instances / AKS**
- **Self-hosted Docker environments**

The core components that make this possible:

- **Custom Dockerfile** exposing metrics on port `9001`
- **Python monitoring scripts** that authenticate to your Salesforce org and run scheduled checks
- **Prometheus-compatible metrics format**

---

## 🚀 Quick Start (with AWS ECS)

This project includes Terraform configurations for running SFMon on **AWS ECS**:

1. **Provision AWS Infrastructure** – ECS Cluster, Prometheus service, IAM roles, security groups.
2. **Build & Push Docker Image** – Include your Salesforce auth URL as a build argument.
3. **Deploy to ECS** – Launch the containerized service using Terraform.
4. **Configure Grafana** – Import the sample dashboard and connect it to your Prometheus instance.

---

## 📦 Core Components

### Python Monitoring Scripts

Located in `sre/deployments/scripts/sfmon-service`, these scripts:

- Authenticate to Salesforce using the CLI
- Schedule and run custom monitoring jobs
- Export Prometheus-formatted metrics

You can customize:

- Monitoring intervals
- Org-specific logic
- Additional checks

### Dockerfile

Located in `sre/deployments/docker/sfmon-service`, it:

- Installs Python and dependencies
- Copies in the monitoring scripts
- Sets the entrypoint to run `salesforce_monitoring.py`
- Exposes port `9001` for Prometheus scraping

---

## 🔨 Building the Docker Image

You'll need to build and push the image to your preferred container registry (e.g., ECR, GCR, Docker Hub).

**Required build argument**: Salesforce org SFDX auth URL.

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

Import the JSON file in `configs/grafana` to get started with a ready-to-use SFMon dashboard. Customize based on your orgs and alerting requirements.

---

## 🔐 Security Notes

- Never commit your **SFDX auth URLs**.
- Use secrets management systems (e.g., AWS Secrets Manager, GCP Secret Manager, or Kubernetes Secrets).
- Ensure your Prometheus server can access port `9001` of the SFMon container.

---

## ✍️ Authors

Originally developed by **Deep Suthar** and **Matt Carvin** for ECS deployment at Avalara.

---

## 🔄 Alternatives & Extensions

If you’re not on AWS, you can:

- Replace ECS with Kubernetes and expose the metrics endpoint as a service
- Run SFMon as a sidecar or standalone Docker container on GCP/Azure
- Push metrics to alternative backends (e.g., Google Cloud Monitoring) via an OpenTelemetry Collector
