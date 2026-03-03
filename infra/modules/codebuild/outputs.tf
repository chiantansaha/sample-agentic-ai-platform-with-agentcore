output "codebuild_project_name" {
  description = "CodeBuild project name"
  value       = aws_codebuild_project.agent_build.name
}

output "codebuild_project_arn" {
  description = "CodeBuild project ARN"
  value       = aws_codebuild_project.agent_build.arn
}

output "codebuild_role_arn" {
  description = "CodeBuild IAM role ARN"
  value       = aws_iam_role.codebuild.arn
}
