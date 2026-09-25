locals {
  name = "${var.project}-${var.environment}"
}

resource "aws_ecr_repository" "this" {
  for_each = toset(var.repository_names)

  name                 = "${local.name}/${each.value}"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    # Scan on push catches vulnerable base images without a separate CI job.
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = merge(var.tags, { Name = "${local.name}-${each.value}" })
}

resource "aws_ecr_lifecycle_policy" "this" {
  for_each = aws_ecr_repository.this

  repository = each.value.name

  # Untagged layers are what actually cost money, so they expire fastest.
  # Tagged release images are retained so a rollback target always exists.
  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images after ${var.untagged_expire_days} days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = var.untagged_expire_days
        }
        action = { type = "expire" }
      },
      {
        rulePriority = 2
        description  = "Keep the most recent ${var.keep_tagged_images} tagged images"
        selection = {
          # tagStatus = "any" must not carry a tagPrefixList.
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = var.keep_tagged_images
        }
        action = { type = "expire" }
      },
    ]
  })
}
