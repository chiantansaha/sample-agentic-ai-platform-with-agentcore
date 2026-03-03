# SQS + Lambda for KB Creation

# SQS Dead Letter Queue
resource "aws_sqs_queue" "kb_creation_dlq" {
  name                      = "${var.project_name}-kb-creation-dlq-${var.environment}"
  message_retention_seconds = 1209600 # 14 days
  sqs_managed_sse_enabled   = true

  tags = {
    Name        = "${var.project_name}-kb-creation-dlq-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# SQS Queue
resource "aws_sqs_queue" "kb_creation" {
  name                       = "${var.project_name}-kb-creation-queue-${var.environment}"
  visibility_timeout_seconds = 360 # 6 minutes (Lambda timeout + buffer)
  message_retention_seconds  = 345600 # 4 days
  receive_wait_time_seconds  = 20 # Long polling
  delay_seconds              = 0 # No delay for faster processing
  sqs_managed_sse_enabled    = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.kb_creation_dlq.arn
    maxReceiveCount     = 3 # 최대 3회 재시도
  })

  tags = {
    Name        = "${var.project_name}-kb-creation-queue-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Lambda Layer for Dependencies
resource "aws_lambda_layer_version" "kb_dependencies" {
  filename            = var.lambda_layer_zip_path
  layer_name          = "${var.project_name}-kb-dependencies-${var.environment}"
  compatible_runtimes = ["python3.11"]
  source_code_hash    = filebase64sha256(var.lambda_layer_zip_path)

  description = "Dependencies for KB creation: opensearch-py, requests-aws4auth"
}

# Lambda Function
resource "aws_lambda_function" "kb_creation" {
  filename      = var.lambda_zip_path
  function_name = "${var.project_name}-kb-creation-handler-${var.environment}"
  role          = var.lambda_role_arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 360 # 6 minutes (index wait 1min + polling 3min + work + buffer)
  memory_size   = 512

  source_code_hash           = filebase64sha256(var.lambda_zip_path)
  reserved_concurrent_executions = var.reserved_concurrent_executions

  layers = [aws_lambda_layer_version.kb_dependencies.arn]

  tracing_config {
    mode = "Active"
  }

  environment {
    variables = {
      DYNAMODB_KB_TABLE         = var.dynamodb_kb_table_name
      DYNAMODB_KB_VERSION_TABLE = var.dynamodb_kb_version_table_name
      OPENSEARCH_ENDPOINT       = var.opensearch_endpoint
      OPENSEARCH_COLLECTION_ARN = var.opensearch_collection_arn
      KB_ROLE_ARN               = var.bedrock_kb_role_arn
      EMBEDDING_MODEL_ARN       = var.embedding_model_arn
      KB_SYNC_QUEUE_URL         = var.kb_sync_queue_url
      ENVIRONMENT               = var.environment
    }
  }

  tags = {
    Name        = "${var.project_name}-kb-creation-handler-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Lambda Event Source Mapping
resource "aws_lambda_event_source_mapping" "kb_creation" {
  event_source_arn = aws_sqs_queue.kb_creation.arn
  function_name    = aws_lambda_function.kb_creation.arn
  batch_size       = 1
  enabled          = true

  # 재시도 설정
  function_response_types = ["ReportBatchItemFailures"]
  
  scaling_config {
    maximum_concurrency = 10 # 최대 동시 실행 수
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "kb_creation" {
  name              = "/aws/lambda/${aws_lambda_function.kb_creation.function_name}"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${var.project_name}-kb-creation-logs-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
