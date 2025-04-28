variable "application_context" {
  type = string
}

variable "environment_name" {
  type = string
}

variable "tag_contact" {
  type        = string
  description = "Used for the contact tags"
}

variable "tag_owner" {
  type        = string
  description = "Used for the owner tags"
}

variable "terraform_repo" {
  type        = string
  description = "The name of the repository where this Terraform is kept, in group/project format"
}
