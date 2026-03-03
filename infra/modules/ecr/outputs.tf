# ECR Module Outputs

output "repository_url" {
  description = "ECR repository URL for playground agents"
  value       = aws_ecr_repository.playground_agents.repository_url
}

output "repository_name" {
  description = "ECR repository name for playground agents"
  value       = aws_ecr_repository.playground_agents.name
}

output "repository_arn" {
  description = "ECR repository ARN"
  value       = aws_ecr_repository.playground_agents.arn
}

output "registry_id" {
  description = "ECR registry ID (AWS Account ID)"
  value       = aws_ecr_repository.playground_agents.registry_id
}

# MCP Server ECR outputs
output "mcp_server_repository_url" {
  description = "ECR repository URL for MCP server"
  value       = aws_ecr_repository.mcp_server.repository_url
}

output "mcp_server_repository_arn" {
  description = "ECR repository ARN for MCP server"
  value       = aws_ecr_repository.mcp_server.arn
}

output "mcp_server_repository_name" {
  description = "ECR repository name for MCP server"
  value       = aws_ecr_repository.mcp_server.name
}
