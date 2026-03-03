# CloudFront Distribution Module
# Architecture: User → CloudFront (HTTPS) → ALB (HTTP) → ECS

# Random string for custom header secret
resource "random_string" "custom_header_secret" {
  length  = 32
  special = false
}

locals {
  custom_header_name  = "X-Custom-Secret"
  custom_header_value = "${var.project_name}-${random_string.custom_header_secret.result}"
}

# CloudFront Distribution
resource "aws_cloudfront_distribution" "main" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "${var.project_name} CloudFront Distribution"
  default_root_object = "index.html"
  web_acl_id          = var.waf_web_acl_arn
  price_class         = var.price_class

  # ALB Origin
  origin {
    domain_name = var.alb_dns_name
    origin_id   = "ALBOrigin"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"  # ALB는 HTTP로 통신
      origin_ssl_protocols   = ["TLSv1.2"]
      origin_read_timeout    = 60
      origin_keepalive_timeout = 5
    }

    # Custom Header for ALB validation (직접 ALB 접근 차단)
    custom_header {
      name  = local.custom_header_name
      value = local.custom_header_value
    }
  }

  # Default behavior (Frontend)
  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD", "OPTIONS"]
    target_origin_id = "ALBOrigin"

    # 캐싱 비활성화 (동적 콘텐츠)
    cache_policy_id          = aws_cloudfront_cache_policy.no_cache.id
    origin_request_policy_id = aws_cloudfront_origin_request_policy.all_viewer.id

    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
  }

  # API behavior (/api/*)
  ordered_cache_behavior {
    path_pattern     = "/api/*"
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD", "OPTIONS"]
    target_origin_id = "ALBOrigin"

    # API는 캐싱 완전 비활성화
    cache_policy_id          = aws_cloudfront_cache_policy.no_cache.id
    origin_request_policy_id = aws_cloudfront_origin_request_policy.all_viewer.id

    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
  }

  # WebSocket support for streaming (/api/v1/playground/*)
  ordered_cache_behavior {
    path_pattern     = "/api/v1/playground/*"
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "ALBOrigin"

    cache_policy_id          = aws_cloudfront_cache_policy.no_cache.id
    origin_request_policy_id = aws_cloudfront_origin_request_policy.all_viewer.id

    viewer_protocol_policy = "redirect-to-https"
    compress               = false  # Streaming은 압축 비활성화
  }

  # Geographic restrictions (none)
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  # SSL Certificate
  viewer_certificate {
    cloudfront_default_certificate = var.acm_certificate_arn == "" ? true : false
    acm_certificate_arn            = var.acm_certificate_arn != "" ? var.acm_certificate_arn : null
    ssl_support_method             = var.acm_certificate_arn != "" ? "sni-only" : null
    minimum_protocol_version       = var.acm_certificate_arn != "" ? "TLSv1.2_2021" : null
  }

  # Custom domain (if provided)
  aliases = var.domain_names

  dynamic "logging_config" {
    for_each = var.logging_bucket != null ? [1] : []
    content {
      bucket          = var.logging_bucket
      include_cookies = false
      prefix          = "cloudfront/"
    }
  }

  tags = {
    Name        = "${var.project_name}-cloudfront-${var.environment}"
    Environment = var.environment
  }
}

# Cache Policy - No Caching (for dynamic content)
resource "aws_cloudfront_cache_policy" "no_cache" {
  name        = "${var.project_name}-no-cache-policy-${var.environment}"
  comment     = "No caching policy for dynamic content"
  min_ttl     = 0
  default_ttl = 0
  max_ttl     = 0

  parameters_in_cache_key_and_forwarded_to_origin {
    # caching disabled (TTL=0) 시에는 cookies/query_strings를 none으로 설정
    cookies_config {
      cookie_behavior = "none"
    }
    headers_config {
      header_behavior = "none"
    }
    query_strings_config {
      query_string_behavior = "none"
    }
    enable_accept_encoding_brotli = false
    enable_accept_encoding_gzip   = false
  }
}

# Origin Request Policy - Forward all viewer headers
resource "aws_cloudfront_origin_request_policy" "all_viewer" {
  name    = "${var.project_name}-all-viewer-policy-${var.environment}"
  comment = "Forward all viewer headers to origin"

  cookies_config {
    cookie_behavior = "all"
  }

  headers_config {
    header_behavior = "allViewerAndWhitelistCloudFront"
    headers {
      items = ["CloudFront-Viewer-Country", "CloudFront-Is-Mobile-Viewer"]
    }
  }

  query_strings_config {
    query_string_behavior = "all"
  }
}

# CloudFront managed prefix list data source
data "aws_ec2_managed_prefix_list" "cloudfront" {
  name = "com.amazonaws.global.cloudfront.origin-facing"
}
