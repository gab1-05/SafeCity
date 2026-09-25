variable "project" {
  description = "Project slug used in resource names."
  type        = string
  default     = "safecity"
}

variable "environment" {
  description = "Deployment environment: dev, staging or prod."
  type        = string
}

variable "region" {
  description = "AWS region, used for dashboard widget rendering."
  type        = string
  default     = "ap-south-1"
}

variable "log_group_names" {
  description = "Log group suffixes to create, e.g. [\"backend\", \"celery-worker\"]."
  type        = list(string)
  default     = ["backend", "celery-worker", "celery-beat", "nginx"]
}

variable "log_retention_days" {
  description = "Log retention. Keep short in dev to control cost."
  type        = number
  default     = 14
}

variable "alert_email" {
  description = "Email address subscribed to the alert topic. Empty creates no subscription."
  type        = string
  default     = ""
}

variable "alb_arn_suffix" {
  description = "ALB ARN suffix for metric dimensions. Empty skips the load balancer alarms."
  type        = string
  default     = ""
}

variable "db_instance_id" {
  description = "RDS instance identifier for metric dimensions. Empty skips the database alarms."
  type        = string
  default     = ""
}

variable "redis_replication_group_id" {
  description = "ElastiCache replication group ID. Empty skips the cache alarms."
  type        = string
  default     = ""
}

variable "alb_5xx_threshold" {
  description = "Number of 5xx responses in 5 minutes that trips the alarm."
  type        = number
  default     = 25
}

variable "alb_latency_threshold_seconds" {
  description = "Average target response time in seconds that trips the alarm."
  type        = number
  default     = 2
}

variable "rds_cpu_threshold_percent" {
  description = "Database CPU percentage that trips the alarm."
  type        = number
  default     = 80
}

variable "rds_min_free_storage_bytes" {
  description = "Free storage floor in bytes. Default 2 GiB."
  type        = number
  default     = 2147483648
}

variable "rds_max_connections" {
  description = "Connection count that trips the alarm."
  type        = number
  default     = 80
}

variable "redis_memory_threshold_percent" {
  description = "Redis memory usage percentage that trips the alarm."
  type        = number
  default     = 80
}

variable "redis_eviction_threshold" {
  description = "Number of evictions in 5 minutes that trips the alarm."
  type        = number
  default     = 100
}

variable "create_dashboard" {
  description = "Create the operations dashboard. Only useful once the stack exists."
  type        = bool
  default     = true
}

variable "tags" {
  description = "Common tags applied to every resource."
  type        = map(string)
  default     = {}
}
