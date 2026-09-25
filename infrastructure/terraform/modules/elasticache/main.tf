locals {
  name = "${var.project}-${var.environment}"

  # automatic_failover requires at least two cache clusters, so the node count
  # is derived from the multi-AZ switch rather than configured separately.
  node_count = var.multi_az ? 2 : 1
}

resource "aws_elasticache_subnet_group" "this" {
  name       = "${local.name}-redis"
  subnet_ids = var.private_subnet_ids

  tags = merge(var.tags, { Name = "${local.name}-redis-subnet-group" })
}

resource "aws_elasticache_replication_group" "this" {
  replication_group_id = "${local.name}-redis"
  description          = "SafeCity Redis: Celery broker, cache, rate limits, Channels layer"

  engine         = "redis"
  engine_version = var.engine_version
  node_type      = var.node_type
  port           = 6379

  num_cache_clusters         = local.node_count
  automatic_failover_enabled = var.multi_az
  multi_az_enabled           = var.multi_az

  subnet_group_name  = aws_elasticache_subnet_group.this.name
  security_group_ids = [var.security_group_id]

  # Both encryption layers are on unconditionally: Redis carries Celery job
  # payloads and notification content, and there is no scenario where plaintext
  # is acceptable.
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true

  # Only meaningful (and only consulted) when transit encryption is enabled.
  auth_token = var.auth_token

  # An unused cache cluster is still a bill, but the data is reconstructible
  # from PostgreSQL, so snapshots are a recovery convenience, not the source of truth.
  snapshot_retention_limit = var.snapshot_retention_days
  snapshot_window          = "19:00-20:00"

  maintenance_window         = "sun:20:30-sun:21:30"
  auto_minor_version_upgrade = true
  apply_immediately          = var.apply_immediately

  tags = merge(var.tags, { Name = "${local.name}-redis" })

  lifecycle {
    # Changing the auth token on a live cluster would break every worker at once.
    ignore_changes = [auth_token]
  }
}
