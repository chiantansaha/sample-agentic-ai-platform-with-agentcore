variable "project_name" {
  description = "Project name prefix"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "lambda_zip_path" {
  description = "Path to Lambda deployment package"
  type        = string
}

variable "lambda_layer_zip_path" {
  description = "Path to Lambda layer deployment package"
  type        = string
}

variable "lambda_role_arn" {
  description = "ARN of Lambda execution IAM role"
  type        = string
}

variable "dynamodb_kb_table_name" {
  description = "Name of DynamoDB KB management table"
  type        = string
}

variable "dynamodb_kb_version_table_name" {
  description = "Name of DynamoDB KB version table"
  type        = string
}

variable "opensearch_endpoint" {
  description = "Endpoint of OpenSearch Serverless collection"
  type        = string
}

variable "opensearch_collection_arn" {
  description = "ARN of OpenSearch Serverless collection"
  type        = string
}

variable "bedrock_kb_role_arn" {
  description = "ARN of Bedrock KB IAM role"
  type        = string
}

variable "embedding_model_arn" {
  description = "ARN of Bedrock embedding model"
  type        = string
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 365
}

variable "reserved_concurrent_executions" {
  description = "Reserved concurrent executions for Lambda function (-1 for unreserved)"
  type        = number
  default     = -1
}

variable "kb_sync_queue_url" {
  description = "URL of the KB sync checker SQS queue (optional)"
  type        = string
  default     = ""
}
