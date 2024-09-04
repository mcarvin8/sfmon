# Generate the container definitions.
locals {
  # This container copies the configuration file from S3 to the shared location and then exits.
  config_init_container_def = {
    name = local.container_values.config_init.container_name
    image = local.container_values.config_init.docker_image
    essential = false
    entryPoint =[ "/bin/bash" ]
    command = [
      "-c",
      "cd /${local.shared_volume_name} && ${local.aws_s3_sync_cmd}"
    ]
    mountPoints = [{
      sourceVolume = local.shared_volume_name
      containerPath = "/${local.shared_volume_name}"
    }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group" = local.container_values.config_init.log_group_name
        "awslogs-region" = var.aws_region
        "awslogs-stream-prefix" = local.container_values.config_init.container_name
      }
    }
  }

  # The script that will run in the reloader container.
  reloader_script = <<EOF
trap "exit 0" SIGINT SIGTERM SIGTSTP
cd /${local.shared_volume_name} || exit 1

sleep 5
checksums=$(cksum *)

while :; do
  sleep ${var.config_sync_seconds}
  ${local.aws_s3_sync_cmd}
  test_checksums=$(cksum *)
  if [[ $checksums != $test_checksums ]] ; then
    checksums=$test_checksums
    curl -d '' http://localhost:${local.container_values.prometheus.container_port}/-/reload
  fi
done
EOF

  # This container polls for changes in the the confiruation file in S3 then copies the file to the shared location.
  config_reloader_container_def = {
    name = local.container_values.config_reloader.container_name
    image = local.container_values.config_reloader.docker_image
    essential = true
    entryPoint =[ "/bin/bash" ]
    command = [
      "-c",
      local.reloader_script
    ]
    mountPoints = [{
      sourceVolume = local.shared_volume_name
      containerPath = "/${local.shared_volume_name}"
    }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group" = local.container_values.config_reloader.log_group_name
        "awslogs-region" = var.aws_region
        "awslogs-stream-prefix" = local.container_values.config_reloader.container_name
      }
    }
  }

  # This container runs Prometheus.
  prometheus_container_def = {
    name = local.container_values.prometheus.container_name
    image = local.container_values.prometheus.docker_image
    essential = true
    command = [
      "--config.file=/${local.shared_volume_name}/${var.config_file_name}",
      "--storage.tsdb.path=/prometheus",
      "--web.console.libraries=/usr/share/prometheus/console_libraries",
      "--web.console.templates=/usr/share/prometheus/consoles",
      "--web.enable-lifecycle"
    ]
    mountPoints = [{
      sourceVolume = local.shared_volume_name
      containerPath = "/${local.shared_volume_name}"
    }]
    portMappings = [{
      containerPort = local.container_values.prometheus.container_port
      hostPort = local.container_values.prometheus.container_port
    }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group" = local.container_values.prometheus.log_group_name
        "awslogs-region" = var.aws_region
        "awslogs-stream-prefix" = local.container_values.prometheus.container_name
      }
    }
    dependsOn = [{
      condition = "SUCCESS"
      containerName = local.container_values.config_init.container_name
    }]
  }

  # This container runs Prometheus Push Gateway.
  prometheus_pushgateway_container_def = {
    name = local.container_values.prometheus_pushgateway.container_name
    image = local.container_values.prometheus_pushgateway.docker_image
    essential = true
    portMappings = [{
      containerPort = local.container_values.prometheus_pushgateway.container_port
      hostPort = local.container_values.prometheus_pushgateway.container_port
    }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group" = local.container_values.prometheus_pushgateway.log_group_name
        "awslogs-region" = var.aws_region
        "awslogs-stream-prefix" = local.container_values.prometheus_pushgateway.container_name
      }
    }
  }

  # This container runs Teralytics ECS Discovery.
  ecs_discovery_container_def = {
    name = local.container_values.teralytics_ecs_discovery.container_name
    image = local.container_values.teralytics_ecs_discovery.docker_image
    essential = true
    command = [
      "-config.cluster",
      var.ecs_cluster_name_targets,
      "-config.write-to",
      "/${local.shared_volume_name}/ecs_file_sd.yml"
    ]
    mountPoints = [{
      sourceVolume = local.shared_volume_name
      containerPath = "/${local.shared_volume_name}"
    }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group" = local.container_values.teralytics_ecs_discovery.log_group_name
        "awslogs-region" = var.aws_region
        "awslogs-stream-prefix" = local.container_values.teralytics_ecs_discovery.container_name
      }
    }
  }

  container_definitions = [
    local.config_init_container_def,
    local.config_reloader_container_def,
    local.prometheus_container_def,
    local.prometheus_pushgateway_container_def,
    local.ecs_discovery_container_def,
  ]
}
