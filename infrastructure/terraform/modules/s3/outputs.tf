output "bucket_name" {
  description = "Globally unique media bucket name."
  value       = aws_s3_bucket.media.bucket
}

output "bucket_arn" {
  description = "Media bucket ARN for least-privilege IAM policies."
  value       = aws_s3_bucket.media.arn
}

output "bucket_regional_domain_name" {
  description = "Regional domain name used as AWS_S3_ENDPOINT_URL-adjacent configuration."
  value       = aws_s3_bucket.media.bucket_regional_domain_name
}
