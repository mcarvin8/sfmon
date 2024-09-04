variable "docker_image_tag" {
  type        = string
  description = "The Docker image tag to be appended to the image URL"
  default     = "latest"
}

variable "ecs_exec_command_policy_name" {
  type        = string
  description = "The name of the pre-existing IAM policy for enabling ECS exec-command (optional)"
}

variable "ecs_container_subnet_ids" {
  type        = set(string)
  description = "The IDs of the subnets in which to run the ECS containers"
}

variable "container_logDriver" {
  type        = string
  description = "The log driver to use for the container. Use 'auto' for awslogs or specify another log driver."
  default     = "auto"
}

variable "aws_account" {
  type        = string
  description = "The AWS account that assets will be created in"
}

variable "aws_region" {
  type        = string
  description = "The AWS region that assets will be created in"
}

variable "environment_name" {
  type        = string
}

variable "sre_owner_email" {
  type        = string
}

variable "repo_name" {
  type        = string
  description = "The name of the repository where this Terraform is kept, in group/project format"
}

variable "vpc_id" {
  type        = string
  description = "The name of the repository where this Terraform is kept, in group/project format"
}
