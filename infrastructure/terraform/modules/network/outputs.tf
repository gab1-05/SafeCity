output "vpc_id" {
  description = "VPC identifier."
  value       = aws_vpc.this.id
}

output "vpc_cidr" {
  description = "The VPC CIDR block."
  value       = aws_vpc.this.cidr_block
}

output "public_subnet_ids" {
  description = "Public subnet IDs (ALB, NAT gateways)."
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnet IDs (EKS nodes, RDS, ElastiCache)."
  value       = aws_subnet.private[*].id
}

output "availability_zones" {
  description = "AZs the subnets were placed in."
  value       = aws_subnet.private[*].availability_zone
}

output "alb_security_group_id" {
  description = "Security group attached to the public ALB."
  value       = aws_security_group.alb.id
}

output "app_security_group_id" {
  description = "Security group for EKS nodes and SafeCity pods."
  value       = aws_security_group.app.id
}

output "rds_security_group_id" {
  description = "Security group allowing PostgreSQL from the app tier."
  value       = aws_security_group.rds.id
}

output "redis_security_group_id" {
  description = "Security group allowing Redis from the app tier."
  value       = aws_security_group.redis.id
}
