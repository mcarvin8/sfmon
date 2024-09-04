# Common variables
variable "name" {
  description = "Required: Name for your Service and Task Definition."
  type        = string
}

variable "name_prefix" {
  description = "Optional: Prefix for the Name, such as `<env>-<name>`. If not given, module will use default prefix."
  type        = string
  default     = null
}

# Task specific variables
variable "launchType" {
  description = "Required: Launch type for the task. `EC2` or `FARGATE`"
  type        = string
}

variable "task_role" {
  description = "Optional: Name of IAM role used by containers to make API requests to authorized AWS services"
  type        = string
  default     = null
}

variable "task_execution_role" {
  description = "Optional: Name of IAM role used by tasks to pull container images and publish logs to CloudWatch. Required if using `container_environmentFiles` or `container_repositoryCredentials`"
  type        = string
  default     = null
}

variable "network_mode" {
  description = "Optional: Docker networking mode to use for the containers. `none`, `bridge`, `awsvpc`, or `host`. Replaced to `awsvpc` if `launchType` is `FARGATE`" # https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#network_mode
  type        = string
  default     = null
}

variable "task_cpu" {
  description = "Optional: Number of CPU Units for the TASK. Required if variable `launchType` is `FARGATE`"
  type        = number
  default     = null
}

variable "task_memory" {
  description = "Optional: Limit(in MB) of memory for the TASK. Required if variable `launchType` is `FARGATE`"
  type        = number
  default     = null
}

# Container specific variables
variable "container_name" {
  description = "Optional: Name for the container definition. If null, name of Task Definition will be used. NOTE: This is not the container 'hostname'"
  type        = string
  default     = null
}

# Set to null if using `containerDefinition_jsonFile`
variable "container_repositoryURL" {
  description = "Required: URL of the docker image registry"
  type        = string
}

variable "container_imageTag" {
  description = "Optional: Image tag"
  type        = string
  default     = "latest"
}

# Secret Manager should hold two key:value pairs for `username` and `password` respectively.
# Follow AWS guide https://docs.aws.amazon.com/AmazonECS/latest/developerguide/private-auth.html#private-auth-enable
variable "container_repositoryCredentials" {
  description = "Required if image registry requires authentication. Name of the Secrete Manager."
  type        = string
  default     = null
}

variable "container_cpu" {
  description = "Optional: Number of CPU Units for the container."
  type        = number
  default     = null
}

variable "container_memoryHardLimit" {
  description = "Optional: Hard Limit(in MB) of memory for the container. Referred as `memory` in Container Definition JSON"
  type        = number
  default     = null
}

variable "container_memorySoftLimit" {
  description = "Optional: Soft Limit(in MB) of memory for the container. Referred as `memoryReservation` in Container Definition JSON"
  type        = number
  default     = null
}

# Set to null if using `containerDefinition_jsonFile`
variable "container_portMappings" {
  description = "Required: List of Container to host port mapping. `hostPort` will be replaced with value of `containerPort` if `network_mode` is `awsvpc` or `launchType` is `FARGATE`" # https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_PortMapping.html#API_PortMapping_Contents
  type = list(object({
    containerPort = number
    hostPort      = number
    Protocol      = string
  }))
}

variable "container_environmentVars" {
  description = "Optional: Environment variables within the container."
  type        = map(string)
  default     = null
}

variable "container_environmentFiles" {
  description = "Optional: Environment variable file from the S3 bucket. Requires variable `task_execution_role`"
  type        = list(string)
  default     = null
}

variable "container_hostname" {
  description = "Optional: Hostname to set for the container. Ignored if `network_mode` is `awsvpc` or `launchType` is `FARGATE`"
  type        = string
  default     = null
}

variable "container_seachDomains" {
  description = "Optional: List of search domains within container. Ignored if `network_mode` is `awsvpc` or `launchType` is `FARGATE`"
  type        = list(string)
  default     = null
}

variable "container_dnsServers" {
  description = "Optional: List of DNS Servers within container. Ignored if `network_mode` is `awsvpc` or `launchType` is `FARGATE`"
  type        = list(string)
  default     = null
}

variable "container_extraHosts" {
  description = "Optional: Map of Local DNS names. This will go into `/etc/hosts` file within container. Ignored if `network_mode` is `awsvpc` or `launchType` is `FARGATE`"
  type        = map(string)
  default     = null
}

variable "container_logDriver" {
  description = "Optional: Set this to `auto` for auto select or use values from the available list." # https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_LogConfiguration.html#API_LogConfiguration_Contents
  type        = string
  default     = null
}

variable "container_logOptions" {
  description = "Required if `log_driver` is other than `auto` or `null`. Optional if `log_driver` set to `auto`. Not required / ignored if `log_driver` is set to `null`"
  type        = map(string)
  default     = null
}

