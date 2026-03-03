# Staging Environment Variables

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "staging"
}

variable "aws_region" {
  description = "AWS Region"
  type        = string
  default     = "ap-northeast-2"
}

# DynamoDB Tables
variable "dynamodb_tables" {
  description = "DynamoDB table names"
  type        = map(string)
  default = {
    agent      = "staging-AgentManagement"
    kb         = "staging-KnowledgeBaseManagement"
    teamtag    = "staging-TeamTagManagement"
    playground = "staging-PlaygroundManagement"
  }
}

# ECS Configuration
variable "ecs_cluster_name" {
  description = "ECS Cluster name"
  type        = string
  default     = "agentic-staging"
}

variable "ecs_service_name" {
  description = "ECS Service name"
  type        = string
  default     = "agentic-backend-staging"
}

# Container Configuration
variable "container_cpu" {
  description = "Container CPU units"
  type        = number
  default     = 512
}

variable "container_memory" {
  description = "Container memory in MB"
  type        = number
  default     = 1024
}

# Application Configuration
variable "app_port" {
  description = "Application port"
  type        = number
  default     = 8000
}

variable "skip_auth" {
  description = "Skip authentication"
  type        = bool
  default     = false
}
