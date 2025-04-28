variable "docker_image_tag" {
  type        = string
  description = "The Docker image tag to be appended to the image URL"
}

variable "container_logDriver" {
  type        = string
  description = "The log driver to use for the container. Use 'auto' for awslogs or specify another log driver."
  default     = "auto"
}
