#  Create the log group for the SFMon service.
resource "aws_cloudwatch_log_group" "sfmon" {
  name               = local.cloudwatch_name
  retention_in_days  = 180

  tags = merge(
    module.tags.tags,
    { Name = local.cloudwatch_name }
  )
}
