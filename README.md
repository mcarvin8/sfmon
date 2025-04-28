# Salesforce Monitoring (SFMon)

This project provides the necessary resources to deploy a Salesforce Monitoring (SFMon) service on AWS ECS. SFMon monitors your Salesforce orgs by leveraging a custom Docker image hosted in AWS Elastic Container Registry (ECR).

## Overview

SFMon runs as an ECS service using a Docker image that contains the required Python environment and Salesforce dependencies. It periodically authenticates with your Salesforce orgs and collects monitoring data.

## Authors

Originally developed by Deep Suthar and Matt Carvin.

## Prerequisites

Before you can deploy SFMon, you must provision the following AWS infrastructure:

- An ECS Cluster to host the SFMon service
- A Prometheus ECS Service to scrape and store metrics
- The ECS Exec Command IAM policy to allow troubleshooting access into containers if needed

## Building and Publishing the Docker Image

SFMon depends on a custom Docker image that needs to be built and pushed to your ECR repository.

When building the image, you must provide authentication URLs for each Salesforce org you intend to monitor. These URLs are passed as build arguments during the Docker build process.

Example Docker build command:

```
docker build \
  --build-arg PRODUCTION_AUTH_URL="https://login.salesforce.com/services/oauth2/authorize?..." \
  --build-arg FULLQA_AUTH_URL="https://test.salesforce.com/services/oauth2/authorize?..." \
  --build-arg FULLQAB_AUTH_URL="https://test.salesforce.com/services/oauth2/authorize?..." \
  --build-arg DEV_AUTH_URL="https://test.salesforce.com/services/oauth2/authorize?..." \
  -t <your-ecr-repo>/sfmon:latest .


Once built, push the image to your ECR:

```
aws ecr get-login-password --region <your-region> | docker login --username AWS --password-stdin <your-account-id>.dkr.ecr.<your-region>.amazonaws.com
docker push <your-ecr-repo>/sfmon:latest
```

## Deploying SFMon to ECS

After your image is published to ECR:

1. Create or update your ECS Task Definition to use the new Docker image.
2. Deploy the SFMon service to your ECS cluster.
3. Ensure the ECS service has the necessary permissions to pull the image from ECR and execute commands.

## Notes

- Each Salesforce org to be monitored must have a corresponding AUTH URL.
- Keep your authentication URLs secure and updated as needed.
- This setup assumes you are running Prometheus and scraping targets from the ECS cluster that the SFMon ECS lives in.
