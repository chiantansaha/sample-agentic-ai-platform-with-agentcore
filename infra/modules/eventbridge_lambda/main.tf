# SQS + Lambda for KB Sync Status Checker
# Replaces EventBridge with SQS-based retry mechanism

# SQS Dead Letter Queue
resource "aws_sqs_queue" "kb_sync_dlq" {
  name                      = "${var.project_name}-kb-sync-dlq-${var.environment}"
  message_retention_seconds = 1209600 # 14 days
  sqs_managed_sse_enabled   = true

  tags = {
    Name        = "${var.project_name}-kb-sync-dlq-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# SQS Queue for Sync Checker
resource "aws_sqs_queue" "kb_sync_checker" {
  name                       = "${var.project_name}-kb-sync-checker-queue-${var.environment}"
  visibility_timeout_seconds = 360 # 6 minutes (Lambda timeout + buffer)
  message_retention_seconds  = 345600 # 4 days
  receive_wait_time_seconds  = 20 # Long polling
  delay_seconds              = 300 # 5 minutes delay for retry
  sqs_managed_sse_enabled    = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.kb_sync_dlq.arn
    maxReceiveCount     = 5 # 최대 5회 재시도
  })

  tags = {
    Name        = "${var.project_name}-kb-sync-checker-queue-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Lambda Function
resource "aws_lambda_function" "kb_sync_checker" {
  filename      = var.lambda_zip_path
  function_name = "${var.project_name}-kb-sync-checker-${var.environment}"
  role          = var.lambda_role_arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 360 # 6 minutes
  memory_size   = 256

  source_code_hash           = filebase64sha256(var.lambda_zip_path)
  reserved_concurrent_executions = var.reserved_concurrent_executions

  tracing_config {
    mode = "Active"
  }

  environment {
    variables = {
      DYNAMODB_KB_TABLE         = var.dynamodb_kb_table_name
      DYNAMODB_KB_VERSION_TABLE = var.dynamodb_kb_version_table_name
      KB_SYNC_QUEUE_URL         = aws_sqs_queue.kb_sync_checker.url
    }
  }

  tags = {
    Name        = "${var.project_name}-kb-sync-checker-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Lambda Event Source Mapping (SQS → Lambda)
resource "aws_lambda_event_source_mapping" "kb_sync_checker" {
  event_source_arn = aws_sqs_queue.kb_sync_checker.arn
  function_name    = aws_lambda_function.kb_sync_checker.arn
  batch_size       = 1
  enabled          = true

  # 재시도 설정
  function_response_types = ["ReportBatchItemFailures"]

  scaling_config {
    maximum_concurrency = 5 # 최대 동시 실행 수
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "kb_sync_checker" {
  name              = "/aws/lambda/${aws_lambda_function.kb_sync_checker.function_name}"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${var.project_name}-kb-sync-checker-${var.environment}-logs"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
