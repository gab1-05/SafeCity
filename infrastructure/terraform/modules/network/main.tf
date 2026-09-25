locals {
  name = "${var.project}-${var.environment}"

  # Derive subnets from the VPC CIDR so dev/staging/prod only need different
  # base CIDRs, not hand-maintained subnet lists.
  public_subnet_cidrs  = [for i in range(var.availability_zone_count) : cidrsubnet(var.vpc_cidr, 4, i)]
  private_subnet_cidrs = [for i in range(var.availability_zone_count) : cidrsubnet(var.vpc_cidr, 4, i + 8)]

  # EKS/ALB discovery relies on these tags. "shared" means the VPC may be used
  # by more than one cluster, which is true for our dev environment.
  cluster_tags = var.cluster_name == "" ? {} : {
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
  }
}

data "aws_availability_zones" "available" {
  state = "available"

  # Newer local zones (for example ap-south-1-ksl1-az1) are not valid for RDS or
  # NAT gateways, so restrict to standard regional zones.
  filter {
    name   = "opt-in-status"
    values = ["opt-in-not-required"]
  }
}

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(var.tags, { Name = "${local.name}-vpc" })
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = merge(var.tags, { Name = "${local.name}-igw" })
}

# ── Public subnets: internet-facing ALB only ─────────────────────
resource "aws_subnet" "public" {
  count = var.availability_zone_count

  vpc_id                  = aws_vpc.this.id
  cidr_block              = local.public_subnet_cidrs[count.index]
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = false

  # Public subnets are tagged for internet-facing load balancer discovery.
  # The cluster tag (when a cluster name is supplied) comes from local.cluster_tags.
  tags = merge(
    var.tags,
    local.cluster_tags,
    {
      Name                     = "${local.name}-public-${count.index + 1}"
      "kubernetes.io/role/elb" = "1"
    },
  )
}

# ── Private subnets: EKS nodes, RDS, ElastiCache ─────────────────
resource "aws_subnet" "private" {
  count = var.availability_zone_count

  vpc_id            = aws_vpc.this.id
  cidr_block        = local.private_subnet_cidrs[count.index]
  availability_zone = data.aws_availability_zones.available.names[count.index]

  # Private subnets are tagged for internal load balancer discovery.
  tags = merge(
    var.tags,
    local.cluster_tags,
    {
      Name                              = "${local.name}-private-${count.index + 1}"
      "kubernetes.io/role/internal-elb" = "1"
    },
  )
}

# ── NAT: one shared gateway by default (cheap), per-AZ for prod ──
# A NAT gateway costs roughly USD 32/month plus data processing in ap-south-1.
# Dev defaults to a single gateway deliberately; see docs/COST-CONTROL.md.
resource "aws_eip" "nat" {
  count = var.nat_gateway_per_az ? var.availability_zone_count : 1

  domain = "vpc"

  tags = merge(var.tags, { Name = "${local.name}-nat-eip-${count.index + 1}" })

  depends_on = [aws_internet_gateway.this]
}

resource "aws_nat_gateway" "this" {
  count = var.nat_gateway_per_az ? var.availability_zone_count : 1

  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = merge(var.tags, { Name = "${local.name}-nat-${count.index + 1}" })

  depends_on = [aws_internet_gateway.this]
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }

  tags = merge(var.tags, { Name = "${local.name}-public-rt" })
}

resource "aws_route_table" "private" {
  count = var.nat_gateway_per_az ? var.availability_zone_count : 1

  vpc_id = aws_vpc.this.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.this[count.index].id
  }

  tags = merge(var.tags, { Name = "${local.name}-private-rt-${count.index + 1}" })
}

resource "aws_route_table_association" "public" {
  count = var.availability_zone_count

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count = var.availability_zone_count

  subnet_id = aws_subnet.private[count.index].id
  # With a single NAT gateway every private subnet shares one route table.
  route_table_id = var.nat_gateway_per_az ? aws_route_table.private[count.index].id : aws_route_table.private[0].id
}

# ── Security groups: each tier only accepts from the tier above ──
resource "aws_security_group" "alb" {
  name        = "${local.name}-alb"
  description = "Public ingress to the SafeCity load balancer"
  vpc_id      = aws_vpc.this.id

  tags = merge(var.tags, { Name = "${local.name}-alb-sg" })
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  security_group_id = aws_security_group.alb.id
  description       = "HTTP from anywhere (redirected to HTTPS by the listener)"
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 80
  to_port           = 80
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  security_group_id = aws_security_group.alb.id
  description       = "HTTPS from anywhere"
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "alb_to_app" {
  security_group_id            = aws_security_group.alb.id
  description                  = "Forward to application pods only"
  referenced_security_group_id = aws_security_group.app.id
  ip_protocol                  = "-1"
}

resource "aws_security_group" "app" {
  name        = "${local.name}-app"
  description = "EKS worker nodes and SafeCity pods"
  vpc_id      = aws_vpc.this.id

  tags = merge(var.tags, { Name = "${local.name}-app-sg" })
}

resource "aws_vpc_security_group_ingress_rule" "app_from_alb" {
  security_group_id            = aws_security_group.app.id
  description                  = "Application traffic from the ALB"
  referenced_security_group_id = aws_security_group.alb.id
  from_port                    = 8080
  to_port                      = 8080
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "app_self" {
  security_group_id            = aws_security_group.app.id
  description                  = "Node-to-node and pod-to-pod traffic inside the cluster"
  referenced_security_group_id = aws_security_group.app.id
  ip_protocol                  = "-1"
}

resource "aws_vpc_security_group_egress_rule" "app_all" {
  security_group_id = aws_security_group.app.id
  description       = "Outbound to RDS, Redis, S3, ECR and AWS APIs"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_security_group" "rds" {
  name        = "${local.name}-rds"
  description = "PostgreSQL access from application pods"
  vpc_id      = aws_vpc.this.id

  tags = merge(var.tags, { Name = "${local.name}-rds-sg" })
}

resource "aws_vpc_security_group_ingress_rule" "rds_from_app" {
  security_group_id            = aws_security_group.rds.id
  description                  = "PostgreSQL from EKS pods"
  referenced_security_group_id = aws_security_group.app.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
}

resource "aws_security_group" "redis" {
  name        = "${local.name}-redis"
  description = "Redis access from application pods"
  vpc_id      = aws_vpc.this.id

  tags = merge(var.tags, { Name = "${local.name}-redis-sg" })
}

resource "aws_vpc_security_group_ingress_rule" "redis_from_app" {
  security_group_id            = aws_security_group.redis.id
  description                  = "Redis from EKS pods"
  referenced_security_group_id = aws_security_group.app.id
  from_port                    = 6379
  to_port                      = 6379
  ip_protocol                  = "tcp"
}
