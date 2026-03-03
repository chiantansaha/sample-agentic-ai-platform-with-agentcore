output "bedrock_kb_role_arn" {
  description = "ARN of Bedrock KB IAM role"
  value       = aws_iam_role.bedrock_kb.arn
}

output "bedrock_kb_role_name" {
  description = "Name of Bedrock KB IAM role"
  value       = aws_iam_role.bedrock_kb.name
}

output "lambda_kb_creation_role_arn" {
  description = "ARN of Lambda KB creation IAM role"
  value       = aws_iam_role.lambda_kb_creation.arn
}

output "lambda_kb_creation_role_name" {
  description = "Name of Lambda KB creation IAM role"
  value       = aws_iam_role.lambda_kb_creation.name
}

output "playground_runtime_role_arn" {
  description = "ARN of Playground Runtime IAM role"
  value       = aws_iam_role.playground_runtime.arn
}

output "playground_runtime_role_name" {
  description = "Name of Playground Runtime IAM role"
  value       = aws_iam_role.playground_runtime.name
}
