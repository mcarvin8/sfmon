variable "aws_region" {
  type        = string
  description = "AWS deployment region"
}

variable "ecr_repo" {
  type        = string
  description = "The URI of the ECR repository"
}
