output "alb_arn" {
  description = "Load balancer ARN."
  value       = aws_lb.this.arn
}

output "alb_arn_suffix" {
  description = "ARN suffix used as the CloudWatch dimension for ALB metrics and alarms."
  value       = aws_lb.this.arn_suffix
}

output "dns_name" {
  description = "Public DNS name of the load balancer."
  value       = aws_lb.this.dns_name
}

output "zone_id" {
  description = "Canonical hosted zone ID of the load balancer."
  value       = aws_lb.this.zone_id
}

output "backend_target_group_arn" {
  description = "Target group ARN for the Django API."
  value       = aws_lb_target_group.backend.arn
}

output "frontend_target_group_arn" {
  description = "Target group ARN for the React SPA."
  value       = aws_lb_target_group.frontend.arn
}

output "https_enabled" {
  description = "Whether an HTTPS listener was created."
  value       = local.https_enabled
}
