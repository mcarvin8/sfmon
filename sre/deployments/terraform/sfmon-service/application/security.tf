resource "aws_security_group" "sfmon_service_sg" {
  name        = "${var.environment_name}-${local.application_context}-${local.service_name}-container-sg"
  description = "Security group for sfmon service"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    module.tags.tags,
    { Name = "${var.environment_name}-${local.application_context}-${local.service_name}-container-sg" }
  )
}
