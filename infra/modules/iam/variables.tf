variable "project_name" {
  description = "Project name prefix"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "s3_bucket_arn" {
  description = "ARN of S3 bucket for KB files"
  type        = string
}

variable "opensearch_collection_arn" {
  description = "ARN of OpenSearch Serverless collection"
  type        = string
}

variable "embedding_model_arn" {
  description = "ARN of Bedrock embedding model"
  type        = string
}

variable "sqs_queue_arn" {
  description = "ARN of SQS queue for KB creation"
  type        = string
}

variable "sqs_sync_queue_arn" {
  description = "ARN of SQS queue for KB sync checker"
  type        = string
}

variable "dynamodb_kb_table_arn" {
  description = "ARN of DynamoDB KB management table"
  type        = string
}

variable "dynamodb_kb_version_table_arn" {
  description = "ARN of DynamoDB KB version table"
  type        = string
}

variable "playground_sessions_bucket_arn" {
  description = "ARN of S3 bucket for playground sessions"
  type        = string
}

variable "playground_ecr_repository_arn" {
  description = "ARN of ECR repository for playground agent images"
  type        = string
  default     = ""
}
