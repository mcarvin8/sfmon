locals {
  service_name                      = "sfmon-service"
  application_context               = "finance"
  environment_name                  = "dev" # update based on your AWS environment
  ecr_name                          = local.service_name
  aws_account                       = "443899120762" # update to your AWS account
  cloudwatch_name                   = "/ecs/${local.service_name}"
  aws_region                        = "us-west-2"
  sre_owner_email                   = "tbd@domain.com" # update with tag email
  repo_name                         = "sfmon-repo" # update with repo
  vpc_id                            = "vpc-baed17dc"
}
