locals {
  name = "${var.project}-${var.environment}"
}

resource "aws_eks_cluster" "this" {
  name     = "${local.name}-eks"
  version  = var.kubernetes_version
  role_arn = var.cluster_role_arn

  vpc_config {
    # Control plane ENIs go in private subnets; public subnets are only for the ALB.
    subnet_ids              = var.private_subnet_ids
    security_group_ids      = [var.security_group_id]
    endpoint_public_access  = var.endpoint_public_access
    endpoint_private_access = true
    public_access_cidrs     = var.endpoint_public_access ? var.public_access_cidrs : null
  }

  # Control plane logs are the first place to look when authentication or
  # admission fails during a deployment.
  enabled_cluster_log_types = var.enabled_cluster_log_types

  # Restrict secrets in etcd to envelope encryption with a KMS key when one is
  # supplied; without it, Kubernetes secrets are only encrypted at the disk layer.
  dynamic "encryption_config" {
    for_each = var.kms_key_arn == "" ? [] : [1]

    content {
      resources = ["secrets"]

      provider {
        key_arn = var.kms_key_arn
      }
    }
  }

  tags = merge(var.tags, { Name = "${local.name}-eks" })

  # The cluster role and its AmazonEKSClusterPolicy attachment are owned by the
  # iam module; the environment wires them together via cluster_role_arn.
}

# ── OIDC provider for IRSA ───────────────────────────────────────
data "tls_certificate" "this" {
  url = aws_eks_cluster.this.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "this" {
  url             = aws_eks_cluster.this.identity[0].oidc[0].issuer
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.this.certificates[0].sha1_fingerprint]

  tags = merge(var.tags, { Name = "${local.name}-eks-oidc" })
}

# ── Managed node group ───────────────────────────────────────────
resource "aws_eks_node_group" "this" {
  cluster_name    = aws_eks_cluster.this.name
  node_group_name = "${local.name}-nodes"
  node_role_arn   = var.node_role_arn

  subnet_ids = var.private_subnet_ids

  instance_types = var.node_instance_types
  capacity_type  = var.node_capacity_type
  disk_size      = var.node_disk_size_gb
  ami_type       = var.node_ami_type

  scaling_config {
    desired_size = var.node_desired_size
    min_size     = var.node_min_size
    max_size     = var.node_max_size
  }

  update_config {
    # Roll one node at a time so the cluster keeps capacity during upgrades.
    max_unavailable = 1
  }

  labels = {
    role        = "safecity-worker"
    environment = var.environment
  }

  # taints = [] intentionally: all workloads share the pool at SDP scale.

  tags = merge(var.tags, { Name = "${local.name}-nodes" })

  lifecycle {
    # The cluster autoscaler (or HPA-driven scaling) owns desired_size at
    # runtime; Terraform must not fight it on every apply.
    ignore_changes = [scaling_config[0].desired_size]
  }
}

# ── Core addons ──────────────────────────────────────────────────
# Managed addons are patched by AWS, which matters for a project with a short
# maintenance window.
resource "aws_eks_addon" "vpc_cni" {
  cluster_name                = aws_eks_cluster.this.name
  addon_name                  = "vpc-cni"
  resolve_conflicts_on_update = "OVERWRITE"

  tags = merge(var.tags, { Name = "${local.name}-vpc-cni" })
}

resource "aws_eks_addon" "coredns" {
  cluster_name                = aws_eks_cluster.this.name
  addon_name                  = "coredns"
  resolve_conflicts_on_update = "OVERWRITE"

  tags = merge(var.tags, { Name = "${local.name}-coredns" })

  depends_on = [aws_eks_node_group.this]
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name                = aws_eks_cluster.this.name
  addon_name                  = "kube-proxy"
  resolve_conflicts_on_update = "OVERWRITE"

  tags = merge(var.tags, { Name = "${local.name}-kube-proxy" })
}

# ── Access for the CI deploy role ────────────────────────────────
# EKS access entries replace the old aws-auth ConfigMap and are scoped to the
# specific role rather than granting blanket cluster-admin.
resource "aws_eks_access_entry" "deploy" {
  count = var.deploy_role_arn == "" ? 0 : 1

  cluster_name  = aws_eks_cluster.this.name
  principal_arn = var.deploy_role_arn
  type          = "STANDARD"

  tags = merge(var.tags, { Name = "${local.name}-deploy-access" })
}

resource "aws_eks_access_policy_association" "deploy" {
  count = var.deploy_role_arn == "" ? 0 : 1

  cluster_name  = aws_eks_cluster.this.name
  principal_arn = var.deploy_role_arn
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSEditPolicy"

  # Edit is scoped to the application namespace only, not the whole cluster.
  access_scope {
    type       = "namespace"
    namespaces = [var.app_namespace]
  }

  depends_on = [aws_eks_access_entry.deploy]
}
