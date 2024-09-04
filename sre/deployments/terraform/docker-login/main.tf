provider "aws" {
  region = var.aws_region
}

# Retrieves authorization token using environmental AWS credentials.
data "aws_ecr_authorization_token" "token" {
}

# We store the authentication token in a file so that it doesn't appear in the Terraform output.
resource "local_file" "docker-pw" {
  filename = "${path.module}/.terraform/tmp/${timestamp()}.txt"
  file_permission = "0600"
  sensitive_content = data.aws_ecr_authorization_token.token.password
}

# Invoke Docker login by passing in the contents of the password file.
resource "null_resource" "docker-login" {
  provisioner "local-exec" {
    command = "docker login --username AWS --password-stdin ${var.ecr_repo} < ${local_file.docker-pw.filename}"
  }
}

# Delete the password file after logging in.
resource "null_resource" "docker-login-cleanup" {
  provisioner "local-exec" {
    command = "rm ${local_file.docker-pw.filename}"
  }

  depends_on = [ null_resource.docker-login ]
}