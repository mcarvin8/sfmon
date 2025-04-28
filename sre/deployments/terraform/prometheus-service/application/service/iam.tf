# Policy document that enables permissions for the various applications within the service.
data "aws_iam_policy_document" "prometheus_service" {
  # Enables ECS discovery.
  statement {
    actions = [
      "ecs:Describe*",
      "ecs:List*",
    ]

    resources = [
      "*",
    ]
  }

  # Enables the service to download the config file.
  statement {
    actions = [
      "s3:GetObject",
      "s3:GetObjectVersion",
      "s3:ListBucket",
    ]

    resources = [
      "arn:aws:s3:::${aws_s3_bucket.config.id}",
      "arn:aws:s3:::${aws_s3_bucket.config.id}/*",
    ]
  }
}

# Create the policy that enables permissions for the various applications within the service.
resource "aws_iam_policy" "prometheus_service" {
  name       =  local.service_name
  description = "Permissions for various applications within the prometheus service"
  policy      = data.aws_iam_policy_document.prometheus_service.json

  tags = merge(
    module.tags.tags,
    { Name = local.service_name }
  )
}

# Policy document for the ECS exec-command policy.
data "aws_iam_policy_document" "ecs_exec_command" {
  statement {
    actions = [
      "ssmmessages:CreateControlChannel",
      "ssmmessages:CreateDataChannel",
      "ssmmessages:OpenControlChannel",
      "ssmmessages:OpenDataChannel",
    ]

    resources = [
      "*",
    ]
  }
}

# Create the policy that enables ECS exec-command for the service.
resource "aws_iam_policy" "ecs_exec_command" {
  name       =  local.ecs_exec_command_policy_name
  description = "Permissions to enable ECS exec-command"
  policy      = data.aws_iam_policy_document.ecs_exec_command.json

  tags = merge(
    module.tags.tags,
    { Name = local.ecs_exec_command_policy_name }
  )
}

# Policy document for the task role we'll create.
data "aws_iam_policy_document" "ecs_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# Create the ECS task role with the run-time IAM permissions.
resource "aws_iam_role" "prometheus_service_task" {
  name               = local.ecs_task_iam_role_name
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json

  tags = merge(
    module.tags.tags,
    { Name = local.ecs_task_iam_role_name }
  )
}

# Attach the exec-command policy to the ECS task role so we can connect to containers using SSM.
resource "aws_iam_role_policy_attachment" "ecs_exec_command" {
  role       = aws_iam_role.prometheus_service_task.name
  policy_arn = aws_iam_policy.ecs_exec_command.arn
}

# Attach the access policy to the ECS task role so the service applications have the permissions they need.
resource "aws_iam_role_policy_attachment" "prometheus_service" {
  role       = aws_iam_role.prometheus_service_task.name
  policy_arn = aws_iam_policy.prometheus_service.arn
}

# Look up the AWS-managed task execution policy.
data "aws_iam_policy" "ecs_task_execution" {
  arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Generate the JSON document for the secrets read policy.
data "aws_iam_policy_document" "ecs_secrets_read" {
  count = length(var.secret_arns) == 0 ? 0 : 1

  statement {
    actions = [
      "secretsmanager:GetSecretValue",
    ]

    resources = var.secret_arns
  }
}

# Create the policy for reading secrets.
resource "aws_iam_policy" "ecs_secrets" {
  count = length(var.secret_arns) == 0 ? 0 : 1

  name        = local.ecs_secrets_policy_name
  description = "IAM policy with permissions to read secrets from Secrets Manager"
  policy      = data.aws_iam_policy_document.ecs_secrets_read[0].json

  tags = merge(
    module.tags.tags,
    { Name = local.ecs_secrets_policy_name }
  )
}

# Generate the assume-role policy to be used by the new role.
data "aws_iam_policy_document" "ecs_task_execution_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# Create the new ECS task execution role.
resource "aws_iam_role" "ecs_task_execution" {
  name               = local.ecs_task_execution_role_name
  assume_role_policy = data.aws_iam_policy_document.ecs_task_execution_assume_role.json

  tags = merge(
    module.tags.tags,
    { Name = local.ecs_task_execution_role_name }
  )
}

# Attaches the AWS-managed task execution policy to the new role.
resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = data.aws_iam_policy.ecs_task_execution.arn
}

# Attaches our new secrets read policy to the new role.
resource "aws_iam_role_policy_attachment" "ecs_task_execution_secrets" {
  count = length(var.secret_arns) == 0 ? 0 : 1

  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = aws_iam_policy.ecs_secrets[0].arn
}
