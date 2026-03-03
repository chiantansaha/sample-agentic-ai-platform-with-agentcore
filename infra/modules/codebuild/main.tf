# Data sources
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

# CloudWatch Log Group for CodeBuild
resource "aws_cloudwatch_log_group" "codebuild" {
  name              = "/aws/codebuild/${var.project_name}-agent-build-${var.environment}"
  retention_in_days = 365

  tags = {
    Name        = "${var.project_name}-codebuild-logs-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# CodeBuild 프로젝트
resource "aws_codebuild_project" "agent_build" {
  name          = "${var.project_name}-agent-build-${var.environment}"
  description   = "Build Agent Docker images for AgentCore Runtime"
  service_role  = aws_iam_role.codebuild.arn
  build_timeout = 20

  artifacts {
    type = "NO_ARTIFACTS"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/standard:7.0"
    type                        = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"
    privileged_mode             = true #checkov:skip=CKV_AWS_316:Privileged mode required for Docker image builds

    environment_variable {
      name  = "AWS_DEFAULT_REGION"
      value = data.aws_region.current.name
    }

    environment_variable {
      name  = "AWS_ACCOUNT_ID"
      value = data.aws_caller_identity.current.account_id
    }

    environment_variable {
      name  = "ECR_REPOSITORY_URL"
      value = var.ecr_repository_url
    }
  }

  source {
    type      = "S3"
    location  = "${var.source_bucket_name}/agent-builds/"
    buildspec = file("${path.module}/buildspec.yml")
  }

  logs_config {
    cloudwatch_logs {
      group_name  = aws_cloudwatch_log_group.codebuild.name
      stream_name = "build-log"
    }
  }

  tags = {
    Name        = "${var.project_name}-agent-build-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }

  depends_on = [aws_cloudwatch_log_group.codebuild]
}

# IAM Role for CodeBuild
resource "aws_iam_role" "codebuild" {
  name = "${var.project_name}-codebuild-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "codebuild.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-codebuild-role-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# IAM Policy for CodeBuild
resource "aws_iam_role_policy" "codebuild" {
  role = aws_iam_role.codebuild.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CloudWatchLogsAccess"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Sid    = "S3SourceAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:ListBucket",
          "s3:PutObject"
        ]
        Resource = [
          var.source_bucket_arn,
          "${var.source_bucket_arn}/*"
        ]
      },
      {
        Sid    = "ECRGetAuthorizationToken"
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      },
      {
        Sid    = "ECRAgentRepositoryAccess"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = "arn:aws:ecr:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:repository/${var.ecr_repository_name}"
      },
      {
        Sid    = "ECRBaseImageReadAccess"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = var.base_image_ecr_arn != "" ? var.base_image_ecr_arn : "arn:aws:ecr:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:repository/*"
      },
      {
        Sid    = "BedrockAgentCoreControlPlaneAccess"
        Effect = "Allow"
        Action = [
          "bedrock-agentcore-control:CreateAgentRuntime",
          "bedrock-agentcore-control:GetAgentRuntime",
          "bedrock-agentcore-control:UpdateAgentRuntime",
          "bedrock-agentcore-control:DeleteAgentRuntime",
          "bedrock-agentcore-control:ListAgentRuntimes"
        ]
        Resource = "*"
      },
      {
        Sid    = "BedrockAgentCoreDataPlaneAccess"
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:CreateAgentRuntime",
          "bedrock-agentcore:GetAgentRuntime",
          "bedrock-agentcore:UpdateAgentRuntime",
          "bedrock-agentcore:DeleteAgentRuntime",
          "bedrock-agentcore:ListAgentRuntimes",
          "bedrock-agentcore:InvokeAgent",
          "bedrock-agentcore:*"
        ]
        Resource = "*"
      },
      {
        Sid    = "IAMPassRoleForAgentCore"
        Effect = "Allow"
        Action = [
          "iam:PassRole"
        ]
        Resource = var.agentcore_role_arn != "" ? var.agentcore_role_arn : "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/*AgentCore*"
        Condition = {
          StringEquals = {
            "iam:PassedToService" = "bedrock-agentcore.amazonaws.com"
          }
        }
      }
    ]
  })
}
