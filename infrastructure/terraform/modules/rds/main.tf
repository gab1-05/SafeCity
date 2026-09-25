locals {
  name = "${var.project}-${var.environment}"
}

resource "aws_db_subnet_group" "this" {
  name       = "${local.name}-db"
  subnet_ids = var.private_subnet_ids

  tags = merge(var.tags, { Name = "${local.name}-db-subnet-group" })
}

resource "aws_db_parameter_group" "this" {
  name        = "${local.name}-pg-params"
  family      = "postgres16"
  description = "SafeCity PostgreSQL parameters"

  # Log slow queries so the analytics endpoints can be tuned from evidence.
  parameter {
    name  = "log_min_duration_statement"
    value = var.log_min_duration_ms
  }

  # PostgreSQL logs queries slower than the threshold above.
  parameter {
    name  = "log_statement"
    value = "ddl"
  }

  # Modest working memory: db.t4g.micro has ~1 GB RAM in dev.
  parameter {
    name  = "work_mem"
    value = var.work_mem_kb
  }

  # Require TLS from the application pods.
  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }

  tags = merge(var.tags, { Name = "${local.name}-db-parameters" })

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_db_instance" "this" {
  identifier = "${local.name}-pg"

  engine         = "postgres"
  engine_version = var.engine_version
  instance_class = var.instance_class

  allocated_storage     = var.allocated_storage_gb
  max_allocated_storage = var.max_allocated_storage_gb
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [var.security_group_id]
  parameter_group_name   = aws_db_parameter_group.this.name
  port                   = 5432

  # Multi-AZ doubles cost; dev deliberately runs single-AZ. Prod must be true.
  multi_az = var.multi_az

  backup_retention_period    = var.backup_retention_days
  backup_window              = var.backup_window
  maintenance_window         = var.maintenance_window
  copy_tags_to_snapshot      = true
  auto_minor_version_upgrade = true

  # Ship PostgreSQL logs to CloudWatch for the incident-response runbook.
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  performance_insights_enabled          = var.performance_insights_enabled
  performance_insights_retention_period = var.performance_insights_enabled ? var.performance_insights_retention_days : null

  # Deletion protection and final snapshots are the guard rails that stop an
  # accidental `terraform destroy` from vaporising citizen incident data.
  deletion_protection       = var.deletion_protection
  skip_final_snapshot       = var.skip_final_snapshot
  final_snapshot_identifier = var.skip_final_snapshot ? null : "${local.name}-pg-final"

  apply_immediately = var.apply_immediately

  tags = merge(var.tags, { Name = "${local.name}-pg" })
}
