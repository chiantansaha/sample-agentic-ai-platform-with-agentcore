# =============================================================================
# CloudFront Outputs (Primary Entry Point)
# =============================================================================
output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name (Primary Entry Point)"
  value       = module.cloudfront.distribution_domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = module.cloudfront.distribution_id
}

output "application_url" {
  description = "Application URL (use this to access the application)"
  value       = "https://${module.cloudfront.distribution_domain_name}"
}

# =============================================================================
# ALB Outputs (Internal - not directly accessible)
# =============================================================================
output "alb_dns_name" {
  description = "ALB DNS name (Internal - access blocked, use CloudFront)"
  value       = aws_lb.main.dns_name
}

# output "domain_name" {
#   description = "Application domain name"
#   value       = aws_route53_record.alb.name
# }

output "frontend_ecr_repository_url" {
  description = "Frontend ECR repository URL"
  value       = aws_ecr_repository.frontend.repository_url
}

output "backend_ecr_repository_url" {
  description = "Backend ECR repository URL"
  value       = aws_ecr_repository.backend.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.main.name
}

output "environment" {
  description = "Environment name"
  value       = var.environment
}

# DynamoDB Tables
output "dynamodb_mcp_table_name" {
  description = "DynamoDB MCP table name"
  value       = aws_dynamodb_table.mcp.name
}

output "dynamodb_mcp_versions_table_name" {
  description = "DynamoDB MCP versions table name"
  value       = aws_dynamodb_table.mcp_versions.name
}

# ECR Repository for MCP Server (from module)
output "mcp_server_ecr_repository_url" {
  description = "MCP Server ECR repository URL"
  value       = module.ecr.mcp_server_repository_url
}

output "mcp_server_ecr_repository_name" {
  description = "MCP Server ECR repository name"
  value       = module.ecr.mcp_server_repository_name
}

# Cognito
output "cognito_user_pool_id" {
  description = "Cognito User Pool ID for MCP OAuth"
  value       = aws_cognito_user_pool.mcp.id
}

output "cognito_user_pool_endpoint" {
  description = "Cognito User Pool endpoint"
  value       = aws_cognito_user_pool.mcp.endpoint
}

output "cognito_client_id" {
  description = "Cognito App Client ID for MCP Gateway"
  value       = aws_cognito_user_pool_client.mcp_gateway.id
}

output "cognito_oauth_token_url" {
  description = "Cognito OAuth token endpoint URL"
  # domain과 동기화: 'aws' 예약어 제외
  value       = "https://agentic-ai-mcp-${data.aws_caller_identity.current.account_id}-${var.environment}.auth.${var.aws_region}.amazoncognito.com/oauth2/token"
}

output "cognito_discovery_url" {
  description = "Cognito OpenID Connect discovery URL"
  value       = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.mcp.id}/.well-known/openid-configuration"
}

# Playground outputs
output "playground_agent_code_bucket_name" {
  description = "Playground agent code bucket name"
  value       = module.s3.playground_agent_code_bucket_name
}

output "playground_sessions_bucket_name" {
  description = "Playground sessions bucket name"
  value       = module.s3.playground_sessions_bucket_name
}

output "playground_conversations_table_name" {
  description = "Playground conversations table name"
  value       = module.dynamodb.playground_conversations_table_name
}

output "playground_runtime_role_arn" {
  description = "Playground runtime role ARN"
  value       = module.iam.playground_runtime_role_arn
}

# =====================================================
# GitLab CI/CD Configuration Outputs
# =====================================================
output "aws_account_id" {
  description = "AWS Account ID for CI/CD"
  value       = data.aws_caller_identity.current.account_id
}

output "aws_region" {
  description = "AWS Region for CI/CD"
  value       = var.aws_region
}

output "base_project_name" {
  description = "Base project name without environment suffix for CI/CD"
  value       = var.base_project_name
}

output "project_name" {
  description = "Full project name (with environment) for CI/CD"
  value       = var.project_name
}

output "ecr_registry" {
  description = "ECR Registry URL for CI/CD"
  value       = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com"
}
