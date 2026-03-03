variable "project_name" {
  description = "프로젝트 이름"
  type        = string
}

variable "environment" {
  description = "환경 (dev, prod 등)"
  type        = string
}

variable "aws_region" {
  description = "AWS 리전"
  type        = string
}
