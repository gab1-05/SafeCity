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
  description = "Private subnet IDs for the DB subnet group."
  type        = list(string)
}

variable "security_group_id" {
  description = "Security group allowing PostgreSQL from the app tier."
  type        = string
}

variable "instance_class" {
  description = "RDS instance class. db.t4g.micro is the cheapest ARM Graviton option."
  type        = string
  default     = "db.t4g.micro"
}

variable "engine_version" {
  description = "PostgreSQL engine version."
  type        = string
  default     = "16.4"
}

variable "allocated_storage_gb" {
  description = "Initial storage in GiB."
  type        = number
  default     = 20
}

variable "max_allocated_storage_gb" {
  description = "Storage autoscaling ceiling in GiB. Set equal to allocated to disable autoscaling."
  type        = number
  default     = 100
}

variable "db_name" {
  description = "Initial database name."
  type        = string
  default     = "safecity"
}

variable "db_username" {
  description = "Master username. Never use 'postgres' or 'admin'."
  type        = string
  default     = "safecity"
}

variable "db_password" {
  description = "Master password. Supply from Secrets Manager, never from a committed file."
  type        = string
  sensitive   = true
}

variable "multi_az" {
  description = "Run a synchronous standby in a second AZ. Doubles cost; required for production."
  type        = bool
  default     = false
}

variable "backup_retention_days" {
  description = "Automated backup retention. 0 disables backups and is never acceptable outside a throwaway sandbox."
  type        = number
  default     = 7

  validation {
    condition     = var.backup_retention_days == 0 || var.backup_retention_days >= 7
    error_message = "backup_retention_days must be 0 or at least 7; shorter windows are not a real backup strategy."
  }
}

variable "backup_window" {
  description = "Preferred backup window in UTC. 18:00 UTC is 23:30 IST, outside Mumbai business hours."
  type        = string
  default     = "18:00-18:30"
}

variable "maintenance_window" {
  description = "Preferred maintenance window in UTC."
  type        = string
  default     = "sun:19:00-sun:20:00"
}

variable "performance_insights_enabled" {
  description = "Enable Performance Insights. Adds cost; useful when diagnosing slow analytics queries."
  type        = bool
  default     = false
}

variable "performance_insights_retention_days" {
  description = "Performance Insights retention. 7 is the free tier."
  type        = number
  default     = 7
}

variable "log_min_duration_ms" {
  description = "Log statements slower than this many milliseconds. 1000 in dev, 250 in prod."
  type        = string
  default     = "1000"
}

variable "work_mem_kb" {
  description = "PostgreSQL work_mem in kB. Keep modest on small instance classes."
  type        = string
  default     = "4096"
}

variable "deletion_protection" {
  description = "Block accidental deletion of the database. Must be true for staging and prod."
  type        = bool
  default     = false
}

variable "skip_final_snapshot" {
  description = "Skip the final snapshot on destroy. Only acceptable in dev."
  type        = bool
  default     = true
}

variable "apply_immediately" {
  description = "Apply changes immediately instead of during the maintenance window. Causes downtime; dev only."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Common tags applied to every resource."
  type        = map(string)
  default     = {}
}
