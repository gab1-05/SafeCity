variable "project" {
  description = "Project slug used in resource names and tags."
  type        = string
  default     = "safecity"

  validation {
    condition     = can(regex("^[a-z0-9-]{3,20}$", var.project))
    error_message = "project must be 3-20 lowercase alphanumeric or hyphen characters."
  }
}

variable "environment" {
  description = "Deployment environment: dev, staging or prod."
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC. /16 leaves room for the derived /20 subnets."
  type        = string
  default     = "10.20.0.0/16"
}

variable "availability_zone_count" {
  description = "Number of AZs to spread subnets across. Two is the minimum for RDS Multi-AZ and an ALB."
  type        = number
  default     = 2

  validation {
    condition     = var.availability_zone_count >= 2 && var.availability_zone_count <= 3
    error_message = "availability_zone_count must be 2 or 3."
  }
}

variable "nat_gateway_per_az" {
  description = "Create one NAT gateway per AZ. Costs ~USD 32/month each in ap-south-1, so dev uses a single shared gateway."
  type        = bool
  default     = false
}

variable "cluster_name" {
  description = "EKS cluster name used for the kubernetes.io/cluster/<name> subnet tags. Empty disables the tags."
  type        = string
  default     = ""
}

variable "tags" {
  description = "Common tags applied to every resource (Project, Environment, Owner, CostCenter)."
  type        = map(string)
  default     = {}
}
