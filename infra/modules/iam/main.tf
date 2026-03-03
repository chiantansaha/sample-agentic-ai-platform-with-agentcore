# IAM Roles for Agentic AI Platform

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Bedrock KB Role
resource "aws_iam_role" "bedrock_kb" {
  name = "${var.project_name}-bedrock-kb-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "bedrock.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-bedrock-kb-role-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

resource "aws_iam_role_policy" "bedrock_kb" {
  name = "${var.project_name}-bedrock-kb-policy-${var.environment}"
  role = aws_iam_role.bedrock_kb.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3Access"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          var.s3_bucket_arn,
          "${var.s3_bucket_arn}/*"
        ]
      },
      {
        Sid    = "OpenSearchAccess"
        Effect = "Allow"
        Action = [
          "aoss:APIAccessAll"
        ]
        Resource = var.opensearch_collection_arn
      },
      {
        Sid    = "BedrockModelAccess"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = var.embedding_model_arn
      }
    ]
  })
}

# Lambda KB Creation Role
resource "aws_iam_role" "lambda_kb_creation" {
  name = "${var.project_name}-lambda-kb-creation-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-lambda-kb-creation-role-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

#checkov:skip=CKV_AWS_290:Bedrock KB and OpenSearch operations require wildcard resources as resources are dynamically created at runtime
#checkov:skip=CKV_AWS_355:Bedrock KB and OpenSearch operations require wildcard resources as resources are dynamically created at runtime
resource "aws_iam_role_policy" "lambda_kb_creation" {
  name = "${var.project_name}-lambda-kb-creation-policy-${var.environment}"
  role = aws_iam_role.lambda_kb_creation.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SQSAccess"
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:SendMessage"
        ]
        Resource = [
          var.sqs_queue_arn,
          var.sqs_sync_queue_arn
        ]
      },
      {
        Sid    = "DynamoDBAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:UpdateItem",
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:Scan",
          "dynamodb:Query"
        ]
        Resource = [
          var.dynamodb_kb_table_arn,
          var.dynamodb_kb_version_table_arn
        ]
      },
      {
        Sid    = "BedrockAccess"
        Effect = "Allow"
        Action = [
          "bedrock:CreateKnowledgeBase",
          "bedrock:GetKnowledgeBase",
          "bedrock:CreateDataSource",
          "bedrock:GetDataSource",
          "bedrock:UpdateDataSource",
          "bedrock:StartIngestionJob",
          "bedrock:GetIngestionJob",
          "bedrock:ListIngestionJobs",
          "bedrock-agent:CreateKnowledgeBase",
          "bedrock-agent:CreateDataSource",
          "bedrock-agent:GetKnowledgeBase",
          "bedrock-agent:GetDataSource",
          "bedrock-agent:UpdateDataSource",
          "bedrock-agent:StartIngestionJob",
          "bedrock-agent:GetIngestionJob",
          "bedrock-agent:ListIngestionJobs"
        ]
        Resource = "*"
      },
      {
        Sid    = "OpenSearchAccess"
        Effect = "Allow"
        Action = [
          "aoss:CreateIndex",
          "aoss:DeleteIndex",
          "aoss:APIAccessAll"
        ]
        Resource = "*"
      },
      {
        Sid    = "IAMPassRole"
        Effect = "Allow"
        Action = [
          "iam:PassRole"
        ]
        Resource = aws_iam_role.bedrock_kb.arn
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# Attach VPC execution policy to Lambda role
resource "aws_iam_role_policy_attachment" "lambda_vpc_execution" {
  role       = aws_iam_role.lambda_kb_creation.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# ============================================================================
# Playground Runtime Role
# ============================================================================

resource "aws_iam_role" "playground_runtime" {
  name = "${var.project_name}-playground-runtime-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AssumeRolePolicy"
        Effect = "Allow"
        Principal = {
          Service = "bedrock-agentcore.amazonaws.com"
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
          ArnLike = {
            "aws:SourceArn" = "arn:aws:bedrock-agentcore:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*"
          }
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-playground-runtime-role-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

#checkov:skip=CKV_AWS_290:AgentCore runtime requires wildcard for ECR auth, CloudWatch logs, X-Ray, and AgentCore control plane operations
#checkov:skip=CKV_AWS_355:AgentCore runtime requires wildcard for ECR auth, CloudWatch logs, X-Ray, and AgentCore control plane operations
resource "aws_iam_role_policy" "playground_runtime" {
  name = "${var.project_name}-playground-runtime-policy-${var.environment}"
  role = aws_iam_role.playground_runtime.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "BedrockModelAccess"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock:Converse",
          "bedrock:ConverseStream"
        ]
        Resource = [
          "arn:aws:bedrock:*::foundation-model/*",
          "arn:aws:bedrock:*:*:inference-profile/*"
        ]
      },
      {
        Sid    = "BedrockKBAccess"
        Effect = "Allow"
        Action = [
          "bedrock:Retrieve",
          "bedrock:RetrieveAndGenerate"
        ]
        Resource = "arn:aws:bedrock:*:*:knowledge-base/*"
      },
      {
        Sid    = "S3SessionAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          var.playground_sessions_bucket_arn,
          "${var.playground_sessions_bucket_arn}/*"
        ]
      },
      {
        Sid    = "ECRAccess"
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      },
      {
        Sid    = "ECRRepositoryAccess"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:DescribeRepositories",
          "ecr:CreateRepository",
          "ecr:ListImages"
        ]
        Resource = var.playground_ecr_repository_arn != "" ? var.playground_ecr_repository_arn : "arn:aws:ecr:*:*:repository/${var.project_name}-playground-agents-${var.environment}"
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Sid    = "XRayTracing"
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords",
          "xray:GetSamplingRules",
          "xray:GetSamplingTargets",
          "xray:GetSamplingStatisticSummaries"
        ]
        Resource = "*"
      },
      {
        Sid    = "GatewayInvokeAccess"
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:InvokeGateway"
        ]
        Resource = "arn:aws:bedrock-agentcore:*:*:gateway/*"
      },
      {
        Sid    = "AgentCoreRuntimeAccess"
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:GetWorkloadAccessToken"
        ]
        Resource = "*"
      },
      {
        Sid    = "AgentCoreControlAccess"
        Effect = "Allow"
        Action = [
          "bedrock-agentcore-control:CreateAgentRuntime",
          "bedrock-agentcore-control:GetAgentRuntime",
          "bedrock-agentcore-control:UpdateAgentRuntime",
          "bedrock-agentcore-control:DeleteAgentRuntime",
          "bedrock-agentcore-control:ListAgentRuntimes"
        ]
        Resource = "*"
      }
    ]
  })
}

