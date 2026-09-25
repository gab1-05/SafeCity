variable "project" {
  description = "Project slug used in repository names."
  type        = string
  default     = "safecity"
}

variable "environment" {
  description = "Deployment environment: dev, staging or prod."
  type        = string
}

variable "repository_names" {
  description = "Repository suffixes to create, e.g. [\"backend\", \"frontend\"]."
  type        = list(string)
  default     = ["backend", "frontend"]
}

variable "untagged_expire_days" {
  description = "Days after which untagged images are expired."
  type        = number
  default     = 14
}

variable "keep_tagged_images" {
  description = "Number of most recent tagged images to retain per repository."
  type        = number
  default     = 20
}

variable "tags" {
  description = "Common tags applied to every resource."
  type        = map(string)
  default     = {}
}
