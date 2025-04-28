terraform {
  backend "s3" {
    acl    = "bucket-owner-full-control"
    bucket = "avalara-finance-dev-us-west-2-tf"
    key    = "443899120762/us-west-2/vpc-dev/ecs-cluster/ips-monitoring/terraform.tfstate"
    region = "us-west-2"
  }
}
