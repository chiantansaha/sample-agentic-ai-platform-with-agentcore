output "ecr_repository_url" {
  description = "Base image ECR repository URL"
  value       = aws_ecr_repository.base_image.repository_url
}

output "ecr_repository_name" {
  description = "Base image ECR repository name"
  value       = aws_ecr_repository.base_image.name
}

output "ecr_repository_arn" {
  description = "Base image ECR repository ARN"
  value       = aws_ecr_repository.base_image.arn
}

output "codebuild_project_name" {
  description = "CodeBuild project name for base image"
  value       = aws_codebuild_project.base_image.name
}

output "codebuild_project_arn" {
  description = "CodeBuild project ARN for base image"
  value       = aws_codebuild_project.base_image.arn
}

output "s3_bucket_name" {
  description = "S3 bucket name for base image source"
  value       = aws_s3_bucket.base_image_source.bucket
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN for base image source"
  value       = aws_s3_bucket.base_image_source.arn
}

output "base_image_uri" {
  description = "Base image URI (latest tag)"
  value       = "${aws_ecr_repository.base_image.repository_url}:latest"
}
