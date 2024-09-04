provider "aws" {
  region = "us-west-2"
}

# The ECS exec-command policy.
module "ecs-exec-command-policy" {
  source = "../../../../application"

  application_context = "monitoring"
  aws_region          = "us-west-2"
  sre_owner_email     = "tbd@domain.com"
  repo_name           = "mcarvin8/sfmon"
  environment_name    = "dev"
}
