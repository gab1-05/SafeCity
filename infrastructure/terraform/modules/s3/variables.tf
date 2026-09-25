variable "project" {
  description = "Project slug used in the bucket name."
  type        = string
  default     = "safecity"
}

variable "environment" {
  description = "Deployment environment: dev, staging or prod."
  type        = string
}

variable "allowed_origins" {
  description = "Origins permitted to PUT/GET objects directly (the SPA origins)."
  type        = list(string)
  default     = ["http://localhost:5173"]
}

variable "standard_to_ia_days" {
  description = "Days before incident media moves to STANDARD_IA."
  type        = number
  default     = 90
}

variable "ia_to_glacier_days" {
  description = "Days before incident media moves to Glacier Instant Retrieval."
  type        = number
  default     = 365
}

variable "noncurrent_version_expire_days" {
  description = "Days after which non-current object versions are deleted."
  type        = number
  default     = 90
}

variable "tags" {
  description = "Common tags applied to every resource."
  type        = map(string)
  default     = {}
}
