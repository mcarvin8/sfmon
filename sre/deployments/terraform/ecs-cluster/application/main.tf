locals {
  cluster_name = "monitoring"
}

resource "aws_ecs_cluster" "cluster" {
  name = local.cluster_name

  tags = merge(
    module.tags.tags,
    { Name = local.cluster_name }
  )
}
