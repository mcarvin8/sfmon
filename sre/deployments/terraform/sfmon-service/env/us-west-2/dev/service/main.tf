locals {
  environment_name                  = "dev"
  aws_account                       = "443899120762"
  aws_region                        = "us-west-2"
  sre_owner_email                   = "tbd@domain.com"
  repo_name                         = "mcarvin8/sfmon"
  subnet_ids_ecs                    = [ "subnet-3a002e73", "subnet-26415641" ]
  vpc_id                            = "vpc-baed17dc"
}

provider "aws" {
  region = local.aws_region
}

module "ecs_service" {
  source = "../../../../application"

  aws_account                  = local.aws_account
  environment_name             = local.environment_name
  aws_region                   = local.aws_region
  docker_image_tag             = var.docker_image_tag
  ecs_container_subnet_ids     = local.subnet_ids_ecs
  ecs_exec_command_policy_name = "monitoring-ecs-exec-command-policy"
  sre_owner_email              = local.sre_owner_email
  repo_name                    = local.repo_name
  vpc_id                       = local.vpc_id
}
