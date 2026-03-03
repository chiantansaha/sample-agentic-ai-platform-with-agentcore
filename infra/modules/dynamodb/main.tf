# DynamoDB Tables for Agentic AI Platform

# AgentManagement Table
#checkov:skip=CKV_AWS_119:Using AWS-owned CMK encryption (enabled=true). Customer-managed KMS key is optional for this open-source sample.
resource "aws_dynamodb_table" "agent_management" {
  name           = "${var.project_name}-agent-management-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "PK"
  range_key      = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  attribute {
    name = "GSI1PK"
    type = "S"
  }

  attribute {
    name = "GSI1SK"
    type = "S"
  }

  attribute {
    name = "GSI2PK"
    type = "S"
  }

  attribute {
    name = "GSI2SK"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI1"
    hash_key        = "GSI1PK"
    range_key       = "GSI1SK"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "GSI2"
    hash_key        = "GSI2PK"
    range_key       = "GSI2SK"
    projection_type = "ALL"
  }

  server_side_encryption {
    enabled = true
  }

  point_in_time_recovery {
    enabled = var.enable_pitr
  }

  deletion_protection_enabled = var.enable_deletion_protection

  tags = {
    Name        = "${var.project_name}-agent-management-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# KnowledgeBaseManagement Table
#checkov:skip=CKV_AWS_119:Using AWS-owned CMK encryption (enabled=true). Customer-managed KMS key is optional for this open-source sample.
resource "aws_dynamodb_table" "kb_management" {
  name           = "${var.project_name}-kb-management-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "PK"
  range_key      = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  attribute {
    name = "GSI1PK"
    type = "S"
  }

  attribute {
    name = "GSI1SK"
    type = "S"
  }

  attribute {
    name = "GSI2PK"
    type = "S"
  }

  attribute {
    name = "GSI2SK"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI1"
    hash_key        = "GSI1PK"
    range_key       = "GSI1SK"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "GSI2"
    hash_key        = "GSI2PK"
    range_key       = "GSI2SK"
    projection_type = "ALL"
  }

  server_side_encryption {
    enabled = true
  }

  point_in_time_recovery {
    enabled = var.enable_pitr
  }

  deletion_protection_enabled = var.enable_deletion_protection

  tags = {
    Name        = "${var.project_name}-kb-management-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# PlaygroundManagement Table
#checkov:skip=CKV_AWS_119:Using AWS-owned CMK encryption (enabled=true). Customer-managed KMS key is optional for this open-source sample.
resource "aws_dynamodb_table" "playground_management" {
  name           = "${var.project_name}-playground-management-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "PK"
  range_key      = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  attribute {
    name = "GSI1PK"
    type = "S"
  }

  attribute {
    name = "GSI1SK"
    type = "S"
  }

  attribute {
    name = "GSI2PK"
    type = "S"
  }

  attribute {
    name = "GSI2SK"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI1"
    hash_key        = "GSI1PK"
    range_key       = "GSI1SK"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "GSI2"
    hash_key        = "GSI2PK"
    range_key       = "GSI2SK"
    projection_type = "ALL"
  }

  server_side_encryption {
    enabled = true
  }

  point_in_time_recovery {
    enabled = var.enable_pitr
  }

  deletion_protection_enabled = var.enable_deletion_protection

  tags = {
    Name        = "${var.project_name}-playground-management-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# KB Versions Table
#checkov:skip=CKV_AWS_119:Using AWS-owned CMK encryption (enabled=true). Customer-managed KMS key is optional for this open-source sample.
resource "aws_dynamodb_table" "kb_versions" {
  name           = "${var.project_name}-kb-versions-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "kb_id"
  range_key      = "version"

  attribute {
    name = "kb_id"
    type = "S"
  }

  attribute {
    name = "version"
    type = "N"
  }

  server_side_encryption {
    enabled = true
  }

  point_in_time_recovery {
    enabled = var.enable_pitr
  }

  deletion_protection_enabled = var.enable_deletion_protection

  tags = {
    Name        = "${var.project_name}-kb-versions-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# PlaygroundConversations Table
#checkov:skip=CKV_AWS_119:Using AWS-owned CMK encryption (enabled=true). Customer-managed KMS key is optional for this open-source sample.
resource "aws_dynamodb_table" "playground_conversations" {
  name           = "${var.project_name}-playground-conversations-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "PK"
  range_key      = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  attribute {
    name = "GSI1PK"
    type = "S"
  }

  attribute {
    name = "GSI1SK"
    type = "S"
  }

  global_secondary_index {
    name            = "UserConversationsIndex"
    hash_key        = "GSI1PK"
    range_key       = "GSI1SK"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "TTL"
    enabled        = true
  }

  server_side_encryption {
    enabled = true
  }

  point_in_time_recovery {
    enabled = var.enable_pitr
  }

  deletion_protection_enabled = var.enable_deletion_protection

  tags = {
    Name        = "${var.project_name}-playground-conversations-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Purpose     = "Playground conversation metadata"
  }
}
