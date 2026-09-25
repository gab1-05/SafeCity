# ── Identity and tagging ─────────────────────────────────────────
variable "project" {
  description = "Project slug used in every resource name."
  type        = string
  default     = "safecity"
}

variable "environment" {
  description = "Deployment environment. Fixed to dev in this directory."
  type        = string
  default     = "dev"

  validation {
    condition     = var.environment == "dev"
    error_message = "This directory deploys the dev environment only."
  }
}

variable "owner" {
  description = "Owning team or individual, applied as the Owner tag."
  type        = string
  default     = "bombay-salesian-society-sdp"
}

variable "cost_center" {
  description = "Cost centre tag for AWS cost allocation reports."
  type        = string
  default     = "sdp-academic"
}

variable "region" {
  description = "AWS region. ap-south-1 (Mumbai) keeps latency low for the target users."
  type        = string
  default     = "ap-south-1"
}

# ── Networking ───────────────────────────────────────────────────
variable "vpc_cidr" {
  description = "VPC CIDR. Must not overlap the other environments if they share an account."
  type        = string
  default     = "10.20.0.0/16"
}

variable "availability_zone_count" {
  description = "Number of AZs to use. Two is the minimum for a valid ALB."
  type        = number
  default     = 2
}

variable "nat_gateway_per_az" {
  description = "One NAT gateway per AZ. false halves the monthly cost but loses egress redundancy."
  type        = bool
  default     = false
}

variable "allowed_origins" {
  description = "Origins allowed to upload media directly to S3."
  type        = list(string)
  default     = ["http://localhost:5173", "http://localhost:8080"]
}

# ── Database ─────────────────────────────────────────────────────
variable "db_username" {
  description = "PostgreSQL master username."
  type        = string
  default     = "safecity"
}

variable "db_name" {
  description = "Initial database name."
  type        = string
  default     = "safecity"
}

variable "db_instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t4g.micro"
}

variable "db_allocated_storage_gb" {
  description = "Initial database storage in GiB."
  type        = number
  default     = 20
}

variable "db_max_allocated_storage_gb" {
  description = "Storage autoscaling ceiling in GiB."
  type        = number
  default     = 50
}

variable "db_backup_retention_days" {
  description = "Automated backup retention. 0 disables backups, which the module rejects below 7 unless 0."
  type        = number
  default     = 0
}

variable "secret_recovery_window_days" {
  description = "Secrets Manager recovery window. 0 makes dev teardown immediate and irreversible."
  type        = number
  default     = 0
}

# ── Cache ────────────────────────────────────────────────────────
variable "redis_node_type" {
  description = "ElastiCache node type."
  type        = string
  default     = "cache.t4g.micro"
}

# ── Kubernetes ───────────────────────────────────────────────────
variable "kubernetes_version" {
  description = "EKS control plane version."
  type        = string
  default     = "1.30"
}

variable "node_instance_types" {
  description = "Worker node instance types."
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_capacity_type" {
  description = "ON_DEMAND or SPOT. SPOT is ~70% cheaper but can be reclaimed at two minutes' notice."
  type        = string
  default     = "SPOT"
}

variable "node_desired_size" {
  description = "Desired worker node count."
  type        = number
  default     = 2
}

variable "node_max_size" {
  description = "Maximum worker node count."
  type        = number
  default     = 3
}

variable "cluster_public_access_cidrs" {
  description = "CIDRs allowed to reach the Kubernetes API. Narrow this to your own address where possible."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "app_namespace" {
  description = "Namespace the application and the CI deploy role operate in."
  type        = string
  default     = "safecity"
}

# ── CI/CD ────────────────────────────────────────────────────────
variable "github_repository" {
  description = "GitHub repository (owner/name) allowed to assume the deploy role via OIDC. Empty creates no CI role."
  type        = string
  default     = ""
}

# ── TLS and DNS ──────────────────────────────────────────────────
variable "certificate_arn" {
  description = "ACM certificate ARN. Empty leaves the ALB HTTP-only, which is fine for dev."
  type        = string
  default     = ""
}

variable "domain_name" {
  description = "DNS name for the application. Empty skips the Route 53 record."
  type        = string
  default     = ""
}

variable "hosted_zone_id" {
  description = "Route 53 hosted zone ID. Empty skips the Route 53 record."
  type        = string
  default     = ""
}

# ── Observability ────────────────────────────────────────────────
variable "log_retention_days" {
  description = "CloudWatch log retention. Dev keeps this short to control cost."
  type        = number
  default     = 7
}

variable "alert_email" {
  description = "Email subscribed to the alarm topic. Empty creates no subscription."
  type        = string
  default     = ""
}
