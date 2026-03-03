output "alb_dns_name" {
  description = "ALB DNS name"
  value       = aws_lb.main.dns_name
}

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
