output "td_arn" {
  description = "Full ARN of the Task Definition (including both family and revision)"
  value       = module.service.td_arn
}

output "td_revision" {
  description = "Revision of the task in a particular family"
  value       = module.service.td_revision
}

output "ecs_cluster" {
  description = "ARN of ECS cluster where the service runs on"
  value       = module.service.ecs_cluster_arn
}

output "desired_count" {
  description = "Number of instances of the task definition."
  value       = module.service.desired_count
}

output "service_arn" {
  description = "ARN of the ECS service"
  value       = module.service.service_arn
}

output "service_name" {
  description = "Name of the service"
  value       = module.service.service_name
}
