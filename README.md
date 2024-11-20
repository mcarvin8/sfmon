# Salesforce Monitoring (SFMon)

This project contains Terraform files required to build an AWS ECS to monitor your Salesforce org.

## Authors

This SFMon service was originally developed by Deep Suthar and myself.

## Terraform Structure

The terraform files are found in `sre/deployments/terraform`.

The core infrastructure to deploy is found in the `ecs-cluster`, `ecs-exec-command-policy`, `prometheus-service`, and `sfmon-service` folders. Each of these folders contains an `application` sub-folder with templates for reusable modules. Each of these folders contains an `env` sub-folder with examples for environment specific files that import the reusable modules. You should update these for your environment and add your own backend configuration with your Terraform state file. You should run terraform commands in the `env` sub-folders after you update these for your accounts.

The `docker-login` folder can be used to login to the Elastic Container Registry (ECR) so you can publish Docker images to it. The `ecs-service` folder contains reusable modules which is used to create the sfmon service. The `tags` folder contains reusable modules with the base tags for all assets.

## SFMon ECS Service

The ECS service depends on a Docker container image published to the ECR. This container image contains the required Python and Salesforce dependencies such as the Salesforce CLI. The container image runs a Python script when launched which connects to the desired Salesforce org and collects the required metrics for monitoring.

The Python script looks for environment variables named `PRODUCTION_AUTH_URL` and `FULLQA_AUTH_URL` containing the Force Auth URLS for your production org and Full QA/UAT org. I recommend creating a new Monitoring user profile in your Salesforce org solely for the purpose of this service. The Auth URLs are added to the Docker containers as a Docker build arguments, but you could update this if you want to store this Auth URL in an AWS Secrets Manager. 

You must deploy the following infrastructure to use SFMon:
1. Monitoring ECS Cluster (or use a pre-existing ECS cluster if you'd like)
1. SFMon ECR
1. SFMon ECS Service
1. Prometheus ECS Service (or use a pre-existing Prometheus ECS if you'd like )
1. ECS Exec Command policy

After all of the infrastructure is created in AWS, you can then create a Grafana dashboard which uses your Prometheus data source.

## Prometheus ECS Service

An example Prometheus ECS service is provided.

The configuration for Prometheus is defined in a YAML file maintained in `configs\dev-prometheus-us-west-2\prometheus.yml`. This Prometheus service uses file-based service discovery to scrape Prometheus targets within the ECS cluster using the [Prometheus ECS Discovery](https://github.com/teralytics/prometheus-ecs-discovery) docker image. The Prometheus ECS Discovery container is configured to discover ECS instances in the `monitoring` ECS cluster which can be created from this repo.
