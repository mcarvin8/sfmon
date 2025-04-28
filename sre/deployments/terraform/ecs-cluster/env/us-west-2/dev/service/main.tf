locals {
  application_context = "ips"
  aws_region          = "us-west-2"
  environment_name    = "dev"
  sre_owner_email     = "dg-saasoperations@avalara.com"
}

provider "aws" {
  region = local.aws_region
}

module "cluster" {
  source = "../../../../application"

  application_context = local.application_context
  environment_name    = local.environment_name
  tag_contact         = local.sre_owner_email
  tag_owner           = local.sre_owner_email
  terraform_repo      = "ips/monitoring"
}
