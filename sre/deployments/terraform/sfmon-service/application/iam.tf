# Look up the ECS exec-command policy, if specified.
data "aws_iam_policy" "ecs_exec_command" {
  count = var.ecs_exec_command_policy_name == null ? 0 : 1

  name = var.ecs_exec_command_policy_name
}

data "aws_iam_policy_document" "this" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      identifiers = ["ecs-tasks.amazonaws.com"]
      type        = "Service"
    }
  }
}

data "aws_iam_policy_document" "pass_role" {
  statement {
    actions = ["iam:PassRole"]
    resources = ["arn:aws:iam::${var.aws_account}:role/${var.environment_name}-${local.application_context}-${local.service_name}-exec-role"]
  }
}

resource "aws_iam_policy" "pass_role_policy" {
  name        = "${var.environment_name}-${local.application_context}-${local.service_name}-pass-role"
  description = "Policy to allow passing the ECS execution role"
  policy      = data.aws_iam_policy_document.pass_role.json

  tags = merge(
    module.tags.tags,
    { Name = "${var.environment_name}-${local.application_context}-${local.service_name}-pass-role"}
  )
}

resource "aws_iam_role" "this" {
  name                 = "${var.environment_name}-${local.application_context}-${local.service_name}-exec-role"
  description          = "ECS task execution for ${var.environment_name} ${local.service_name}."
  assume_role_policy   = data.aws_iam_policy_document.this.json
  managed_policy_arns = [
    "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy",
    "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
    "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role",
    aws_iam_policy.pass_role_policy.arn,
    data.aws_iam_policy.ecs_exec_command[0].arn,
  ]
  tags = merge(
    module.tags.tags,
    { Name = "${var.environment_name}-${local.application_context}-${local.service_name}-exec-role" }
  )
}
