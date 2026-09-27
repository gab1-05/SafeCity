variable "project" {
  description = "Project slug used in secret names."
  type        = string
  default     = "safecity"
}

variable "environment" {
  description = "Deployment environment: dev, staging or prod."
  type        = string
}

variable "db_username" {
  description = "Database username stored alongside the generated password."
  type        = string
  default     = "safecity"
}

variable "db_name" {
  description = "Database name stored alongside the generated password."
  type        = string
  default     = "safecity"
}

variable "db_host" {
  description = "Database host. Left empty at plan time and patched after RDS is created."
  type        = string
  default     = ""
}

variable "db_port" {
  description = "Database port."
  type        = number
  default     = 5432
}

variable "integration_secrets" {
  description = "Optional third-party credentials to store. Keep empty for a zero-credential deployment."
  type        = map(string)
  default     = {}
  # Marked sensitive so values never appear in plan output or CI logs.
  sensitive = true
}

variable "recovery_window_in_days" {
  description = "Secrets Manager recovery window. Use 0 in dev so teardown is immediate."
  type        = number
  default     = 7
}

variable "tags" {
  description = "Tags applied to all secrets in this module."
  type        = map(string)
  default     = {}
}
