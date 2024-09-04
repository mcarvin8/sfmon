# Create the log group for each container.
resource "aws_cloudwatch_log_group" "container" {
  for_each = local.container_values

  name              = each.value.log_group_name
  retention_in_days = 180

  tags = merge(
    module.tags.tags,
    { Name = each.value.log_group_name }
  )
}
