variable "project" {
  description = "Project slug used in resource names."
  type        = string
  default     = "safecity"
}

variable "environment" {
  description = "Deployment environment: dev, staging or prod."
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for the cache subnet group."
  type        = list(string)
}

variable "security_group_id" {
  description = "Security group allowing Redis from the app tier."
  type        = string
}

variable "node_type" {
  description = "Cache node type. cache.t4g.micro is the cheapest Graviton option."
  type        = string
  default     = "cache.t4g.micro"
}

variable "engine_version" {
  description = "Redis engine version."
  type        = string
  default     = "7.1"
}

variable "multi_az" {
  description = "Run a replica in a second AZ with automatic failover. Roughly doubles cost."
  type        = bool
  default     = false
}

variable "auth_token" {
  description = "Redis AUTH token. Supply from Secrets Manager. Must be 16-128 characters when set."
  type        = string
  default     = null
  sensitive   = true
}

variable "snapshot_retention_days" {
  description = "Days to retain Redis snapshots. 0 disables snapshots; acceptable because Redis data is reconstructible."
  type        = number
  default     = 0
}

variable "apply_immediately" {
  description = "Apply changes immediately instead of during the maintenance window."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Common tags applied to every resource."
  type        = map(string)
  default     = {}
}
