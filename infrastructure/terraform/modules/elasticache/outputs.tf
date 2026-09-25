output "primary_endpoint" {
  description = "Primary (writer) endpoint address."
  value       = aws_elasticache_replication_group.this.primary_endpoint_address
}

output "reader_endpoint" {
  description = "Reader endpoint address, present when more than one node exists."
  value       = aws_elasticache_replication_group.this.reader_endpoint_address
}

output "port" {
  description = "Redis port."
  value       = aws_elasticache_replication_group.this.port
}

output "replication_group_id" {
  description = "Replication group identifier."
  value       = aws_elasticache_replication_group.this.replication_group_id
}

output "arn" {
  description = "Replication group ARN."
  value       = aws_elasticache_replication_group.this.arn
}
