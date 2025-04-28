# Create the Prometheus config bucket.
resource "aws_s3_bucket" "config" {
  bucket = var.config_bucket_name
  acl    = "private"

  versioning {
    enabled = true
  }

  tags = merge(
    module.tags.tags,
    { Name = var.config_bucket_name }
  )
}

resource "aws_s3_bucket_public_access_block" "config" {
  bucket = aws_s3_bucket.config.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Upload the configuration file(s).
resource "aws_s3_bucket_object" "config_file" {
  for_each = fileset(var.config_source_dir, "*")

  bucket = aws_s3_bucket.config.id
  key = each.key
  source = "${var.config_source_dir}/${each.key}"
  etag = filemd5("${var.config_source_dir}/${each.key}")
}