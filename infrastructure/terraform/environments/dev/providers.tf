provider "aws" {
  region = var.region

  # `default_tags` is deliberately NOT used here. Every module already receives
  # the common tag map explicitly, so the tags a resource carries are visible in
  # its own block rather than hidden in provider configuration. This also avoids
  # the perpetual-diff problems default_tags causes with ASG-backed resources.
  #
  # Credentials are never configured here. Use one of:
  #   - `aws configure sso` (recommended),
  #   - AWS_PROFILE / AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY environment variables,
  #   - an assumed role in CI via GitHub OIDC.
  # Nothing in this repository stores an access key.
}
