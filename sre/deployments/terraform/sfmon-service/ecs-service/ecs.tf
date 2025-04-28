provider "aws" {
  region = "us-west-2"
}

data "aws_security_group" "sfmon_service_sg" {
  name = "${local.environment_name}-${local.application_context}-${local.service_name}-container-sg"
}

module "service" {
  source                        = "../../ecs-service"
  name                          = local.service_name
  cluster_name                  = local.cluster_name
  desired_count                 = 1
  launchType                    = "FARGATE"
  container_name                = local.service_name
  container_imageTag            = var.docker_image_tag
  container_repositoryURL       = "${aws_account}.dkr.ecr.${aws_region}.amazonaws.com/${service_name}"
  task_cpu                      = 2048
  task_memory                   = 8192
  task_execution_role           = aws_iam_role.this.name
  container_portMappings        = [{ containerPort = 9001, hostPort = 0, Protocol = "tcp" }]
  containerDefinition_jsonFile  = templatefile("${path.module}/container-definitions.json", {
                                                  service_name      = local.service_name,
                                                  aws_account       = local.aws_account,
                                                  aws_region        = local.aws_region,
                                                  docker_image_tag  = var.docker_image_tag
                                                })
  container_logDriver           = var.container_logDriver

  network_config = {
    security_group_ids = [data.aws_security_group.sfmon_service_sg.id]
    subnet_ids         = local.subnet_ids_ecs
  }

  project             = local.application_context
  contact             = local.sre_owner_email
  environment_runtime = local.environment_name
  repo                = local.repo_name
}
