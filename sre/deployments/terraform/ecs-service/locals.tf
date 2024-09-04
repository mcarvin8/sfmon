locals {

  # -------- Default name for the resources -------- #
  default_name = var.name_prefix != null ? "${var.name_prefix}-${var.name}" : "${var.environment_runtime}-${var.project}-${var.name}"
  is_fargate   = var.launchType == "FARGATE" ? true : false
  is_awsvpc    = local.network_mode == "awsvpc" ? true : false

  # -------- Refactor variables conditionally -------- #
  network_mode               = local.is_fargate ? "awsvpc" : var.network_mode
  placement_strategy         = var.placement_strategy != null ? { for k, v in var.placement_strategy : v.order_no => v if v.order_no < 6 } : null
  load_balancers             = var.load_balancers != null ? { for v in var.load_balancers : "${v.container_name}_${v.container_port}" => v } : null
  capacity_provider_strategy = var.capacity_provider_strategy != null ? { for v in var.capacity_provider_strategy : v.provider_name => v } : null

  # -------- Validate and refactor container definitions -------- #
  container_name                  = var.container_name != null ? var.container_name : local.default_name
  container_repositoryCredentials = var.container_repositoryCredentials != null ? { "credentialsParameter" = data.aws_secretsmanager_secret.secret[0].arn } : null
  container_portMappings          = var.container_portMappings != null ? [for v in var.container_portMappings : { containerPort : v.containerPort, Protocol : v.Protocol, hostPort : local.is_fargate ? v.containerPort : v.hostPort }] : null
  container_logOptions            = var.container_logOptions == null && var.container_logDriver == "auto" ? { "awslogs-create-group" = true, "awslogs-group" = "/ecs/${local.container_name}", "awslogs-region" = data.aws_region.current.name, "awslogs-stream-prefix" = "ecs" } : var.container_logDriver == null ? null : var.container_logOptions
  container_logConfig             = var.container_logDriver != null ? { logDriver : var.container_logDriver == "auto" ? "awslogs" : var.container_logDriver, options : local.container_logOptions } : null
  container_environmentVars       = var.container_environmentVars != null ? [for k, v in var.container_environmentVars : { name : k, value : v }] : null
  container_environmentFiles      = var.container_environmentFiles != null ? [for k, v in var.container_environmentFiles : { type : "s3", value : v }] : null
  container_extraHosts            = var.container_extraHosts != null ? local.is_awsvpc ? null : [for k, v in var.container_extraHosts : { hostname : k, ipAddress : v }] : null
  container_hostname              = local.is_awsvpc ? null : var.container_hostname
  container_dnsServers            = local.is_awsvpc ? null : var.container_dnsServers
  container_seachDomains          = local.is_awsvpc ? null : var.container_seachDomains

  # -------- Populate dynamic set of default tags -------- #
  default_tags = merge(
    module.tags.tags
  )
}

data "aws_secretsmanager_secret" "secret" {
  count = var.container_repositoryCredentials != null ? 1 : 0
  name  = var.container_repositoryCredentials
}
