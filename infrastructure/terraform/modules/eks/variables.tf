variable "project" {
  description = "Project slug used in resource names."
  type        = string
  default     = "safecity"
}

variable "environment" {
  description = "Deployment environment: dev, staging or prod."
  type        = string
}

variable "kubernetes_version" {
  description = "EKS control plane version."
  type        = string
  default     = "1.30"
}

variable "cluster_role_arn" {
  description = "IAM role ARN the EKS control plane assumes. Created by the iam module."
  type        = string
}

variable "node_role_arn" {
  description = "IAM role ARN for the managed node group. Created by the iam module."
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for control plane ENIs and worker nodes."
  type        = list(string)
}

variable "security_group_id" {
  description = "Security group for cluster and node networking."
  type        = string
}

variable "endpoint_public_access" {
  description = "Expose the Kubernetes API publicly. Required for GitHub-hosted runners to deploy, at the cost of a public endpoint."
  type        = bool
  default     = true
}

variable "public_access_cidrs" {
  description = "CIDRs allowed to reach the public API endpoint. Restrict to office/VPN ranges where possible."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "enabled_cluster_log_types" {
  description = "Control plane log types shipped to CloudWatch."
  type        = list(string)
  default     = ["api", "audit", "authenticator"]
}

variable "kms_key_arn" {
  description = "KMS key for envelope-encrypting Kubernetes secrets. Empty leaves secrets at the etcd disk layer only."
  type        = string
  default     = ""
}

variable "node_instance_types" {
  description = "Instance types for the managed node group. t3.medium is the smallest viable for the addons plus the app."
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_capacity_type" {
  description = "ON_DEMAND or SPOT. Spot is much cheaper but can be reclaimed with two minutes notice."
  type        = string
  default     = "ON_DEMAND"

  validation {
    condition     = contains(["ON_DEMAND", "SPOT"], var.node_capacity_type)
    error_message = "node_capacity_type must be ON_DEMAND or SPOT."
  }
}

variable "node_ami_type" {
  description = "AMI type for the nodes. AL2023_ARM_64_STANDARD pairs with Graviton instance families."
  type        = string
  default     = "AL2023_x86_64_STANDARD"
}

variable "node_disk_size_gb" {
  description = "Node root volume size. Needs room for image layers of backend, frontend and Celery."
  type        = number
  default     = 30
}

variable "node_desired_size" {
  description = "Desired node count. Must be at least 2 so a rolling node replacement keeps capacity."
  type        = number
  default     = 2
}

variable "node_min_size" {
  description = "Minimum node count."
  type        = number
  default     = 2
}

variable "node_max_size" {
  description = "Maximum node count for cluster autoscaling headroom."
  type        = number
  default     = 4
}

variable "deploy_role_arn" {
  description = "CI role granted namespaced edit access for deployments. Empty skips the access entry."
  type        = string
  default     = ""
}

variable "app_namespace" {
  description = "Namespace the deploy role may edit."
  type        = string
  default     = "safecity"
}

variable "tags" {
  description = "Common tags applied to every resource."
  type        = map(string)
  default     = {}
}
