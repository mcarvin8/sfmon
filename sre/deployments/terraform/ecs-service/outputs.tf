output "td_arn" {
  description = "Full ARN of the Task Definition (including both family and revision)"
  value       = aws_ecs_task_definition.this.arn
}

output "td_revision" {
  description = "Revision of the task in a particular family"
  value       = aws_ecs_task_definition.this.revision
}

output "ecs_cluster_arn" {
  description = "ARN of ECS cluster where the service runs on"
  value       = aws_ecs_service.this.cluster
}

output "desired_count" {
  description = "Number of instances of the task definition"
  value       = aws_ecs_service.this.desired_count
}

output "service_arn" {
  description = "ARN of the ECS service"
  value       = aws_ecs_service.this.id
}

output "service_name" {
  description = "Name of the service"
  value       = aws_ecs_service.this.name
}
