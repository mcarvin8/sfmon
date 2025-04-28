terraform {
  backend "s3" {
    acl    = "bucket-owner-full-control"
    bucket = "avalara-biztech-us-west-2-tf"
    key    = "566156093836/global/iam/finance-ecs-exec-command-policy/terraform.tfstate"
    region = "us-west-2"
  }
}