/*
----------------------- WARNING! -----------------------
- This variable should only be used in case you want some advanced container configurations, which does not collectively cover with all above `container_*` variables
- This variable takes a valid container definitions in a JSON format and overwrites / ignores all above `container_*` variables
- Refer to AWS docs to write valid JSON - https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#container_definitions
- Refer the example for how to use this variable
- if using this, set `container_repositoryURL` and `container_portMappings` with any dummy values
*/
variable "containerDefinition_jsonFile" {
  description = "Optional: Valid JSON file with container definitions."
  type        = string
  default     = null
}

# Service Specific variables
variable "cluster_name" {
  description = "Required: Name of the ECS cluster"
  type        = string
}

variable "desired_count" {
  description = "Required: Number of instances of the task definition to place and keep running"
  type        = number
}

variable "minimum_healthy_percent" {
  description = "Optional: Lower limit (In Percent of desired_count) Must be <100. Deployment strategy that decides number of existing tasks can be terminated during deployment"
  type        = number
  default     = 100
}

variable "maximum_percent" {
  description = "Optional: Upper limit (In Percent of desired_count) Must be >100. Deployment strategy that decides number of new tasks can be placed during deployment"
  type        = number
  default     = 200
}

# Only Valid/Required, if `network_mode` is `awsvpc` or `launchType` is `FARGATE`
variable "network_config" {
  description = "Optional: VPC configuration with exact fields as shown below. Required if `network_mode` is `awsvpc` or `launchType` is `FARGATE`"
  type = object({
    security_group_ids = list(string)
    subnet_ids         = list(string)
  })
  default = null
}

variable "assign_public_ip" {
  description = "Optional: Assign a public IP address to the ENI (FARGATE launch type only)"
  type        = bool
  default     = false
}

/*
************* INFO: Few considerations while using load_balancer configuration! *************
- Only one of the parameter `elb_name` or `tg_name` is required, set other to `null`. `tg_name` will be preferred if both is provided.
- Target group must be already associated with the load balancer
- Target group must be of type IP, if `network_mode` is `awsvpc` or `launchType` is `FARGATE`
- Target group must be of type INSTANCE, if `network_mode` is NOT `awsvpc` or `launchType` is `EC2`
- Network Configuration `network_config` must be provided when `network_mode` is `awsvpc` or `launchType` is `FARGATE`
- Classic ELB - Not supported with FARGATE
- Classic ELB - Exact host to container port mapping is required.
- Classic ELB - Listeners must be already configured
*/
variable "load_balancers" {
  description = "Optional: List of load balancer configuration"
  type = list(object({
    elb_name       = string // Required: Name for the Classic Load Balancer
    tg_name        = string // Required: Name of the Target Group
    container_name = string // Required: Name of the container specified in Task Definition
    container_port = number // Required: Port on the container to associate with the load balancer
  }))
  default = null
}

# NOTE: Only one capacity provider in a capacity provider strategy can have a base defined. Set others to `null`
variable "capacity_provider_strategy" {
  description = "Optional: Capacity provider strategy to use for the service"
  type = list(object({
    provider_name = string // Required: Short name of the capacity provider
    weight        = number // Required: Relative percentage of the total number of launched tasks that should use the specified capacity provider
    base          = number // Optional: Number of tasks, at a minimum, to run on the specified capacity provider
  }))
  default = null
}

# NOTE: Only valid if launchType` is `EC2`. ignored otherwise
variable "scheduling_strategy" {
  description = "Optional: Scheduling strategy to use for the service. `REPLICA` or `DAEMON`"
  type        = string
  default     = "REPLICA"
}

# NOTE: Only valid if launchType` is `EC2`. ignored otherwise
# The maximum number of placement_strategy blocks is "5". Anything after that will be ignored
variable "placement_strategy" {
  description = "Optional: Service level strategy rules that are taken into consideration during task placement. List from top to bottom in order of precedence"
  type = list(object({
    order_no = number // Required: Order number in the list
    type     = string // Required: Type of placement strategy. Must be one of: binpack, random, or spread
    field    = string // Optional: For the spread strategy, valid values are instanceId, For the binpack type, valid values are memory and cpu, For the random type, this attribute is not needed
  }))
  default = null
}

variable "wait_for_steady_state" {
  description = "Optional: If true, Terraform will wait for the service to reach a steady state"
  type        = bool
  default     = false
}

variable "rollback_on_failure" {
  description = "Optional: Whether to enable Amazon ECS to roll back the service if a service deployment fails"
  type        = bool
  default     = false
}

variable "force_new_deployment" {
  description = "Optional: Trigger a new deployment with no service definition changes. exp. Newer Docker image with the same image/tag combination"
  type        = bool
  default     = false
}

# Tagging variables
variable "project" {
  description = "Required: project tag"
  type        = string
}

variable "environment_runtime" {
  description = "Required: environment-runtime tag"
  type        = string
}

variable "repo" {
  description = "Required: repo tag"
  type        = string
}

variable "contact" {
  description = "Required: contact tag"
  type        = string
}

variable "owner" {
  description = "Optional: owner tag"
  default     = null
}
