variable "environment_name" {
  type = string
}

variable "sre_owner_email" {
  type        = string
  description = "Email for technical contact."
}

variable "repo_name" {
  type        = string
  description = "The name of the repository where this Terraform is kept, in group/project format"
}
