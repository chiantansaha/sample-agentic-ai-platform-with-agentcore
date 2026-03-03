variable "project_name" {
  type        = string
  description = "Project name prefix"
}

variable "environment" {
  type        = string
  description = "Environment (dev, staging, prod)"
}

variable "ecr_repository_url" {
  type        = string
  description = "ECR repository URL for pushing images"
}

variable "ecr_repository_name" {
  type        = string
  description = "ECR repository name for IAM policy"
}

variable "source_bucket_name" {
  type        = string
  description = "S3 bucket name for build source code"
}

variable "source_bucket_arn" {
  type        = string
  description = "S3 bucket ARN for build source code"
}

variable "base_image_ecr_arn" {
  type        = string
  description = "Base image ECR repository ARN for pull access"
  default     = ""
}

variable "agentcore_role_arn" {
  type        = string
  description = "AgentCore Runtime IAM Role ARN for iam:PassRole"
  default     = ""
}
