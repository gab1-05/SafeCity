locals {
  name = "${var.project}-${var.environment}"

  # An HTTPS listener can only exist with a certificate. ACM certificates also
  # require DNS validation to have completed, so the listener is conditional.
  https_enabled = var.certificate_arn != ""
}

resource "aws_lb" "this" {
  name               = "${local.name}-alb"
  load_balancer_type = "application"
  internal           = false

  security_groups = [var.security_group_id]
  subnets         = var.public_subnet_ids

  # The SPA uploads media through presigned S3 URLs rather than proxying
  # through the ALB, so idle timeout only has to cover normal API calls.
  idle_timeout = var.idle_timeout_seconds

  # SafeCity stores no cookies at the ALB, so the load balancer must not keep them.
  enable_deletion_protection = var.enable_deletion_protection

  # WebSocket traffic (Django Channels) requires an ALB that supports
  # upgrade; application load balancers do this natively.
  drop_invalid_header_fields = true

  tags = merge(var.tags, { Name = "${local.name}-alb" })
}

# ── Target groups ────────────────────────────────────────────────
# The backend target group uses the readiness endpoint so a pod that has lost
# its database or Redis connection is removed from rotation rather than
# receiving traffic it cannot serve.
resource "aws_lb_target_group" "backend" {
  name        = "${local.name}-backend"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  deregistration_delay = var.deregistration_delay_seconds

  health_check {
    enabled             = true
    path                = "/api/readiness/"
    port                = "traffic-port"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  tags = merge(var.tags, { Name = "${local.name}-backend-tg" })
}

resource "aws_lb_target_group" "frontend" {
  name        = "${local.name}-frontend"
  port        = 80
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  deregistration_delay = var.deregistration_delay_seconds

  health_check {
    enabled             = true
    path                = "/"
    port                = "traffic-port"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  tags = merge(var.tags, { Name = "${local.name}-frontend-tg" })
}

# ── Listeners ────────────────────────────────────────────────────
# Port 80 exists only to redirect. Without this, citizens typing the bare
# domain would hit a dead end and never reach the SPA.
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = local.https_enabled ? "redirect" : "forward"

    dynamic "redirect" {
      for_each = local.https_enabled ? [1] : []

      content {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }

    target_group_arn = local.https_enabled ? null : aws_lb_target_group.frontend.arn
  }

  tags = merge(var.tags, { Name = "${local.name}-http-listener" })
}

resource "aws_lb_listener" "https" {
  count = local.https_enabled ? 1 : 0

  load_balancer_arn = aws_lb.this.arn
  port              = 443
  protocol          = "HTTPS"

  # TLS 1.2 minimum: TLS 1.0/1.1 are deprecated and fail most security reviews.
  ssl_policy      = var.ssl_policy
  certificate_arn = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }

  tags = merge(var.tags, { Name = "${local.name}-https-listener" })
}

# API traffic is routed by path. The frontend nginx config also proxies /api/,
# but routing it at the load balancer keeps the SPA image stateless.
resource "aws_lb_listener_rule" "api" {
  count = local.https_enabled ? 1 : 0

  listener_arn = aws_lb_listener.https[0].arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }

  condition {
    path_pattern {
      values = ["/api/*", "/admin/*", "/static/*"]
    }
  }

  tags = merge(var.tags, { Name = "${local.name}-api-rule" })
}

resource "aws_lb_listener_rule" "websocket" {
  count = local.https_enabled ? 1 : 0

  listener_arn = aws_lb_listener.https[0].arn
  priority     = 90

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }

  # Real-time notification sockets are served by Django Channels on the backend.
  condition {
    path_pattern {
      values = ["/ws/*"]
    }
  }

  tags = merge(var.tags, { Name = "${local.name}-websocket-rule" })
}

# ── DNS ──────────────────────────────────────────────────────────
resource "aws_route53_record" "app" {
  count = var.hosted_zone_id == "" || var.domain_name == "" ? 0 : 1

  zone_id = var.hosted_zone_id
  name    = var.domain_name
  type    = "A"

  # Alias record: no TTL, no charge for queries, and it follows the ALB.
  alias {
    name                   = aws_lb.this.dns_name
    zone_id                = aws_lb.this.zone_id
    evaluate_target_health = true
  }
}
