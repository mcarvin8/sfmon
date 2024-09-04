module "tags" {
  source = "../../../tags"

  environment_runtime = var.environment_name
  owner               = var.tag_owner
  repo                = var.terraform_repo
}

