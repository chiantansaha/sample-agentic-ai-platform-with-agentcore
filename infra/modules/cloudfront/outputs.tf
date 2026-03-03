# CloudFront Module Outputs

output "distribution_id" {
  description = "CloudFront distribution ID"
  value       = aws_cloudfront_distribution.main.id
}

output "distribution_arn" {
  description = "CloudFront distribution ARN"
  value       = aws_cloudfront_distribution.main.arn
}

output "distribution_domain_name" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.main.domain_name
}

output "distribution_hosted_zone_id" {
  description = "CloudFront distribution hosted zone ID (for Route53)"
  value       = aws_cloudfront_distribution.main.hosted_zone_id
}

output "custom_header_name" {
  description = "Custom header name for ALB validation"
  value       = local.custom_header_name
}

output "custom_header_value" {
  description = "Custom header value for ALB validation"
  value       = local.custom_header_value
  sensitive   = true
}

output "cloudfront_prefix_list_id" {
  description = "CloudFront managed prefix list ID for security group"
  value       = data.aws_ec2_managed_prefix_list.cloudfront.id
}
