# Security group for the application load balancer.
resource "aws_security_group" "load_balancer" {
  name        = local.load_balancer_security_group_name
  description = "${var.environment_name} Prometheus service load balancer"
  vpc_id      = var.vpc_id

  tags = merge(
    module.tags.tags,
    { Name = local.load_balancer_security_group_name }
  )
}

# Security group rule for the application load balancer: ingress to Prometheus port from the network.
resource "aws_security_group_rule" "load_balancer_prometheus_http_in" {
  type            = "ingress"
  from_port       = local.load_balancer_port_prometheus
  to_port         = local.load_balancer_port_prometheus
  protocol        = "tcp"
  cidr_blocks     = var.load_balancer_ingress
  description     = "Allow Prometheus traffic from the network into the load balancer"

  security_group_id = aws_security_group.load_balancer.id
}

# Security group rule for the application load balancer: ingress to Prometheus Push Gateway port from the network.
resource "aws_security_group_rule" "load_balancer_prometheus_pushgw_http_in" {
  type            = "ingress"
  from_port       = local.container_values.prometheus_pushgateway.container_port
  to_port         = local.container_values.prometheus_pushgateway.container_port
  protocol        = "tcp"
  cidr_blocks     = var.load_balancer_ingress
  description     = "Allow Prometheus Push Gateway traffic from the network into the load balancer"

  security_group_id = aws_security_group.load_balancer.id
}

# Security group rule for the application load balancer: all traffic egress.
resource "aws_security_group_rule" "load_balancer_all_out" {
  type            = "egress"
  from_port       = 0
  to_port         = 0
  protocol        = "-1"
  cidr_blocks     = ["0.0.0.0/0"]
  
  security_group_id = aws_security_group.load_balancer.id
}

# Security group for the containers.
resource "aws_security_group" "container" {
  name        = local.container_security_group_name
  description = "Allow port 80 into the container"
  vpc_id      = var.vpc_id

  tags = merge(
    module.tags.tags,
    { Name = local.container_security_group_name }
  )
}

# Security group rules for the containers: ingress to Prometheus from the load-balancer.
resource "aws_security_group_rule" "container_prometheus_http_in" {
  type                     = "ingress"
  from_port                = local.container_values.prometheus.container_port
  to_port                  = local.container_values.prometheus.container_port
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.load_balancer.id
  description              = "Allow Prometheus traffic from the load balancer into the container"

  security_group_id = aws_security_group.container.id
}

# Security group rules for the containers: ingress to Prometheus Push Gateway from the load-balancer.
resource "aws_security_group_rule" "container_prometheus_pushgw_http_in" {
  type                     = "ingress"
  from_port                = local.container_values.prometheus_pushgateway.container_port
  to_port                  = local.container_values.prometheus_pushgateway.container_port
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.load_balancer.id
  description              = "Allow Prometheus Push Gateway traffic from the load balancer into the container"

  security_group_id = aws_security_group.container.id
}

# Security group rule for the containers: all traffic egress.
resource "aws_security_group_rule" "container_all_out" {
  type            = "egress"
  from_port       = 0
  to_port         = 0
  protocol        = "-1"
  cidr_blocks     = ["0.0.0.0/0"]

  security_group_id = aws_security_group.container.id
}

# Allow inbound NFS traffic to the EFS mount targets
resource "aws_security_group_rule" "efs_inbound" {
  type                     = "ingress"
  from_port                = 2049
  to_port                  = 2049
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.container.id
  description              = "Allow NFS traffic from ECS tasks to EFS"
  
  security_group_id = aws_security_group.container.id
}

# Allow outbound NFS traffic from ECS tasks
resource "aws_security_group_rule" "container_efs_outbound" {
  type            = "egress"
  from_port       = 2049
  to_port         = 2049
  protocol        = "tcp"
  cidr_blocks     = ["0.0.0.0/0"] # Or restrict to the EFS mount targets' CIDR blocks if preferred
  
  security_group_id = aws_security_group.container.id
}

