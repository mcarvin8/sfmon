module "tags" {
  source = "git::https://scm.platform.avalara.io/sre-public/tf-core-modules//aws/tags?ref=v4.30.3"

  environment_runtime = var.environment_name
  owner               = local.tag_owner
  contact             = local.tag_contact
  project             = local.tag_project
  repo                = local.terraform_repo
}
