locals {
  application_context = "monitoring"
  aws_account         = "443899120762"
  aws_region          = "us-west-2"
  environment_name    = "dev"
  sre_owner_email     = "tbd@domain.com"
  subnet_ids_ecs      = [ "subnet-3a002e73", "subnet-26415641" ]
  subnet_ids_load_bal = [ "subnet-3a002e73", "subnet-26415641" ]
  vpc_id              = "vpc-baed17dc"
}

provider "aws" {
  region = local.aws_region
}

module "ecs_service" {
  source = "../../../../application/service"

  application_context          = local.application_context
  aws_account                  = local.aws_account
  aws_region                   = local.aws_region
  config_bucket_name           = "${local.application_context}-${local.environment_name}-prometheus-${local.aws_region}-config"
  config_file_name             = "prometheus.yml"
  config_source_dir            = "../../../../../../../../configs/${local.environment_name}-prometheus-${local.aws_region}"
  docker_image_url_aws_cli_v2  = "amazon/aws-cli:2.2.8"
  docker_image_url_ecs_disc    = "tkgregory/prometheus-ecs-discovery:latest"
  docker_image_url_prometheus  = "prom/prometheus:v2.25.2"
  docker_image_url_prom_pushgw = "prom/pushgateway:v1.4.0"
  ecs_cluster_name_prometheus  = "monitoring"
  ecs_cluster_name_targets     = "monitoring"
  ecs_container_subnet_ids     = local.subnet_ids_ecs
  environment_name             = local.environment_name
  load_balancer_ingress        = ["10.0.0.0/8", "139.180.242.33/32", "139.180.242.64/32", "168.149.241.177/32"]
  load_balancer_subnet_ids     = local.subnet_ids_load_bal
  tag_contact                  = local.sre_owner_email
  tag_owner                    = local.sre_owner_email
  task_count                   = 1
  task_cpu_size                = 2048
  task_memory_size             = 8192
  terraform_repo               = "mcarvin8/sfmon"
  vpc_id                       = local.vpc_id
}
