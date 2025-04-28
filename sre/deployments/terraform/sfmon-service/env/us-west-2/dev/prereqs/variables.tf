variable "docker_image_tag" {
  type        = string
  description = "The Docker image tag to be appended to the image URL"
}

variable "ecs_exec_command_policy_name" {
  type        = string
  description = "The name of the pre-existing IAM policy for enabling ECS exec-command (optional)"
  default     = "finance-ecs-exec-command-policy"
}

variable "container_logDriver" {
  type        = string
  description = "The log driver to use for the container. Use 'auto' for awslogs or specify another log driver."
  default     = "auto"
}
