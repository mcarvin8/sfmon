output "prometheus_dns_name" {
  value = module.ecs_service.prometheus-dns-name
}

output "prometheus_config_s3_bucket" {
  value = module.ecs_service.prometheus-config-s3-bucket
}
