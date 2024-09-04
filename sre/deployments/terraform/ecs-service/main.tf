data "aws_region" "current" {}

data "aws_iam_role" "task_role" {
  count = var.task_role != null ? 1 : 0
  name  = var.task_role
}

data "aws_iam_role" "task_execution_role" {
  count = var.task_execution_role != null ? 1 : 0
  name  = var.task_execution_role
}

data "aws_ecs_cluster" "current" {
  cluster_name = var.cluster_name
}

data "aws_lb_target_group" "tg" {
  for_each = local.load_balancers != null ? { for k, v in local.load_balancers : k => v if v.tg_name != null } : {}
  name     = each.value.tg_name
}

# Create Task Definition to use with ECS Service
resource "aws_ecs_task_definition" "this" {

  family                   = local.default_name
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  requires_compatibilities = [var.launchType]
  network_mode             = local.network_mode
  task_role_arn            = var.task_role != null ? data.aws_iam_role.task_role[0].arn : null
  execution_role_arn       = var.task_execution_role != null ? data.aws_iam_role.task_execution_role[0].arn : null

  container_definitions = var.containerDefinition_jsonFile != null ? var.containerDefinition_jsonFile : jsonencode([
    {
      name                  = local.container_name
      image                 = "${var.container_repositoryURL}:${var.container_imageTag}"
      repositoryCredentials = local.container_repositoryCredentials
      cpu                   = var.container_cpu
      memory                = var.container_memoryHardLimit
      memoryReservation     = var.container_memorySoftLimit
      portMappings          = local.container_portMappings
      environment           = local.container_environmentVars
      environmentFiles      = local.container_environmentFiles
      hostname              = local.container_hostname
      dnsSearchDomains      = local.container_seachDomains
      dnsServers            = local.container_dnsServers
      extraHosts            = local.container_extraHosts
      logConfiguration      = local.container_logConfig
      essential             = true
    }
  ])

  tags = merge(
    { Name = local.default_name },
    local.default_tags
  )
}

# Create ECS Service
resource "aws_ecs_service" "this" {
  name                               = local.default_name
  cluster                            = data.aws_ecs_cluster.current.arn
  task_definition                    = aws_ecs_task_definition.this.arn
  launch_type                        = var.launchType
  desired_count                      = var.desired_count
  deployment_minimum_healthy_percent = var.minimum_healthy_percent
  deployment_maximum_percent         = var.maximum_percent
  scheduling_strategy                = local.is_fargate ? "REPLICA" : var.scheduling_strategy
  wait_for_steady_state              = var.wait_for_steady_state
  force_new_deployment               = var.force_new_deployment

  dynamic "network_configuration" {
    for_each = var.network_config != null ? ["1"] : []

    content {
      subnets          = var.network_config.subnet_ids
      security_groups  = var.network_config.security_group_ids
      assign_public_ip = var.assign_public_ip
    }
  }

  dynamic "load_balancer" {
    for_each = local.load_balancers != null ? local.load_balancers : {}

    content {
      elb_name         = load_balancer.value["tg_name"] == null ? load_balancer.value["elb_name"] : null
      target_group_arn = load_balancer.value["tg_name"] != null ? data.aws_lb_target_group.tg[load_balancer.key].arn : null
      container_name   = load_balancer.value["container_name"]
      container_port   = load_balancer.value["container_port"]
    }
  }

  dynamic "capacity_provider_strategy" {
    for_each = local.capacity_provider_strategy != null ? local.capacity_provider_strategy : {}

    content {
      capacity_provider = capacity_provider_strategy.value["provider_name"]
      weight            = capacity_provider_strategy.value["weight"]
      base              = capacity_provider_strategy.value["base"]
    }
  }

  dynamic "deployment_circuit_breaker" {
    for_each = var.rollback_on_failure ? ["1"] : []

    content {
      enable   = true
      rollback = true
    }
  }

  dynamic "ordered_placement_strategy" {
    for_each = local.placement_strategy != null ? local.placement_strategy : {}

    content {
      type  = ordered_placement_strategy.value["type"]
      field = ordered_placement_strategy.value["field"]
    }
  }

  tags = merge(
    { Name = local.default_name },
    local.default_tags
  )
}

module "tags" {
  source = "../tags"

  environment_runtime = var.environment_runtime
  repo                = var.repo
  owner               = var.owner == null ? "" : var.owner
}
