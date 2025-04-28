# Application load balancer.
resource "aws_lb" "this" {
  name               = local.load_balancer_name
  internal           = true
  load_balancer_type = "application"
  security_groups    = [ aws_security_group.load_balancer.id ]
  subnets            = var.load_balancer_subnet_ids

  tags = merge(
    module.tags.tags,
    { Name = local.load_balancer_name }
  )
}

# Prometheus's target group that will get populated by the ECS service.
resource "aws_lb_target_group" "prometheus" {
  name                 = local.target_group_name_prometheus
  port                 = local.container_values.prometheus.container_port
  protocol             = "HTTP"
  target_type          = "ip"
  deregistration_delay = 1
  vpc_id               = var.vpc_id

  health_check {
    path = "/metrics"
  }

  # Necessary because of a race condition between target group registration and ECS service creation.
  depends_on  = [ aws_lb.this ]

  tags = merge(
    module.tags.tags,
    { Name = local.service_name }
  )
}

# Prometheus Push Gateway's target group that will get populated by the ECS service.
resource "aws_lb_target_group" "prometheus_pushgateway" {
  name                 = local.target_group_name_prom_pushgw
  port                 = local.container_values.prometheus_pushgateway.container_port
  protocol             = "HTTP"
  target_type          = "ip"
  deregistration_delay = 1
  vpc_id               = var.vpc_id

  health_check {
    path = "/api/v1/status"
  }

  # Necessary because of a race condition between target group registration and ECS service creation.
  depends_on  = [ aws_lb.this ]

  tags = merge(
    module.tags.tags,
    { Name = local.target_group_name_prom_pushgw }
  )
}

# Prometheus listener.
resource "aws_lb_listener" "prometheus_http" {
  load_balancer_arn = aws_lb.this.arn
  port              = local.load_balancer_port_prometheus
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.prometheus.arn
  }
}

# Avalara Prometheus Agent listener.
resource "aws_lb_listener" "pushgateway_http" {
  load_balancer_arn = aws_lb.this.arn
  port              = local.container_values.prometheus_pushgateway.container_port
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.prometheus_pushgateway.arn
  }
}

