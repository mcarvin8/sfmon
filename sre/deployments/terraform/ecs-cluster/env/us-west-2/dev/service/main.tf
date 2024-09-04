locals {
  aws_region          = "us-west-2"
  environment_name    = "dev"
  sre_owner_email     = "tbd@domain.com"
}

provider "aws" {
  region = local.aws_region
}

module "cluster" {
  source = "../../../../application"

  environment_name    = local.environment_name
  sre_owner_email     = local.sre_owner_email
  repo_name           = "mcarvin8/sfmon"
}
