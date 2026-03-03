variable "project_name" {
  description = "Project name prefix"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "bedrock_kb_role_arn" {
  description = "ARN of Bedrock KB IAM role"
  type        = string
}

variable "lambda_role_arn" {
  description = "ARN of Lambda execution IAM role"
  type        = string
}

variable "local_dev_user" {
  description = "IAM username for local development access"
  type        = string
  default     = ""
}
