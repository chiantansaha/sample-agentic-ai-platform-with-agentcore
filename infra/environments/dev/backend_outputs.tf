# Backend Infrastructure Outputs

# DynamoDB
output "dynamodb_agent_table_name" {
  description = "AgentManagement table name"
  value       = module.dynamodb.agent_management_table_name
}

output "dynamodb_kb_table_name" {
  description = "KnowledgeBaseManagement table name"
  value       = module.dynamodb.kb_management_table_name
}

output "dynamodb_playground_table_name" {
  description = "PlaygroundManagement table name"
  value       = module.dynamodb.playground_management_table_name
}

output "dynamodb_kb_versions_table_name" {
  description = "KB Versions table name"
  value       = module.dynamodb.kb_versions_table_name
}

# S3
output "s3_kb_files_bucket_name" {
  description = "S3 bucket name for KB files"
  value       = module.s3.bucket_name
}

# IAM
output "bedrock_kb_role_arn" {
  description = "ARN of Bedrock KB IAM role"
  value       = module.iam.bedrock_kb_role_arn
}

output "lambda_kb_creation_role_arn" {
  description = "ARN of Lambda KB creation IAM role"
  value       = module.iam.lambda_kb_creation_role_arn
}

# OpenSearch
output "opensearch_collection_endpoint" {
  description = "OpenSearch Serverless collection endpoint"
  value       = module.opensearch.collection_endpoint
}

output "opensearch_collection_arn" {
  description = "OpenSearch Serverless collection ARN"
  value       = module.opensearch.collection_arn
}

# SQS/Lambda
output "sqs_kb_creation_queue_url" {
  description = "SQS queue URL for KB creation"
  value       = module.sqs_lambda.sqs_queue_url
}

output "lambda_kb_creation_function_name" {
  description = "Lambda function name for KB creation"
  value       = module.sqs_lambda.lambda_function_name
}

# ECR
output "ecr_playground_repository_url" {
  description = "ECR repository URL for playground agents"
  value       = module.ecr.repository_url
}

output "ecr_playground_repository_name" {
  description = "ECR repository name for playground agents"
  value       = module.ecr.repository_name
}

output "ecr_playground_repository_arn" {
  description = "ECR repository ARN for playground agents"
  value       = module.ecr.repository_arn
}

# Playground Sessions
output "playground_sessions_bucket" {
  description = "S3 bucket for Playground sessions"
  value       = module.s3.playground_sessions_bucket_name
}

# CodeBuild
output "codebuild_project_name" {
  description = "CodeBuild project name for Agent builds"
  value       = module.codebuild.codebuild_project_name
}

output "agent_build_source_bucket" {
  description = "S3 bucket for Agent build source code"
  value       = module.s3.agent_build_source_bucket_name
}

# Base Image Builder
output "base_image_uri" {
  description = "Custom base image URI for AgentCore Runtime (latest tag)"
  value       = module.base_image_builder.base_image_uri
}

output "base_image_ecr_repository_url" {
  description = "Base image ECR repository URL"
  value       = module.base_image_builder.ecr_repository_url
}

output "base_image_codebuild_project_name" {
  description = "CodeBuild project name for base image builds"
  value       = module.base_image_builder.codebuild_project_name
}
