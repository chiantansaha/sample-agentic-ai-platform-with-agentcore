# CloudFront Module Variables

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "alb_dns_name" {
  description = "ALB DNS name (origin)"
  type        = string
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN for custom domain (leave empty for CloudFront default certificate)"
  type        = string
  default     = ""
}

variable "domain_names" {
  description = "List of custom domain names (CNAMEs)"
  type        = list(string)
  default     = []
}

variable "price_class" {
  description = "CloudFront price class"
  type        = string
  default     = "PriceClass_All"  # PriceClass_100, PriceClass_200, PriceClass_All
}

variable "waf_web_acl_arn" {
  description = "WAF Web ACL ARN to associate with CloudFront distribution"
  type        = string
  default     = null
}

variable "logging_bucket" {
  description = "S3 bucket domain name for CloudFront access logging (e.g., mybucket.s3.amazonaws.com)"
  type        = string
  default     = null
}
