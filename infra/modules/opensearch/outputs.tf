output "collection_arn" {
  description = "ARN of OpenSearch Serverless collection"
  value       = aws_opensearchserverless_collection.kb.arn
}

output "collection_id" {
  description = "ID of OpenSearch Serverless collection"
  value       = aws_opensearchserverless_collection.kb.id
}

output "collection_endpoint" {
  description = "Endpoint of OpenSearch Serverless collection"
  value       = aws_opensearchserverless_collection.kb.collection_endpoint
}

output "dashboard_endpoint" {
  description = "Dashboard endpoint of OpenSearch Serverless collection"
  value       = aws_opensearchserverless_collection.kb.dashboard_endpoint
}
