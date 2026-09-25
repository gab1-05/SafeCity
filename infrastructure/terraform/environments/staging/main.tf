locals {
  # Applied to every resource through the modules' `tags` input. The brief
  # requires project, environment, owner and cost centre on all resources.
  common_tags = {
    Project     = var.project
    Environment = var.environment
    Owner       = var.owner
    CostCenter  = var.cost_center
    ManagedBy   = "terraform"
  }

  cluster_name = "${var.project}-${var.environment}-eks"
}

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

# ── Networking ───────────────────────────────────────────────────
module "network" {
  source = "../../modules/network"

  project                 = var.project
  environment             = var.environment
  vpc_cidr                = var.vpc_cidr
  availability_zone_count = var.availability_zone_count
  nat_gateway_per_az      = var.nat_gateway_per_az
  cluster_name            = local.cluster_name
  tags                    = local.common_tags
}

# ── Container registry ───────────────────────────────────────────
module "ecr" {
  source = "../../modules/ecr"

  project          = var.project
  environment      = var.environment
  repository_names = ["backend", "frontend"]
  tags             = local.common_tags
}

# ── Object storage for incident media ────────────────────────────
module "s3" {
  source = "../../modules/s3"

  project         = var.project
  environment     = var.environment
  allowed_origins = var.allowed_origins
  tags            = local.common_tags
}

# ── Secrets ──────────────────────────────────────────────────────
# db_host is intentionally empty: RDS needs the generated password, so passing
# the RDS address back here would be a circular dependency. The host reaches the
# pods through the Helm values instead (see infrastructure/helm/safecity).
module "secrets" {
  source = "../../modules/secrets"

  project                 = var.project
  environment             = var.environment
  db_username             = var.db_username
  db_name                 = var.db_name
  db_host                 = ""
  recovery_window_in_days = var.secret_recovery_window_days
  tags                    = local.common_tags
}

# ── Database ─────────────────────────────────────────────────────
module "rds" {
  source = "../../modules/rds"

  project            = var.project
  environment        = var.environment
  private_subnet_ids = module.network.private_subnet_ids
  security_group_id  = module.network.rds_security_group_id

  instance_class          = var.db_instance_class
  allocated_storage_gb    = var.db_allocated_storage_gb
  max_allocated_storage_gb = var.db_max_allocated_storage_gb
  db_name                 = var.db_name
  db_username             = var.db_username
  db_password             = module.secrets.database_password

  # Staging mirrors production's durability settings so a restore or failover
  # is rehearsed here rather than discovered in production.
  multi_az                     = true
  backup_retention_days        = var.db_backup_retention_days
  performance_insights_enabled = true
  deletion_protection          = true
  skip_final_snapshot          = false
  apply_immediately            = false

  tags = local.common_tags
}

# ── Cache, queue and Channels layer ──────────────────────────────
module "elasticache" {
  source = "../../modules/elasticache"

  project            = var.project
  environment        = var.environment
  private_subnet_ids = module.network.private_subnet_ids
  security_group_id  = module.network.redis_security_group_id

  node_type               = var.redis_node_type
  multi_az                = true
  snapshot_retention_days = 3
  apply_immediately       = false

  tags = local.common_tags
}

# ── IAM phase 1: cluster, node and CI roles ──────────────────────
# The CI role is created here rather than in phase 2 so that eks can grant it a
# namespaced access entry below, avoiding a second dependency cycle.
module "iam_base" {
  source = "../../modules/iam"

  project       = var.project
  environment   = var.environment
  account_id    = data.aws_caller_identity.current.account_id
  create_eks_roles = true
  enable_irsa      = false

  ecr_repository_arns    = values(module.ecr.repository_arns)
  github_oidc_repository = var.github_repository
  tags                   = local.common_tags
}

# ── Kubernetes ───────────────────────────────────────────────────
module "eks" {
  source = "../../modules/eks"

  project            = var.project
  environment        = var.environment
  private_subnet_ids = module.network.private_subnet_ids
  security_group_id  = module.network.app_security_group_id

  cluster_role_arn = module.iam_base.eks_cluster_role_arn
  node_role_arn    = module.iam_base.node_role_arn

  kubernetes_version  = var.kubernetes_version
  node_instance_types = var.node_instance_types
  node_capacity_type  = var.node_capacity_type
  node_desired_size   = var.node_desired_size
  node_min_size       = 2
  node_max_size       = var.node_max_size

  # The API endpoint stays public for GitHub-hosted runners, but production
  # narrows public_access_cidrs via tfvars.
  endpoint_public_access = true
  public_access_cidrs    = var.cluster_public_access_cidrs

  enabled_cluster_log_types = ["api", "audit", "authenticator"]

  deploy_role_arn = module.iam_base.github_actions_role_arn
  app_namespace   = var.app_namespace

  tags = local.common_tags
}

# ── IAM phase 2: application IRSA role ───────────────────────────
module "iam_app" {
  source = "../../modules/iam"

  project     = var.project
  environment = var.environment
  account_id  = data.aws_caller_identity.current.account_id

  create_eks_roles = false
  enable_irsa      = true

  oidc_provider_arn = module.eks.oidc_provider_arn
  oidc_provider_url = module.eks.oidc_provider_url
  namespace         = var.app_namespace

  media_bucket_arn    = module.s3.bucket_arn
  secret_arns = [
    module.secrets.django_secret_arn,
    module.secrets.database_secret_arn,
  ]
  ecr_repository_arns = values(module.ecr.repository_arns)

  # Handled in phase 1 so eks could reference the role.
  github_oidc_repository = ""

  tags = local.common_tags
}

# ── Load balancing ───────────────────────────────────────────────
module "alb" {
  source = "../../modules/alb"

  project            = var.project
  environment        = var.environment
  vpc_id             = module.network.vpc_id
  public_subnet_ids  = module.network.public_subnet_ids
  security_group_id  = module.network.alb_security_group_id

  # Staging must serve HTTPS: cookie and HSTS behaviour cannot be validated
  # over plain HTTP, so a certificate is effectively required here.
  certificate_arn = var.certificate_arn
  domain_name     = var.domain_name
  hosted_zone_id  = var.hosted_zone_id

  enable_deletion_protection = true

  tags = local.common_tags
}

# ── Observability ────────────────────────────────────────────────
module "cloudwatch" {
  source = "../../modules/cloudwatch"

  project     = var.project
  environment = var.environment
  region      = data.aws_region.current.name

  log_group_names  = ["backend", "celery-worker", "celery-beat"]
  log_retention_days = var.log_retention_days
  alert_email        = var.alert_email

  alb_arn_suffix             = module.alb.alb_arn_suffix
  db_instance_id             = module.rds.instance_id
  redis_replication_group_id = module.elasticache.replication_group_id

  create_dashboard = true

  tags = local.common_tags
}
