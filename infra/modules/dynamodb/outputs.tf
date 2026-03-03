output "agent_management_table_name" {
  description = "AgentManagement table name"
  value       = aws_dynamodb_table.agent_management.name
}

output "agent_management_table_arn" {
  description = "AgentManagement table ARN"
  value       = aws_dynamodb_table.agent_management.arn
}

output "kb_management_table_name" {
  description = "KnowledgeBaseManagement table name"
  value       = aws_dynamodb_table.kb_management.name
}

output "kb_management_table_arn" {
  description = "KnowledgeBaseManagement table ARN"
  value       = aws_dynamodb_table.kb_management.arn
}

output "playground_management_table_name" {
  description = "PlaygroundManagement table name"
  value       = aws_dynamodb_table.playground_management.name
}

output "playground_management_table_arn" {
  description = "PlaygroundManagement table ARN"
  value       = aws_dynamodb_table.playground_management.arn
}

output "kb_versions_table_name" {
  description = "KB Versions table name"
  value       = aws_dynamodb_table.kb_versions.name
}

output "kb_versions_table_arn" {
  description = "KB Versions table ARN"
  value       = aws_dynamodb_table.kb_versions.arn
}

output "playground_conversations_table_name" {
  description = "Playground Conversations table name"
  value       = aws_dynamodb_table.playground_conversations.name
}

output "playground_conversations_table_arn" {
  description = "Playground Conversations table ARN"
  value       = aws_dynamodb_table.playground_conversations.arn
}
