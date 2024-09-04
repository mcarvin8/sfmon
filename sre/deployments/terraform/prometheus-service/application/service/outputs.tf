output "prometheus-dns-name" {
  value = aws_lb.this.dns_name
}

output "prometheus-config-s3-bucket" {
  value = aws_s3_bucket.config.id
}
