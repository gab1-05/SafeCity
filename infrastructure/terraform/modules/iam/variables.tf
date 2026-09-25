variable "project" {
  description = "Project slug used in role names."
  type        = string
  default     = "safecity"
}

variable "environment" {
  description = "Deployment environment: dev, staging or prod."
  type        = string
}

variable "account_id" {
  description = "AWS account ID. Used to build the GitHub Actions OIDC provider ARN."
  type        = string
}

variable "create_eks_roles" {
  description = "Create the EKS control plane and worker node roles. Call the module twice: true before the cluster, false afterwards."
  type        = bool
  default     = true
}

variable "enable_irsa" {
  description = "Create the application IRSA role. Requires the EKS OIDC provider to exist first, so only set this on the second call."
  type        = bool
  default     = true
}

variable "oidc_provider_arn" {
  description = "EKS cluster OIDC provider ARN. Required when enable_irsa is true."
  type        = string
  default     = ""
}

variable "oidc_provider_url" {
  description = "EKS OIDC issuer URL with the https:// prefix stripped."
  type        = string
  default     = ""
}

variable "namespace" {
  description = "Kubernetes namespace the application runs in."
  type        = string
  default     = "safecity"
}

variable "service_account_name" {
  description = "Kubernetes service account allowed to assume the application role."
  type        = string
  default     = "safecity-backend"
}

variable "media_bucket_arn" {
  description = "ARN of the S3 media bucket the application may read and write."
  type        = string
  default     = ""
}

variable "secret_arns" {
  description = "ARNs of the Secrets Manager entries the application may read. Nothing else is readable."
  type        = list(string)
  default     = []
}

variable "ecr_repository_arns" {
  description = "ARNs of the ECR repositories the application and CI may pull from or push to."
  type        = list(string)
  default     = []
}

variable "github_oidc_repository" {
  description = "GitHub repository in owner/name form allowed to assume the deploy role. Empty disables the role."
  type        = string
  default     = ""
}

variable "tags" {
  description = "Common tags applied to every resource."
  type        = map(string)
  default     = {}
}
