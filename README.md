# Salesforce Monitoring (SFMon)

This project provides the necessary resources to deploy a Salesforce Monitoring (SFMon) service on AWS ECS. SFMon monitors your Salesforce orgs by leveraging a custom Docker image hosted in AWS Elastic Container Registry (ECR) and creates Prometheus targets for a Prometheus ECS.

A Grafana dashboard can be used to visualize the Prometheus targets created by SFMon.

## Overview

SFMon runs as an ECS service using a Docker image that contains the required Python environment and Salesforce dependencies (Simple Salesforce & Salesforce CLI). It periodically authenticates with your Salesforce orgs and collects monitoring data.

## Authors

Originally developed by Deep Suthar and Matt Carvin.

## Prerequisites

Before you can deploy SFMon ECS, you must provision the following AWS infrastructure:

- An ECS Cluster to host the SFMon service (you can deploy 1 using `sre/deployments/terraform/ecs-cluster`)
- A Prometheus ECS Service to scrape and store metrics from the ECS cluster (you can deploy 1 using `sre/deployments/terraform/promethes-service`)
- The ECS Exec Command IAM policy to allow troubleshooting access into containers if needed (you can deploy 1 using `sre/deployments/terraform/ecs-exec-command-policy`)
- `sre/deployments/terraform/sfmon-service/prereqs`
    - ECR for SFMon images
    - IAM role for SFMon
    - Security Groups for SFMon
    - Cloudwatch logging group for SFMon

## Modifying Scripts

The Python scripts which runs the monitoring services are hosted in `sre/deployments/scripts/sfmon-service`.

The primary script is `salesforce_monitoring.py` which is what the Docker image runs at launch.

This script imports all monitoring functions, authenticates to each Salesforce org with Simple Salesforce/Salesforce CLI, runs all monitoring functions at launch, and then schedules each function to run at different intervals.

You should update `salesforce_monitoring.py` as such for your orgs:
- Update the Force Auth URL variables stored in the environment before authenticating to each org, if you wish to use other variables besides the 4 variables provided
- Remove any monitoring functions you do not want to use
- Add any monitoring functions you would like to add not covered
- Update the schedules which the monitoring functions run on

I would recommend going through all other scripts to verify they are what you want to use and modify the queries as needed for your orgs.

Currently, the production org is the primary org monitored by these scripts.

The 3 sandboxes are monitored for incidents, email deliverability setting changes, and payment gateway/method status changes.

## Building and Publishing the Docker Image

SFMon depends on a custom Docker image that needs to be built and pushed to the SFMon AWS ECR repository.

When building the image, you must provide the SFDX authorization URLs for each Salesforce org you intend to monitor. These URLs are passed as build arguments during the Docker build process.

Example Docker build and push commands:

```
# Login to the AWS ECR using the docker-login tf files
cd sre/deployments/terraform/docker-login && terraform init -input=false && terraform apply -input=false -auto-approve
docker build \
  --file "./sre/deployments/docker/sfmon-service/Dockerfile"
  --build-arg PRODUCTION_AUTH_URL=$PRODUCTION_AUTH_URL \
  --build-arg FULLQA_AUTH_URL=$FULLQA_AUTH_URL \
  --build-arg FULLQAB_AUTH_URL=$FULLQAB_AUTH_URL \
  --build-arg DEV_AUTH_URL=$DEV_AUTH_URL \
  --tag $ECR_REPO:$CI_COMMIT_SHORT_SHA .
docker push $ECR_REPO:$CI_COMMIT_SHORT_SHA
```

## Deploying SFMon to ECS

After your image is published to ECR and the other AWS infrastructure is created to run the ECS:

1. Create or update your ECS Task Definition to use the new Docker image.
2. Deploy the SFMon service using Terraform to your ECS cluster.
    - `sre\deployments\terraform\sfmon-service\ecs-service`

## Grafana

`configs\grafana` contains a sample Grafana dashboard you can update for your orgs.

## Notes

- Each Salesforce org to be monitored must have a corresponding SFDX AUTH URL.
- Keep your SFDX authentication URLs secure and updated as needed.
- This setup assumes you are running Prometheus and scraping targets from the ECS cluster that the SFMon ECS lives in.

## Alternatives

The heart of this repository is the Python scripts in `sre/deployments/scripts/sfmon-service` and the Dockerfile in `sre/deployments/docker/sfmon-service` which copies the Python scripts and launches the main script at run-time to schedule/run the monitoring functions.

The Docker image exposes Port 9001 for Prometheus metrics. The Docker container with the scripts can easily be deployed to other container registries and uses in services like Google Cloud Managed Service for Prometheus.

- If you're running in GKE, add a PodMonitor or use Kubernetes annotations to enable scraping.
- For Cloud Run or VM users, run a Prometheus agent or OpenTelemetry Collector configured to scrape the metrics endpoint and forward data to Google Cloud Monitoring.
