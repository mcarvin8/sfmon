terraform {
  backend "s3" {
    acl    = "bucket-owner-full-control"
    bucket = "avalara-finance-dev-us-west-2-tf"
    key    = "443899120762/global/iam/finance-ecs-exec-command-policy/terraform.tfstate"
    region = "us-west-2"
  }
}
