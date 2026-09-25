output "repository_urls" {
  description = "Map of repository suffix to full registry URL for docker push."
  value       = { for name, repo in aws_ecr_repository.this : name => repo.repository_url }
}

output "repository_names" {
  description = "Map of repository suffix to repository name."
  value       = { for name, repo in aws_ecr_repository.this : name => repo.name }
}

output "repository_arns" {
  description = "Map of repository suffix to ARN, used by least-privilege IAM policies."
  value       = { for name, repo in aws_ecr_repository.this : name => repo.arn }
}

output "registry_id" {
  description = "AWS account ID hosting the registry."
  value       = length(aws_ecr_repository.this) > 0 ? values(aws_ecr_repository.this)[0].registry_id : null
}
