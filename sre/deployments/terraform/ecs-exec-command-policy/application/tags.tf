module "tags" {
  source = "../../tags"

  environment_runtime = var.environment_name
  owner               = var.sre_owner_email
  repo                = var.repo_name
}
