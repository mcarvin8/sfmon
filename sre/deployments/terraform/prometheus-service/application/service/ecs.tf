# Look up the ECS cluster.
data "aws_ecs_cluster" "monitoring" {
  cluster_name = var.ecs_cluster_name_prometheus
}

# The ECS task definition for all containers.
resource "aws_ecs_task_definition" "this" {
  family                   = local.service_name
  requires_compatibilities = [ "FARGATE" ]
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu_size
  memory                   = var.task_memory_size
  task_role_arn            = aws_iam_role.prometheus_service_task.arn

  # This volume is shared by the Prometheus and Prometheus Agent containers.
  volume {
    name = local.shared_volume_name
    efs_volume_configuration {
      file_system_id = aws_efs_file_system.prometheus.id
    }
  }

  # Keep the old task definition in case the pipeline fails.
  lifecycle {
    create_before_destroy = true
  }

  container_definitions = jsonencode(local.container_definitions)

  tags = merge(
    module.tags.tags,
    { Name = local.service_name }
  )
}

# The ECS service definition
resource "aws_ecs_service" "this" {
  name                   = local.service_name
  cluster                = data.aws_ecs_cluster.monitoring.id
  task_definition        = aws_ecs_task_definition.this.arn
  desired_count          = var.task_count
  launch_type            = "FARGATE"
  enable_execute_command = true
  wait_for_steady_state  = true
  propagate_tags         = "SERVICE"

  # Note: ECS Fargate supports a maximum of 5 load_balancer blocks.

  # Load balancer to access Prometheus's endpoint.
  load_balancer {
    target_group_arn = aws_lb_target_group.prometheus.arn
    container_name   = local.container_values.prometheus.container_name
    container_port   = local.container_values.prometheus.container_port
  }

  # Load balancer to access the Push Gateway's endpoint.
  load_balancer {
    target_group_arn = aws_lb_target_group.prometheus_pushgateway.arn
    container_name   = local.container_values.prometheus_pushgateway.container_name
    container_port   = local.container_values.prometheus_pushgateway.container_port
  }

  network_configuration {
    subnets = var.ecs_container_subnet_ids
    security_groups = [ aws_security_group.container.id ]
  }

  tags = merge(
    module.tags.tags,
    { Name = local.service_name }
  )
}

resource "aws_efs_file_system" "prometheus" {
  encrypted       = true
  throughput_mode = "elastic" # Required for archive support

  lifecycle_policy {
    transition_to_ia      = "AFTER_30_DAYS"
  }

  tags = merge(
    module.tags.tags,
    { Name = "${local.service_name}-efs" }
  )
}

resource "aws_efs_mount_target" "prometheus" {
  for_each = toset(var.ecs_container_subnet_ids)

  file_system_id  = aws_efs_file_system.prometheus.id
  subnet_id       = each.value
  security_groups = [aws_security_group.container.id]
}
