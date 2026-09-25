locals {
  # Bucket names are globally unique, so append the account id.
  bucket_name = "${var.project}-${var.environment}-media-${data.aws_caller_identity.current.account_id}"
}

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "media" {
  bucket = local.bucket_name

  tags = merge(var.tags, { Name = local.bucket_name })

  # Incident media is evidence in a civic workflow; accidental deletion of the
  # bucket would be unrecoverable, so refuse to destroy it while it holds data.
  lifecycle {
    prevent_destroy = true
  }
}

# Incident photos and videos must never be publicly listable/readable. Access is
# only ever through short-lived presigned URLs issued by the backend.
resource "aws_s3_bucket_public_access_block" "media" {
  bucket = aws_s3_bucket.media.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "media" {
  bucket = aws_s3_bucket.media.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "media" {
  bucket = aws_s3_bucket.media.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "media" {
  bucket = aws_s3_bucket.media.id

  # Abort incomplete multipart uploads: large videos that fail mid-upload would
  # otherwise be billed forever as invisible storage.
  rule {
    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  # Media access falls off sharply after the incident is closed, so tier it down
  # rather than paying Standard rates for years of resolution evidence.
  rule {
    id     = "media-to-infrequent-access"
    status = "Enabled"

    filter {
      prefix = "incidents/"
    }

    transition {
      days          = var.standard_to_ia_days
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = var.ia_to_glacier_days
      storage_class = "GLACIER_IR"
    }
  }

  # Expire non-current versions so versioning does not grow without bound.
  rule {
    id     = "expire-noncurrent-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = var.noncurrent_version_expire_days
    }
  }
}

# The SPA fetches uploads directly via presigned PUT, which needs CORS on the bucket.
resource "aws_s3_bucket_cors_configuration" "media" {
  bucket = aws_s3_bucket.media.id

  cors_rule {
    id = "safecity-frontend-upload"

    allowed_methods = ["GET", "PUT", "HEAD"]
    allowed_origins = var.allowed_origins
    allowed_headers = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}
