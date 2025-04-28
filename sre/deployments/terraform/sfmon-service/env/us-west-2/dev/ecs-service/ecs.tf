provider "aws" {
  region = "us-west-2"
}

module "service" {
  source                        = "git::https://scm.platform.avalara.io/sre-public/tf-core-modules//aws/ecs/service-service?ref=v3.16.0"
  name                          = local.service_name
  cluster_name                  = local.cluster_name
  desired_count                 = 1
  launchType                    = "FARGATE"
  container_name                = local.service_name
  container_imageTag            = var.docker_image_tag
  container_repositoryURL       = "${aws_ecr_repository.sfmon.repository_url}"
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
    security_group_ids = [aws_security_group.sfmon_service_sg.id]
    subnet_ids         = local.subnet_ids_ecs
  }

  project             = local.application_context
  contact             = local.sre_owner_email
  environment_billing = local.environment_name
  environment_runtime = local.environment_name
  repo                = local.repo_name
}
