provider "aws" {
  region = var.aws_region
}

module "service" {
  source                        = "../../ecs-service"
  name                          = local.service_name
  cluster_name                  = local.cluster_name
  desired_count                 = 1
  launchType                    = "FARGATE"
  container_name                = local.service_name
  container_imageTag            = var.docker_image_tag
  container_repositoryURL       = "${aws_ecr_repository.sfmon.repository_url}"
  task_cpu                      = 256
  task_memory                   = 1024
  task_execution_role           = aws_iam_role.this.name
  container_portMappings        = [{ containerPort = 9001, hostPort = 0, Protocol = "tcp" }]
  containerDefinition_jsonFile  = templatefile("${path.module}/container-definitions.json", {
                                                  service_name      = local.service_name,
                                                  aws_account       = var.aws_account,
                                                  aws_region        = var.aws_region,
                                                  docker_image_tag  = var.docker_image_tag
                                                })
  container_logDriver           = var.container_logDriver

  network_config = {
    security_group_ids = [aws_security_group.sfmon_service_sg.id]
    subnet_ids         = var.ecs_container_subnet_ids
  }

  project             = local.application_context
  contact             = var.sre_owner_email
  environment_runtime = var.environment_name
  repo                = var.repo_name
}
