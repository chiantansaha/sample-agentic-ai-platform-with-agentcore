# Backend Infrastructure Modules for Prod Environment
# This file contains DynamoDB, S3, IAM, OpenSearch, SQS/Lambda modules

# Data sources
data "aws_caller_identity" "current" {}

# DynamoDB Tables
module "dynamodb" {
  source = "../../modules/dynamodb"

  project_name               = var.project_name
  environment                = var.environment
  enable_pitr                = true  # Prod: PITR 활성화
  enable_deletion_protection = true  # Prod: 삭제 보호 활성화
}

# IAM Roles (먼저 생성 - 다른 모듈에서 참조)
module "iam" {
  source = "../../modules/iam"

  project_name  = var.project_name
  environment   = var.environment
  s3_bucket_arn = module.s3.bucket_arn
  opensearch_collection_arn = module.opensearch.collection_arn
  embedding_model_arn       = local.embedding_model_arn
  sqs_queue_arn             = module.sqs_lambda.sqs_queue_arn
  # 계산된 ARN 사용하여 순환 의존성 회피
  sqs_sync_queue_arn             = "arn:aws:sqs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:${var.project_name}-kb-sync-checker-queue"
  dynamodb_kb_table_arn          = module.dynamodb.kb_management_table_arn
  dynamodb_kb_version_table_arn  = module.dynamodb.kb_versions_table_arn
  playground_sessions_bucket_arn = module.s3.playground_sessions_bucket_arn
  playground_ecr_repository_arn  = module.ecr.repository_arn
}

# S3 Bucket
module "s3" {
  source = "../../modules/s3"

  project_name        = var.project_name
  environment         = var.environment
  bedrock_kb_role_arn = module.iam.bedrock_kb_role_arn
  lambda_role_arn     = module.iam.lambda_kb_creation_role_arn
  local_dev_user      = var.local_dev_user
}

# OpenSearch Serverless
module "opensearch" {
  source = "../../modules/opensearch"

  project_name              = var.project_name
  environment               = var.environment
  bedrock_kb_role_arn       = module.iam.bedrock_kb_role_arn
  lambda_role_arn           = module.iam.lambda_kb_creation_role_arn
  additional_principal_arns = var.opensearch_additional_principals
}

# SQS + Lambda for KB Creation
module "sqs_lambda" {
  source = "../../modules/sqs_lambda"

  project_name                   = var.project_name
  environment                    = var.environment
  lambda_zip_path                = var.lambda_zip_path
  lambda_layer_zip_path          = var.lambda_layer_zip_path
  lambda_role_arn                = module.iam.lambda_kb_creation_role_arn
  dynamodb_kb_table_name         = module.dynamodb.kb_management_table_name
  dynamodb_kb_version_table_name = module.dynamodb.kb_versions_table_name
  opensearch_endpoint            = module.opensearch.collection_endpoint
  opensearch_collection_arn      = module.opensearch.collection_arn
  bedrock_kb_role_arn            = module.iam.bedrock_kb_role_arn
  embedding_model_arn            = local.embedding_model_arn
  kb_sync_queue_url              = module.eventbridge_lambda.sqs_queue_url
  log_retention_days             = 365
}

# EventBridge + Lambda for KB Sync Checker
module "eventbridge_lambda" {
  source = "../../modules/eventbridge_lambda"

  project_name                   = var.project_name
  environment                    = var.environment
  lambda_zip_path                = var.lambda_sync_checker_zip_path
  lambda_role_arn                = module.iam.lambda_kb_creation_role_arn
  dynamodb_kb_table_name         = module.dynamodb.kb_management_table_name
  dynamodb_kb_version_table_name = module.dynamodb.kb_versions_table_name
  log_retention_days             = 365
}

# ECR Repository for Playground Agent Images
module "ecr" {
  source = "../../modules/ecr"

  project_name                = var.project_name
  environment                 = var.environment
  enable_cross_account_access = false
  image_retention_count       = 100 # Prod: 더 많은 이미지 보관
}

# CodeBuild for Agent Docker builds
module "codebuild" {
  source = "../../modules/codebuild"

  project_name        = var.project_name
  environment         = var.environment
  ecr_repository_url  = module.ecr.repository_url
  ecr_repository_name = module.ecr.repository_name
  source_bucket_name  = module.s3.agent_build_source_bucket_name
  source_bucket_arn   = module.s3.agent_build_source_bucket_arn
  base_image_ecr_arn  = module.base_image_builder.ecr_repository_arn
  agentcore_role_arn  = module.iam.playground_runtime_role_arn

  depends_on = [module.base_image_builder]
}

# Base Image Builder (Custom Base Image for AgentCore Runtime)
module "base_image_builder" {
  source = "../../modules/base-image-builder"

  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region
}

# ============================================================
# Additional DynamoDB Tables (MCP, API Catalog)
# ============================================================

# MCP Main Table
resource "aws_dynamodb_table" "mcp" {
  name         = "${var.project_name}-mcp"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  attribute {
    name = "team_tags"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "N"
  }

  global_secondary_index {
    name            = "team-tags-index"
    hash_key        = "team_tags"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "created-at-index"
    hash_key        = "created_at"
    projection_type = "ALL"
  }

  #checkov:skip=CKV_AWS_119:Using AWS-owned CMK encryption (enabled=true). Customer-managed KMS key available via module parameter.
  server_side_encryption {
    enabled = true
  }

  point_in_time_recovery {
    enabled = true  # Prod: PITR 활성화
  }

  deletion_protection_enabled = true  # Prod: 삭제 보호 활성화

  tags = {
    Name        = "${var.project_name}-mcp"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# MCP Versions Table
resource "aws_dynamodb_table" "mcp_versions" {
  name         = "${var.project_name}-mcp-versions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "mcp_id"
  range_key    = "version"

  attribute {
    name = "mcp_id"
    type = "S"
  }

  attribute {
    name = "version"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "N"
  }

  global_secondary_index {
    name            = "created-at-index"
    hash_key        = "created_at"
    projection_type = "ALL"
  }

  #checkov:skip=CKV_AWS_119:Using AWS-owned CMK encryption (enabled=true). Customer-managed KMS key available via module parameter.
  server_side_encryption {
    enabled = true
  }

  point_in_time_recovery {
    enabled = true  # Prod: PITR 활성화
  }

  deletion_protection_enabled = true  # Prod: 삭제 보호 활성화

  tags = {
    Name        = "${var.project_name}-mcp-versions"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# API Catalog Table
resource "aws_dynamodb_table" "api_catalog" {
  name         = "${var.project_name}-api-catalog"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  #checkov:skip=CKV_AWS_119:Using AWS-owned CMK encryption (enabled=true). Customer-managed KMS key available via module parameter.
  server_side_encryption {
    enabled = true
  }

  point_in_time_recovery {
    enabled = true  # Prod: PITR 활성화
  }

  deletion_protection_enabled = true  # Prod: 삭제 보호 활성화

  tags = {
    Name        = "${var.project_name}-api-catalog"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
