# The ECR image repository for application images.
resource "aws_ecr_repository" "sfmon" {
  name = local.ecr_name

  tags = merge(
    module.tags.tags,
    { Name = local.ecr_name }
  )
}

# The ECR lifecycle policy.
resource "aws_ecr_lifecycle_policy" "sfmon" {
  repository = aws_ecr_repository.sfmon.name

  policy = <<EOF
{
  "rules": [
    {
      "action": {
        "type": "expire"
      },
      "selection": {
        "countType": "imageCountMoreThan",
        "countNumber": 10,
        "tagStatus": "any"
      },
      "description": "Keep last 10 images.",
      "rulePriority": 1
    }
  ]
}
EOF
}
