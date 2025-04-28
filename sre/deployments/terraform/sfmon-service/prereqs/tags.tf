module "tags" {
  source = "../../tags"

  environment_runtime = local.environment_name
  owner               = local.sre_owner_email
  repo                = local.repo_name
}
