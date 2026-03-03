variable "aws_region" {
  description = "AWS region (e.g., us-east-1, us-west-2)"
  type        = string
  # default 없음 - terraform.tfvars에서 반드시 설정 필요
}

variable "aws_profile" {
  description = "AWS CLI profile name (aws configure list-profiles로 확인)"
  type        = string
  # default 없음 - terraform.tfvars에서 반드시 설정 필요
}

variable "project_name" {
  description = "Project name - 모든 리소스의 접두사로 사용됨 (고유해야 함!)"
  type        = string
  # default 없음 - terraform.tfvars에서 반드시 설정 필요
}

variable "base_project_name" {
  description = "Base project name without environment suffix (for CI/CD)"
  type        = string
  default     = "aws-agentic-ai"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

# DynamoDB Tables
variable "dynamodb_tables" {
  description = "DynamoDB table names"
  type        = map(string)
  default = {
    agent      = "dev-AgentManagement"
    kb         = "dev-KnowledgeBaseManagement"
    teamtag    = "dev-TeamTagManagement"
    playground = "dev-PlaygroundManagement"
  }
}

# ECS Backend Configuration
variable "backend_container_env" {
  description = "Backend container environment variables"
  type        = map(string)
  default = {
    SKIP_AUTH = "true"
    APP_PORT  = "8000"
  }
}

# Backend Infrastructure Variables
variable "embedding_model_arn" {
  description = "ARN of Bedrock embedding model (region will be replaced dynamically)"
  type        = string
  default     = ""  # 빈 값일 경우 aws_region 변수 사용
}

locals {
  # embedding_model_arn이 비어있으면 동적으로 생성
  embedding_model_arn = var.embedding_model_arn != "" ? var.embedding_model_arn : "arn:aws:bedrock:${var.aws_region}::foundation-model/amazon.titan-embed-text-v1"
}

variable "lambda_zip_path" {
  description = "Path to Lambda deployment package"
  type        = string
  default     = "../../../apps/backend/lambda/kb_creation_handler/kb_creation_handler.zip"
}

variable "lambda_layer_zip_path" {
  description = "Path to Lambda layer deployment package"
  type        = string
  default     = "../../../apps/backend/lambda/layer/kb-dependencies-layer.zip"
}

variable "lambda_sync_checker_zip_path" {
  description = "Path to Lambda sync checker deployment package"
  type        = string
  default     = "../../../apps/backend/lambda/kb_sync_checker/kb_sync_checker.zip"
}

variable "opensearch_additional_principals" {
  description = "Additional IAM principal ARNs for OpenSearch data access"
  type        = list(string)
  default = [
    # Cross-account principals not allowed in OpenSearch Serverless
    # For local development, use AWS_PROFILE or AWS credentials
  ]
}

variable "local_dev_user" {
  description = "IAM username for local development access (without account ID)"
  type        = string
  default     = "dev-ke"
}

