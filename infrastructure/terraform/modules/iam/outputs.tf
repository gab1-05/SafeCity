output "eks_cluster_role_arn" {
  description = "Role ARN for the EKS control plane, or null when create_eks_roles is false."
  value       = length(aws_iam_role.eks_cluster) > 0 ? aws_iam_role.eks_cluster[0].arn : null
}

output "node_role_arn" {
  description = "Role ARN for the managed node group, or null when create_eks_roles is false."
  value       = length(aws_iam_role.node) > 0 ? aws_iam_role.node[0].arn : null
}

output "app_role_arn" {
  description = "IRSA role ARN annotated onto the backend service account, or null when IRSA is disabled."
  value       = length(aws_iam_role.app) > 0 ? aws_iam_role.app[0].arn : null
}

output "github_actions_role_arn" {
  description = "Role ARN GitHub Actions assumes via OIDC for image pushes and deploys, or null when unconfigured."
  value       = length(aws_iam_role.github_actions) > 0 ? aws_iam_role.github_actions[0].arn : null
}
