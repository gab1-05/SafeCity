output "log_group_names" {
  description = "Map of log group suffix to full log group name."
  value       = { for name, group in aws_cloudwatch_log_group.app : name => group.name }
}

output "log_group_arns" {
  description = "Map of log group suffix to ARN, for IAM log-write policies."
  value       = { for name, group in aws_cloudwatch_log_group.app : name => group.arn }
}

output "alert_topic_arn" {
  description = "SNS topic ARN that all alarms publish to."
  value       = aws_sns_topic.alerts.arn
}

output "dashboard_name" {
  description = "Operations dashboard name, or null when disabled."
  value       = length(aws_cloudwatch_dashboard.this) > 0 ? aws_cloudwatch_dashboard.this[0].dashboard_name : null
}
