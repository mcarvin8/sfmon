locals {
  service_name                      = "sfmon-service"
  application_context               = "finance"
  environment_name                  = "dev" # update based on your AWS environment
  cluster_name                      = "${local.environment_name}-${local.application_context}-cluster" # update with target ecs-cluster
  aws_account                       = "443899120762" # update to your AWS account
  aws_region                        = "us-west-2"
  sre_owner_email                   = "tbd@domain.com" # update with tag email
  repo_name                         = "sfmon-repo" # update with repo
  subnet_ids_ecs                    = [ "subnet-3a002e73", "subnet-26415641" ]
}
