module "defaults" {
  source = "../../defaults/env/us-west-2/prd"
}

locals {
  tag_contact    = module.defaults.sre_owner_email
  tag_owner      = module.defaults.sre_owner_email
  tag_project    = module.defaults.application_context
  terraform_repo = module.defaults.repo_name
}
