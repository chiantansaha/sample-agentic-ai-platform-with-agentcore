# ECR Module Variables

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "enable_cross_account_access" {
  description = "Enable cross-account access for AgentCore"
  type        = bool
  default     = false
}

variable "image_retention_count" {
  description = "Number of images to retain in ECR"
  type        = number
  default     = 50
}
