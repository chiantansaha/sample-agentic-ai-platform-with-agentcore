output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.kb_sync_checker.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.kb_sync_checker.arn
}

output "sqs_queue_url" {
  description = "URL of the SQS queue for sync checker"
  value       = aws_sqs_queue.kb_sync_checker.url
}

output "sqs_queue_arn" {
  description = "ARN of the SQS queue for sync checker"
  value       = aws_sqs_queue.kb_sync_checker.arn
}

output "sqs_dlq_url" {
  description = "URL of the DLQ for sync checker"
  value       = aws_sqs_queue.kb_sync_dlq.url
}

output "sqs_dlq_arn" {
  description = "ARN of the DLQ for sync checker"
  value       = aws_sqs_queue.kb_sync_dlq.arn
}
