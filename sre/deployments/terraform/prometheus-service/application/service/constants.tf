locals {
  service_name      = "${var.environment_name}-${var.application_context}-prometheus-service"

  aws_s3_sync_cmd                   = "aws s3 sync --exact-timestamps s3://${var.config_bucket_name} ."
  container_name_config_init        = "config-init"
  container_name_config_reloader    = "config-reloader"
  container_name_ecs_discovery      = "ecs-discovery"
  container_name_prometheus         = "prometheus"
  container_name_prom_pushgw        = "prometheus-pushgateway"
  container_port_none               = -1
  container_port_prometheus         = 9090
  container_port_prom_pushgw        = 9091
  container_security_group_name     = "${local.service_name}-container-sg"
  cloudwatch_name                   = "/ecs/${local.service_name}"
  ecs_exec_command_policy_name      = "${local.service_name}-exec-command"
  ecs_secrets_policy_name           = "${local.service_name}-secrets"
  ecs_task_execution_role_name      = "${local.service_name}-task-exec"
  ecs_task_iam_role_name            = "${local.service_name}-task"
  load_balancer_name                = local.service_name
  load_balancer_port_prometheus     = 9090
  load_balancer_security_group_name = "${local.service_name}-alb-sg"
  log_group_name_config_init        = "/ecs/${local.resource_name_config_init}"
  log_group_name_config_reloader    = "/ecs/${local.resource_name_config_reloader}"
  log_group_name_ecs_discovery      = "/ecs/${local.resource_name_ecs_discovery}"
  log_group_name_prometheus         = "/ecs/${local.resource_name_prometheus}"
  log_group_name_prometheus_pushgw  = "/ecs/${local.resource_name_prom_pushgw}"
  resource_name_base                = "${var.environment_name}-${var.application_context}"
  resource_name_config_init         = "${local.resource_name_base}-prometh-config-init"
  resource_name_config_reloader     = "${local.resource_name_base}-prometh-config-reload"
  resource_name_ecs_discovery       = "${local.resource_name_base}-prometh-ecs-discovery"
  resource_name_prometheus          = "${local.resource_name_base}-prometheus"
  resource_name_prom_pushgw         = "${local.resource_name_base}-prometh-pushgw"
  shared_volume_name                = "shared"
  target_group_name_prometheus      = "${local.resource_name_prometheus}-tg"
  target_group_name_prom_pushgw     = "${local.resource_name_prom_pushgw}-tg"

  container_values = {
    config_init = {
      container_name = local.container_name_config_init
      resource_name = local.resource_name_config_init
      container_port = local.container_port_none
      log_group_name = local.log_group_name_config_init
      docker_image = var.docker_image_url_aws_cli_v2
    }
    config_reloader = {
      container_name = local.container_name_config_reloader
      resource_name = local.resource_name_config_reloader
      container_port = local.container_port_none
      log_group_name = local.log_group_name_config_reloader
      docker_image = var.docker_image_url_aws_cli_v2
    }
    prometheus = {
      container_name = local.container_name_prometheus
      resource_name = local.resource_name_prometheus
      container_port = local.container_port_prometheus
      log_group_name = local.log_group_name_prometheus
      docker_image = var.docker_image_url_prometheus
    }
    prometheus_pushgateway = {
      container_name = local.container_name_prom_pushgw
      resource_name = local.resource_name_prom_pushgw
      container_port = local.container_port_prom_pushgw
      log_group_name = local.log_group_name_prometheus_pushgw
      docker_image = var.docker_image_url_prom_pushgw
    }
    teralytics_ecs_discovery = {
      container_name = local.container_name_ecs_discovery
      resource_name = local.resource_name_ecs_discovery
      container_port = local.container_port_none
      log_group_name = local.log_group_name_ecs_discovery
      docker_image = var.docker_image_url_ecs_disc
    }
  }
}
