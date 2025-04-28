variable "application_context" {
  type = string
}

variable "aws_account" {
  type = string
}

variable "aws_region" {
  type        = string
  description = "AWS deployment region"
}

variable "config_bucket_name" {
  type = string
}

variable "config_file_name" {
  type = string
  description = "The name of the primary Prometheus configuration file"
}

variable "config_source_dir" {
  type        = string
  description = "The relative location of the configuration source directory"
}

variable "config_sync_seconds" {
  type    = number
  default = 60
}

variable "docker_image_url_aws_cli_v2" {
  type        = string
  description = "The AWS CLI V2 Docker image URL"
}

variable "docker_image_url_ecs_disc" {
  type        = string
  description = "The Teralytics ECS Discovery Docker image URL"
}

variable "docker_image_url_prometheus" {
  type        = string
  description = "The Prometheus Docker image URL"
}

variable "docker_image_url_prom_pushgw" {
  type        = string
  description = "The Prometheus Push Gateway Docker image URL"
}

variable "ecs_cluster_name_prometheus" {
  type        = string
  description = "The name of the ECS cluster to use to launch the Prometheus service"
}

variable "ecs_cluster_name_targets" {
  type        = string
  description = "The name of the ECS cluster to search for scrape targets (used by ECS Discovery)"
}

variable "ecs_container_subnet_ids" {
  type        = set(string)
  description = "The IDs of the subnets in which to run the ECS containers"
}

variable "environment_name" {
  type = string
}

variable "load_balancer_ingress" {
  type        = set(string)
  description = "The set of CIDRs or IPs to allow inbound HTTP/HTTPS traffic from"
}

variable "load_balancer_subnet_ids" {
  type        = set(string)
  description = "The IDs of the subnets in which to run the load balancer"
}

variable "secret_arns" {
  type        = set(string)
  description = "The ARNs of any secrets that Prometheus will need access to at runtime (default: none)"
  default     = []
}

variable "tag_contact" {
  type        = string
  description = "Used for the technical contact tags"
}

variable "tag_owner" {
  type        = string
  description = "Used for the owner tags"
}

variable "task_count" {
  type        = number
  description = "The number of desired running tasks."
  validation {
    condition     = var.task_count == 0 || var.task_count == 1
    error_message = "The task_count must be 0 or 1."
  }
}

variable "task_cpu_size" {
  type        = number
  description = "The number of CPU units (vCPUs x 1024) allotted to the ECS tasks. See AWS documentation for valid values."
}

variable "task_memory_size" {
  type        = number
  description = "The amount of memory in MB allotted to the ECS tasks. See AWS documentation for valid values."
}

variable "terraform_repo" {
  type        = string
  description = "The name of the repository where this Terraform is kept, in group/project format"
}

variable "vpc_id" {
  type = string
}
