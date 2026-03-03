variable "project_name" {
  description = "Project name prefix"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "enable_pitr" {
  description = "Enable Point-in-Time Recovery"
  type        = bool
  default     = false
}

variable "enable_deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = false
}
