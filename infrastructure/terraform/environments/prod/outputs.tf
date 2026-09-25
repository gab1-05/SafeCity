output "vpc_id" {
  description = "VPC identifier."
  value       = module.network.vpc_id
}

output "ecr_repository_urls" {
  description = "Registry URLs to tag and push SafeCity images to."
  value       = module.ecr.repository_urls
}

output "eks_cluster_name" {
  description = "EKS cluster name for `aws eks update-kubeconfig`."
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "Kubernetes API endpoint."
  value       = module.eks.cluster_endpoint
}

output "database_endpoint" {
  description = "PostgreSQL endpoint. Marked sensitive because it is only reachable from inside the VPC."
  value       = module.rds.endpoint
  sensitive   = true
}

output "database_secret_name" {
  description = "Secrets Manager secret holding the database credentials."
  value       = module.secrets.database_secret_name
}

output "redis_primary_endpoint" {
  description = "Redis writer endpoint. Sensitive: internal-only address."
  value       = module.elasticache.primary_endpoint
  sensitive   = true
}

output "media_bucket_name" {
  description = "S3 bucket for incident media."
  value       = module.s3.bucket_name
}

output "alb_dns_name" {
  description = "Public DNS name of the load balancer."
  value       = module.alb.dns_name
}

output "alb_https_enabled" {
  description = "Whether an HTTPS listener was created. False means dev is HTTP-only."
  value       = module.alb.https_enabled
}

output "app_irsa_role_arn" {
  description = "IRSA role ARN to annotate onto the backend service account."
  value       = module.iam_app.app_role_arn
}

output "github_actions_role_arn" {
  description = "Role ARN for the GitHub Actions OIDC workflow to assume."
  value       = module.iam_base.github_actions_role_arn
}

output "alerts_topic_arn" {
  description = "SNS topic receiving CloudWatch alarms."
  value       = module.cloudwatch.alert_topic_arn
}

output "operations_dashboard_name" {
  description = "CloudWatch dashboard name."
  value       = module.cloudwatch.dashboard_name
}
