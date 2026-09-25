# ─────────────────────────────────────────────────────────────
# SafeCity — project-wide Terraform version constraints
#
# WHY THIS FILE EXISTS BUT DOES NOTHING AT INIT TIME
#
# Terraform only reads `.tf` files from the *working directory* it is run in.
# This project is always run from an environment directory:
#
#     cd infrastructure/terraform/environments/dev
#     terraform init
#
# so the constraints below are NOT enforced by `terraform init`. The file that
# init actually reads is `environments/<env>/versions.tf`, which carries the
# same pins. Both files are required:
#
#   * this one  — the single, reviewable statement of the project-wide policy
#   * the per-env files — what Terraform enforces, one copy per environment
#
# Changing a version here is therefore a two-step edit: update this file, then
# update the same pin in every environment that should be affected. CI runs
# `terraform fmt -check` and `terraform validate` per environment, which is what
# catches drift between the copies.
# ─────────────────────────────────────────────────────────────

terraform {
  # 1.6 is the floor for the provider-defined functions and `terraform test`
  # behaviour this configuration relies on. The < 2.0 ceiling prevents an
  # unattended major upgrade from rewriting state format expectations.
  required_version = ">= 1.6.0, < 2.0.0"

  required_providers {
    aws = {
      source = "hashicorp/aws"
      # Pinned to a minor series, not to an exact patch: patch releases are
      # backwards-compatible bug fixes, while a minor bump can change defaults.
      version = "~> 5.60"
    }

    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }

    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}

# ─────────────────────────────────────────────────────────────
# Provider configuration lives in each environment's `providers.tf` so that the
# region and the `default_tags` block can differ per environment. This file
# deliberately declares only constraints and never a `provider` block: a
# provider block here would be silently ignored, which is a confusing way to
# discover that your `provider` settings had no effect.
#
# State is local until you opt in to the S3 + DynamoDB backend described in
# `backend.tf.example`. Local state is acceptable for a first look and unsafe
# the moment two people apply from different machines.
# ─────────────────────────────────────────────────────────────
