output "django_secret_arn" {
  description = "ARN of the Django settings secret."
  value       = aws_secretsmanager_secret.django.arn
}

output "database_secret_arn" {
  description = "ARN of the database credentials secret."
  value       = aws_secretsmanager_secret.database.arn
}

output "database_secret_name" {
  description = "Name of the database credentials secret, referenced by External Secrets or CSI driver."
  value       = aws_secretsmanager_secret.database.name
}

output "integrations_secret_arn" {
  description = "ARN of the optional integrations secret, or null when none was configured."
  value       = length(aws_secretsmanager_secret.integrations) > 0 ? aws_secretsmanager_secret.integrations[0].arn : null
}

output "database_password" {
  description = "Generated database password. Sensitive: only pass where strictly required."
  value       = random_password.database.result
  sensitive   = true
}
