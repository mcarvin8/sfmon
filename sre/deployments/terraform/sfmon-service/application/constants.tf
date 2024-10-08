locals {
  service_name                      = "sfmon-service"
  cluster_name                      = "monitoring"
  ecr_name                          = local.service_name
  cloudwatch_name                   = "/ecs/${local.service_name}"
  application_context               = "monitoring"
}
