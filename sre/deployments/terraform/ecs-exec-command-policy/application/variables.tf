variable "application_context" {
  type        = string
  description = "The name of the organization this belongs to"
  default     = "finance"
}

variable "aws_region" {
  type        = string
  description = "The AWS region that assets will be created in"
}

variable "sre_owner_email" {
  type = string
}

variable "repo_name" {
  type        = string
  description = "The name of the repository where this Terraform is kept, in group/project format"
}

variable "environment_name" {
  type        = string
}
