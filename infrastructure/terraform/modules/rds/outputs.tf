output "instance_id" {
  description = "RDS instance identifier."
  value       = aws_db_instance.this.id
}

output "endpoint" {
  description = "Connection endpoint in host:port form."
  value       = aws_db_instance.this.endpoint
}

output "address" {
  description = "Database hostname without the port."
  value       = aws_db_instance.this.address
}

output "port" {
  description = "Database port."
  value       = aws_db_instance.this.port
}

output "database_name" {
  description = "Initial database name."
  value       = aws_db_instance.this.db_name
}

output "arn" {
  description = "Instance ARN, useful for IAM and CloudWatch policies."
  value       = aws_db_instance.this.arn
}

output "resource_id" {
  description = "Instance resource ID used as the CloudWatch dimension for RDS metrics."
  value       = aws_db_instance.this.resource_id
}
