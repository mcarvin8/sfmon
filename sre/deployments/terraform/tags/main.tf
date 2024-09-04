terraform {
  required_version = ">= 0.13"
}

locals {
  common_tags = merge(
    {
      "owner"               = var.owner,
      "environment-runtime" = var.environment_runtime,
      "managed-by"          = "terraform",
      "repo"                = var.repo
    }
  )
}
