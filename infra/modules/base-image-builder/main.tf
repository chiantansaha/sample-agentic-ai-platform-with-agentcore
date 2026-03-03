# Base Image Builder Module
# Builds and manages custom base images for AgentCore Runtime

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

# ECR Repository for Base Image
resource "aws_ecr_repository" "base_image" {
  name                 = "${var.project_name}-agentcore-base-${var.environment}"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "KMS"
  }

  tags = {
    Name        = "${var.project_name}-agentcore-base-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }
}

# ECR Lifecycle Policy (최대 5개 이미지 유지)
resource "aws_ecr_lifecycle_policy" "base_image" {
  repository = aws_ecr_repository.base_image.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 5 images"
        selection = {
          tagStatus     = "any"
          countType     = "imageCountMoreThan"
          countNumber   = 5
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# S3 Bucket for Base Image Source Files
resource "aws_s3_bucket" "base_image_source" {
  bucket = "${var.project_name}-base-image-src-${data.aws_caller_identity.current.account_id}-${var.environment}"

  tags = {
    Name        = "${var.project_name}-base-image-src-${data.aws_caller_identity.current.account_id}-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }
}

resource "aws_s3_bucket_versioning" "base_image_source" {
  bucket = aws_s3_bucket.base_image_source.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "base_image_source" {
  bucket = aws_s3_bucket.base_image_source.id

  rule {
    id     = "delete-old-versions"
    status = "Enabled"

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }

  rule {
    id     = "delete-old-files"
    status = "Enabled"

    expiration {
      days = 90
    }
  }

  rule {
    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# IAM Role for CodeBuild
resource "aws_iam_role" "base_image_build" {
  name = "${var.project_name}-base-image-build-role-${var.environment}"

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
    Name        = "${var.project_name}-base-image-build-role-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }
}

# IAM Policy for CodeBuild
resource "aws_iam_role_policy" "base_image_build" {
  role = aws_iam_role.base_image_build.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/codebuild/${var.project_name}-base-image-builder-${var.environment}*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.base_image_source.arn,
          "${aws_s3_bucket.base_image_source.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = "*"
      }
    ]
  })
}

# CloudWatch Log Group for CodeBuild
resource "aws_cloudwatch_log_group" "base_image_build" {
  name              = "/aws/codebuild/${var.project_name}-base-image-builder-${var.environment}"
  retention_in_days = 365

  tags = {
    Name        = "${var.project_name}-base-image-builder-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }
}

# CodeBuild Project for Base Image
resource "aws_codebuild_project" "base_image" {
  name          = "${var.project_name}-base-image-builder-${var.environment}"
  description   = "Builds custom base image for AgentCore Runtime"
  build_timeout = 60
  service_role  = aws_iam_role.base_image_build.arn

  artifacts {
    type = "NO_ARTIFACTS"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                      = "aws/codebuild/standard:7.0"
    type                       = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"
    privileged_mode            = true #checkov:skip=CKV_AWS_316:Privileged mode required for Docker image builds

    environment_variable {
      name  = "AWS_DEFAULT_REGION"
      value = var.aws_region
    }

    environment_variable {
      name  = "AWS_ACCOUNT_ID"
      value = data.aws_caller_identity.current.account_id
    }

    environment_variable {
      name  = "ECR_REPOSITORY_URL"
      value = aws_ecr_repository.base_image.repository_url
    }

    environment_variable {
      name  = "IMAGE_TAG"
      value = "1.0.0"
    }
  }

  logs_config {
    cloudwatch_logs {
      group_name  = aws_cloudwatch_log_group.base_image_build.name
      stream_name = "build-log"
    }
  }

  source {
    type            = "S3"
    location        = "${aws_s3_bucket.base_image_source.bucket}/base-image/"
    buildspec       = "buildspec.yml"
  }

  tags = {
    Name        = "${var.project_name}-base-image-builder-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }
}

# ============================================================
# Auto Build Base Image (자동 빌드)
# ============================================================
# 1. 최초 배포 시 자동 빌드
# 2. 소스 파일 변경 시 자동 빌드 (Dockerfile, requirements.txt, buildspec.yml)

resource "null_resource" "build_base_image" {
  depends_on = [
    aws_codebuild_project.base_image,
    aws_s3_bucket.base_image_source
  ]

  # 소스 파일 변경 또는 ECR 리포지토리 생성 시 실행
  triggers = {
    ecr_repository_arn = aws_ecr_repository.base_image.arn
    dockerfile_hash    = filemd5("${path.module}/../../base-images/agentcore-base/Dockerfile")
    requirements_hash  = filemd5("${path.module}/../../base-images/agentcore-base/requirements.txt")
    buildspec_hash     = filemd5("${path.module}/../../base-images/agentcore-base/buildspec.yml")
  }

  provisioner "local-exec" {
    working_dir = "${path.module}/../../base-images/agentcore-base"

    command = <<-EOT
      echo "Checking if base image exists in ECR..."

      # Check if image exists in ECR
      IMAGE_EXISTS=$(aws ecr describe-images \
        --repository-name "${aws_ecr_repository.base_image.name}" \
        --region "${var.aws_region}" \
        --query 'imageDetails[?imageTags[?contains(@, `latest`)]]' \
        --output text 2>/dev/null || echo "")

      if [ -z "$IMAGE_EXISTS" ]; then
        echo "Base image not found in ECR."

        # Check if build is already in progress
        IN_PROGRESS=$(aws codebuild list-builds-for-project \
          --project-name "${aws_codebuild_project.base_image.name}" \
          --region "${var.aws_region}" \
          --query 'ids[0]' \
          --output text 2>/dev/null || echo "")

        if [ -n "$IN_PROGRESS" ] && [ "$IN_PROGRESS" != "None" ]; then
          CURRENT_STATUS=$(aws codebuild batch-get-builds \
            --ids "$IN_PROGRESS" \
            --region "${var.aws_region}" \
            --query 'builds[0].buildStatus' \
            --output text 2>/dev/null || echo "")

          if [ "$CURRENT_STATUS" = "IN_PROGRESS" ]; then
            echo "Build already in progress: $IN_PROGRESS"
            echo "Status: $CURRENT_STATUS"
            echo "Skipping new build. Check AWS Console for progress."
            exit 0
          fi
        fi

        # Upload source files to S3
        echo "Uploading source files to S3..."
        aws s3 cp . "s3://${aws_s3_bucket.base_image_source.bucket}/base-image/" --recursive

        # Start CodeBuild (비동기 - 완료 대기 안 함)
        echo "Starting CodeBuild (async)..."
        BUILD_ID=$(aws codebuild start-build \
          --project-name "${aws_codebuild_project.base_image.name}" \
          --region "${var.aws_region}" \
          --query 'build.id' \
          --output text)

        echo ""
        echo "=============================================="
        echo "  Base image build started (async)"
        echo "=============================================="
        echo "  Build ID: $BUILD_ID"
        echo "  Project:  ${aws_codebuild_project.base_image.name}"
        echo "  Region:   ${var.aws_region}"
        echo ""
        echo "  Build will complete in ~30-35 minutes."
        echo "  Check progress:"
        echo "    aws codebuild batch-get-builds --ids $BUILD_ID --region ${var.aws_region}"
        echo ""
        echo "  Or view in AWS Console:"
        echo "    https://${var.aws_region}.console.aws.amazon.com/codesuite/codebuild/projects/${aws_codebuild_project.base_image.name}/build/$BUILD_ID"
        echo "=============================================="
        exit 0
      else
        echo "Base image already exists in ECR. Skipping build."
      fi
    EOT

    interpreter = ["/bin/bash", "-c"]
  }
}
