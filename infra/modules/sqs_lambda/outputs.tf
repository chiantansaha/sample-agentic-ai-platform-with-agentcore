output "sqs_queue_arn" {
  description = "ARN of SQS queue"
  value       = aws_sqs_queue.kb_creation.arn
}

output "sqs_queue_url" {
  description = "URL of SQS queue"
  value       = aws_sqs_queue.kb_creation.url
}

output "sqs_dlq_arn" {
  description = "ARN of SQS DLQ"
  value       = aws_sqs_queue.kb_creation_dlq.arn
}

output "lambda_function_arn" {
  description = "ARN of Lambda function"
  value       = aws_lambda_function.kb_creation.arn
}

output "lambda_function_name" {
  description = "Name of Lambda function"
  value       = aws_lambda_function.kb_creation.function_name
}
