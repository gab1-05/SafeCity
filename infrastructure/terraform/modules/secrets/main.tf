locals {
  name = "${var.project}-${var.environment}"
}

# Generated secrets are created here and never written into tfvars, so no
# credential is ever committed to Git or stored in a plaintext variables file.
# Terraform holds them in state, which is why remote state encryption + a
# restricted state bucket are mandatory (see backend.tf.example).
resource "random_password" "django_secret_key" {
  length  = 64
  special = false
}

resource "random_password" "database" {
  length           = 32
  special          = true
  override_special = "!@#$%^&*()-_=+"
}

resource "aws_secretsmanager_secret" "django" {
  name        = "${local.name}/django"
  description = "SafeCity Django settings (SECRET_KEY and application-level secrets)."

  # Allows immediate re-creation if a deployment is torn down and rebuilt.
  recovery_window_in_days = var.recovery_window_in_days

  tags = merge(var.tags, { Name = "${local.name}-django" })
}

resource "aws_secretsmanager_secret_version" "django" {
  secret_id = aws_secretsmanager_secret.django.id

  secret_string = jsonencode({
    SECRET_KEY = random_password.django_secret_key.result
  })
}

resource "aws_secretsmanager_secret" "database" {
  name        = "${local.name}/database"
  description = "SafeCity PostgreSQL credentials for RDS."

  recovery_window_in_days = var.recovery_window_in_days

  tags = merge(var.tags, { Name = "${local.name}-database" })
}

resource "aws_secretsmanager_secret_version" "database" {
  secret_id = aws_secretsmanager_secret.database.id

  secret_string = jsonencode({
    username = var.db_username
    password = random_password.database.result
    engine   = "postgres"
    host     = var.db_host
    port     = var.db_port
    dbname   = var.db_name
  })
}

# Optional integration secrets. Only created when a value is supplied, so the
# platform keeps working with zero third-party credentials (brief §23).
resource "aws_secretsmanager_secret" "integrations" {
  count = length(var.integration_secrets) > 0 ? 1 : 0

  name        = "${local.name}/integrations"
  description = "Optional third-party credentials (email, SMS, AI). Absent means the app uses its mock adapters."

  recovery_window_in_days = var.recovery_window_in_days

  tags = merge(var.tags, { Name = "${local.name}-integrations" })
}

resource "aws_secretsmanager_secret_version" "integrations" {
  count = length(var.integration_secrets) > 0 ? 1 : 0

  secret_id     = aws_secretsmanager_secret.integrations[0].id
  secret_string = jsonencode(var.integration_secrets)
}
