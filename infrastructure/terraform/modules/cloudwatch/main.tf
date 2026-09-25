locals {
  name = "${var.project}-${var.environment}"
}

# ── Logs ─────────────────────────────────────────────────────────
# Container logs land here via the Fluent Bit / firelens log router, not the
# CloudWatch agent, so the retention and encryption settings live on the group.
resource "aws_cloudwatch_log_group" "app" {
  for_each = toset(var.log_group_names)

  name              = "/aws/safecity/${var.environment}/${each.value}"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, { Name = "${local.name}-${each.value}-logs" })
}

# ── Alerts ───────────────────────────────────────────────────────
resource "aws_sns_topic" "alerts" {
  name = "${local.name}-alerts"

  tags = merge(var.tags, { Name = "${local.name}-alerts" })
}

resource "aws_sns_topic_subscription" "email" {
  count = var.alert_email == "" ? 0 : 1

  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# ── Load balancer alarms ─────────────────────────────────────────
# A 5xx rate means the API is failing for citizens; this is the single most
# important alarm in the stack.
resource "aws_cloudwatch_metric_alarm" "alb_5xx" {
  count = var.alb_arn_suffix == "" ? 0 : 1

  alarm_name          = "${local.name}-alb-5xx"
  alarm_description   = "SafeCity API is returning 5xx responses to users."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "HTTPCode_Target_5XX_Count"
  statistic           = "Sum"
  comparison_operator = "GreaterThanThreshold"
  threshold           = var.alb_5xx_threshold
  evaluation_periods  = 1
  period              = 300
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = var.alb_arn_suffix
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]

  tags = merge(var.tags, { Name = "${local.name}-alb-5xx" })
}

resource "aws_cloudwatch_metric_alarm" "alb_unhealthy_hosts" {
  count = var.alb_arn_suffix == "" ? 0 : 1

  alarm_name          = "${local.name}-alb-unhealthy-hosts"
  alarm_description   = "One or more SafeCity targets failed their health check."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "UnHealthyHostCount"
  statistic           = "Maximum"
  comparison_operator = "GreaterThanThreshold"
  threshold           = 0
  evaluation_periods  = 2
  period              = 60
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = var.alb_arn_suffix
  }

  alarm_actions = [aws_sns_topic.alerts.arn]

  tags = merge(var.tags, { Name = "${local.name}-alb-unhealthy-hosts" })
}

resource "aws_cloudwatch_metric_alarm" "alb_latency" {
  count = var.alb_arn_suffix == "" ? 0 : 1

  alarm_name          = "${local.name}-alb-latency"
  alarm_description   = "Target response time is above the ${var.alb_latency_threshold_seconds}s budget."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "TargetResponseTime"
  statistic           = "Average"
  comparison_operator = "GreaterThanThreshold"
  threshold           = var.alb_latency_threshold_seconds
  evaluation_periods  = 3
  period              = 300
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = var.alb_arn_suffix
  }

  alarm_actions = [aws_sns_topic.alerts.arn]

  tags = merge(var.tags, { Name = "${local.name}-alb-latency" })
}

# ── Database alarms ──────────────────────────────────────────────
resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  count = var.db_instance_id == "" ? 0 : 1

  alarm_name          = "${local.name}-rds-cpu"
  alarm_description   = "PostgreSQL CPU saturation will slow every API request."
  namespace           = "AWS/RDS"
  metric_name         = "CPUUtilization"
  statistic           = "Average"
  comparison_operator = "GreaterThanThreshold"
  threshold           = var.rds_cpu_threshold_percent
  evaluation_periods  = 3
  period              = 300
  treat_missing_data  = "notBreaching"

  dimensions = {
    DBInstanceIdentifier = var.db_instance_id
  }

  alarm_actions = [aws_sns_topic.alerts.arn]

  tags = merge(var.tags, { Name = "${local.name}-rds-cpu" })
}

resource "aws_cloudwatch_metric_alarm" "rds_free_storage" {
  count = var.db_instance_id == "" ? 0 : 1

  alarm_name          = "${local.name}-rds-free-storage"
  alarm_description   = "Running out of database storage stops incident writes entirely."
  namespace           = "AWS/RDS"
  metric_name         = "FreeStorageSpace"
  statistic           = "Average"
  comparison_operator = "LessThanThreshold"
  # Bytes: 2 GiB remaining on a gp3 volume with autoscaling headroom.
  threshold          = var.rds_min_free_storage_bytes
  evaluation_periods = 1
  period             = 300
  treat_missing_data = "notBreaching"

  dimensions = {
    DBInstanceIdentifier = var.db_instance_id
  }

  alarm_actions = [aws_sns_topic.alerts.arn]

  tags = merge(var.tags, { Name = "${local.name}-rds-free-storage" })
}

