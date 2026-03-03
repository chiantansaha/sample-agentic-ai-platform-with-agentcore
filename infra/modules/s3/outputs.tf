output "bucket_name" {
  description = "S3 bucket name"
  value       = aws_s3_bucket.kb_files.id
}

output "bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.kb_files.arn
}

output "bucket_domain_name" {
  description = "S3 bucket domain name"
  value       = aws_s3_bucket.kb_files.bucket_domain_name
}

output "playground_agent_code_bucket_name" {
  description = "Playground agent code bucket name"
  value       = aws_s3_bucket.playground_agent_code.id
}

output "playground_agent_code_bucket_arn" {
  description = "Playground agent code bucket ARN"
  value       = aws_s3_bucket.playground_agent_code.arn
}

output "playground_sessions_bucket_name" {
  description = "Playground sessions bucket name"
  value       = aws_s3_bucket.playground_sessions.id
}

output "playground_sessions_bucket_arn" {
  description = "Playground sessions bucket ARN"
  value       = aws_s3_bucket.playground_sessions.arn
}

output "agent_build_source_bucket_name" {
  description = "Agent build source bucket name"
  value       = aws_s3_bucket.agent_build_source.bucket
}

output "agent_build_source_bucket_arn" {
  description = "Agent build source bucket ARN"
  value       = aws_s3_bucket.agent_build_source.arn
}
