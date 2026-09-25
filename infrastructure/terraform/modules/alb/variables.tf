variable "project" {
  description = "Project slug used in resource names."
  type        = string
  default     = "safecity"
}

variable "environment" {
  description = "Deployment environment: dev, staging or prod."
  type        = string
}

variable "vpc_id" {
  description = "VPC to create the load balancer in."
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs. An internet-facing ALB needs at least two AZs."
  type        = list(string)
}

variable "security_group_id" {
  description = "Security group allowing 80/443 from the internet."
  type        = string
}

variable "certificate_arn" {
  description = "ACM certificate ARN. Empty keeps the stack HTTP-only, which is only appropriate for local/internal testing."
  type        = string
  default     = ""
}

variable "ssl_policy" {
  description = "TLS security policy for the HTTPS listener."
  type        = string
  default     = "ELBSecurityPolicy-TLS13-1-2-2021-06"
}

variable "domain_name" {
  description = "DNS name for the application, e.g. safecity.example.org. Empty skips the Route 53 record."
  type        = string
  default     = ""
}

variable "hosted_zone_id" {
  description = "Route 53 hosted zone ID. Empty skips the Route 53 record."
  type        = string
  default     = ""
}

variable "idle_timeout_seconds" {
  description = "ALB idle timeout. Must exceed the WebSocket keepalive interval."
  type        = number
  default     = 120
}

variable "deregistration_delay_seconds" {
  description = "Time to drain in-flight requests when a target goes away during a rolling deploy."
  type        = number
  default     = 30
}

variable "enable_deletion_protection" {
  description = "Block accidental deletion of the load balancer."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Common tags applied to every resource."
  type        = map(string)
  default     = {}
}
