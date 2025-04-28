terraform {
  backend "s3" {
    acl    = "bucket-owner-full-control"
    bucket = "avalara-biztech-us-west-2-tf"
    key    = "566156093836/us-west-2/vpc-prod/ips-prometheus-service/terraform.tfstate"
    region = "us-west-2"
  }
}
