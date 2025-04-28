module "defaults" {
  source = "../../../../../defaults/env/us-west-2/prd"
}

provider "aws" {
  region = module.defaults.aws_region
}

# The ECS exec-command policy.
module "ecs-exec-command-policy" {
  source = "../../../../application"

  application_context = module.defaults.application_context
  aws_region          = module.defaults.aws_region
  environment_name    = module.defaults.environment_name
  sre_owner_email     = module.defaults.sre_owner_email
  terraform_repo      = module.defaults.repo_name
}
