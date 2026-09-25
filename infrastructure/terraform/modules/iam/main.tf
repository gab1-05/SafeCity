locals {
  name = "${var.project}-${var.environment}"
}

# ── Phase 1: EKS control plane and worker node roles ────────────
#
# These must exist *before* the cluster, while the IRSA role below needs the
# cluster's OIDC provider, which only exists *after* it. Environments therefore
# call this module twice: once with create_eks_roles = true and enable_irsa =
# false, and again after the eks module with the reverse. Gating the resources
# is what keeps that from being a circular dependency.

data "aws_iam_policy_document" "eks_cluster_assume" {
  count = var.create_eks_roles ? 1 : 0

  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["eks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "eks_cluster" {
  count = var.create_eks_roles ? 1 : 0

  name               = "${local.name}-eks-cluster"
  assume_role_policy = data.aws_iam_policy_document.eks_cluster_assume[0].json

  tags = merge(var.tags, { Name = "${local.name}-eks-cluster-role" })
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  count = var.create_eks_roles ? 1 : 0

  role       = aws_iam_role.eks_cluster[0].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

data "aws_iam_policy_document" "node_assume" {
  count = var.create_eks_roles ? 1 : 0

  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "node" {
  count = var.create_eks_roles ? 1 : 0

  name               = "${local.name}-eks-node"
  assume_role_policy = data.aws_iam_policy_document.node_assume[0].json

  tags = merge(var.tags, { Name = "${local.name}-eks-node-role" })
}

# These three are the documented minimum for a managed node group: join the
# cluster, run the VPC CNI, and pull images from ECR.
resource "aws_iam_role_policy_attachment" "node_worker" {
  count = var.create_eks_roles ? 1 : 0

  role       = aws_iam_role.node[0].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
}

resource "aws_iam_role_policy_attachment" "node_cni" {
  count = var.create_eks_roles ? 1 : 0

  role       = aws_iam_role.node[0].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
}

resource "aws_iam_role_policy_attachment" "node_ecr" {
  count = var.create_eks_roles ? 1 : 0

  role       = aws_iam_role.node[0].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# ── Phase 2: application role (IRSA) ────────────────────────────
# Pods assume this role through the cluster OIDC provider, so no long-lived
# access key exists anywhere in the cluster or in CI.
data "aws_iam_policy_document" "app_assume" {
  count = var.enable_irsa ? 1 : 0

  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [var.oidc_provider_arn]
    }

    # Only this one service account in this one namespace may assume the role.
    condition {
      test     = "StringEquals"
      variable = "${var.oidc_provider_url}:sub"
      values   = ["system:serviceaccount:${var.namespace}:${var.service_account_name}"]
    }

    condition {
      test     = "StringEquals"
      variable = "${var.oidc_provider_url}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "app" {
  count = var.enable_irsa ? 1 : 0

  name               = "${local.name}-app"
  assume_role_policy = data.aws_iam_policy_document.app_assume[0].json

  tags = merge(var.tags, { Name = "${local.name}-app-role" })
}

data "aws_iam_policy_document" "app_permissions" {
  count = var.enable_irsa ? 1 : 0

  # Deny by default: the only allowed actions are the ones the application uses.

  statement {
    sid    = "MediaBucketObjects"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:AbortMultipartUpload",
      "s3:ListMultipartUploadParts",
    ]
    resources = ["${var.media_bucket_arn}/*"]
  }

  statement {
    sid       = "MediaBucketList"
    effect    = "Allow"
    actions   = ["s3:ListBucket", "s3:GetBucketLocation"]
    resources = [var.media_bucket_arn]
  }

  statement {
    sid       = "ReadOwnSecretsOnly"
    effect    = "Allow"
    actions   = ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"]
    resources = var.secret_arns
  }

  statement {
    sid       = "EcrAuthToken"
    effect    = "Allow"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid    = "EcrPullOwnRepositories"
    effect = "Allow"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
    ]
    resources = var.ecr_repository_arns
  }

  statement {
    sid       = "ShipLogsAndMetrics"
    effect    = "Allow"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents", "cloudwatch:PutMetricData"]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "app" {
  count = var.enable_irsa ? 1 : 0

  name        = "${local.name}-app-policy"
  description = "Least-privilege policy for the SafeCity application pods"
  policy      = data.aws_iam_policy_document.app_permissions[0].json

  tags = merge(var.tags, { Name = "${local.name}-app-policy" })
}

resource "aws_iam_role_policy_attachment" "app" {
  count = var.enable_irsa ? 1 : 0

  role       = aws_iam_role.app[0].name
  policy_arn = aws_iam_policy.app[0].arn
}

# ── GitHub Actions deploy role via OIDC (no long-lived CI keys) ───
data "aws_iam_policy_document" "github_actions_assume" {
  count = var.github_oidc_repository == "" ? 0 : 1

  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = ["arn:aws:iam::${var.account_id}:oidc-provider/token.actions.githubusercontent.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    # Restrict to this repository and to protected refs only, so a PR from a
    # fork cannot assume the deploy role.
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values = [
        "repo:${var.github_oidc_repository}:ref:refs/heads/main",
        "repo:${var.github_oidc_repository}:ref:refs/heads/develop",
        "repo:${var.github_oidc_repository}:environment:production",
      ]
    }
  }
}

resource "aws_iam_role" "github_actions" {
  count = var.github_oidc_repository == "" ? 0 : 1

  name               = "${local.name}-github-actions"
  assume_role_policy = data.aws_iam_policy_document.github_actions_assume[0].json

  tags = merge(var.tags, { Name = "${local.name}-github-actions-role" })
}

data "aws_iam_policy_document" "github_actions_permissions" {
  count = var.github_oidc_repository == "" ? 0 : 1

  statement {
    sid       = "PushImages"
    effect    = "Allow"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid    = "PushToOwnRepositories"
    effect = "Allow"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:CompleteLayerUpload",
      "ecr:InitiateLayerUpload",
      "ecr:PutImage",
      "ecr:UploadLayerPart",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
    ]
    resources = var.ecr_repository_arns
  }

  # Deployment itself runs through EKS access entries rather than broad
  # cluster-admin permissions.
  statement {
    sid       = "DescribeClusterForDeploy"
    effect    = "Allow"
    actions   = ["eks:DescribeCluster", "eks:ListClusters"]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "github_actions" {
  count = var.github_oidc_repository == "" ? 0 : 1

  name        = "${local.name}-github-actions-policy"
  description = "Allows CI to push SafeCity images to ECR and describe the cluster for deploys"
  policy      = data.aws_iam_policy_document.github_actions_permissions[0].json

  tags = merge(var.tags, { Name = "${local.name}-github-actions-policy" })
}

resource "aws_iam_role_policy_attachment" "github_actions" {
  count = var.github_oidc_repository == "" ? 0 : 1

  role       = aws_iam_role.github_actions[0].name
  policy_arn = aws_iam_policy.github_actions[0].arn
}