resource "aws_cloudwatch_metric_alarm" "rds_connections" {
  count = var.db_instance_id == "" ? 0 : 1

  alarm_name          = "${local.name}-rds-connections"
  alarm_description   = "Connection count approaching the instance ceiling; check for leaked connections."
  namespace           = "AWS/RDS"
  metric_name         = "DatabaseConnections"
  statistic           = "Average"
  comparison_operator = "GreaterThanThreshold"
  threshold           = var.rds_max_connections
  evaluation_periods  = 3
  period              = 300
  treat_missing_data  = "notBreaching"

  dimensions = {
    DBInstanceIdentifier = var.db_instance_id
  }

  alarm_actions = [aws_sns_topic.alerts.arn]

  tags = merge(var.tags, { Name = "${local.name}-rds-connections" })
}

# ── Cache alarms ─────────────────────────────────────────────────
# Redis serves the Celery broker, so memory exhaustion stalls every async job
# including the SLA sweeps.
resource "aws_cloudwatch_metric_alarm" "redis_memory" {
  count = var.redis_replication_group_id == "" ? 0 : 1

  alarm_name          = "${local.name}-redis-memory"
  alarm_description   = "Redis memory pressure will start evicting cache entries and stalling Celery."
  namespace           = "AWS/ElastiCache"
  metric_name         = "DatabaseMemoryUsagePercentage"
  statistic           = "Average"
  comparison_operator = "GreaterThanThreshold"
  threshold           = var.redis_memory_threshold_percent
  evaluation_periods  = 3
  period              = 300
  treat_missing_data  = "notBreaching"

  dimensions = {
    ReplicationGroupId = var.redis_replication_group_id
  }

  alarm_actions = [aws_sns_topic.alerts.arn]

  tags = merge(var.tags, { Name = "${local.name}-redis-memory" })
}

resource "aws_cloudwatch_metric_alarm" "redis_evictions" {
  count = var.redis_replication_group_id == "" ? 0 : 1

  alarm_name          = "${local.name}-redis-evictions"
  alarm_description   = "Cache evictions may be dropping rate-limit counters, weakening brute-force protection."
  namespace           = "AWS/ElastiCache"
  metric_name         = "Evictions"
  statistic           = "Sum"
  comparison_operator = "GreaterThanThreshold"
  threshold           = var.redis_eviction_threshold
  evaluation_periods  = 2
  period              = 300
  treat_missing_data  = "notBreaching"

  dimensions = {
    ReplicationGroupId = var.redis_replication_group_id
  }

  alarm_actions = [aws_sns_topic.alerts.arn]

  tags = merge(var.tags, { Name = "${local.name}-redis-evictions" })
}

# ── Dashboard ────────────────────────────────────────────────────
resource "aws_cloudwatch_dashboard" "this" {
  count = var.create_dashboard ? 1 : 0

  dashboard_name = "${local.name}-operations"

  dashboard_body = jsonencode({
    widgets = concat(
      var.alb_arn_suffix == "" ? [] : [
        {
          type   = "metric"
          x      = 0
          y      = 0
          width  = 12
          height = 6
          properties = {
            title  = "API requests and errors"
            region = var.region
            metrics = [
              ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", var.alb_arn_suffix],
              [".", "HTTPCode_Target_4XX_Count", ".", "."],
              [".", "HTTPCode_Target_5XX_Count", ".", "."],
            ]
            period = 300
            stat   = "Sum"
          }
        },
      ],
      var.db_instance_id == "" ? [] : [
        {
          type   = "metric"
          x      = 12
          y      = 0
          width  = 12
          height = 6
          properties = {
            title  = "PostgreSQL health"
            region = var.region
            metrics = [
              ["AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", var.db_instance_id],
              [".", "DatabaseConnections", ".", "."],
              [".", "FreeStorageSpace", ".", "."],
            ]
            period = 300
            stat   = "Average"
          }
        },
      ],
    )
  })
}
