provider "aws" {
  region = var.aws_region
}

data "aws_iam_policy_document" "ecs-exec-command-policy-doc" {
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

resource "aws_iam_policy" "ecs-exec-command-policy" {
  name        = "${var.application_context}-ecs-exec-command-policy"
  description = "IAM policy with ECS execute-command permissions"
  policy      = data.aws_iam_policy_document.ecs-exec-command-policy-doc.json

  tags = merge(
    module.tags.tags,
    { Name = "${var.application_context}-ecs-exec-command-policy" }
  )
}