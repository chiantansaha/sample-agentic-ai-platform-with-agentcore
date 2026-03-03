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

variable "additional_principal_arns" {
  description = "Additional IAM principal ARNs for data access"
  type        = list(string)
  default     = []
}
