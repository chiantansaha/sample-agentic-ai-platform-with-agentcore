# Data sources for unique bucket naming
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  # S3 bucket unique suffix: region-account_id (globally unique)
  bucket_suffix = "${data.aws_region.current.name}-${data.aws_caller_identity.current.account_id}"
}

# S3 Bucket for Knowledge Base Files

resource "aws_s3_bucket" "kb_files" {
  bucket = "${var.project_name}-kb-files-${local.bucket_suffix}-${var.environment}"

  tags = {
    Name        = "${var.project_name}-kb-files-${local.bucket_suffix}-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Purpose     = "Knowledge Base file storage"
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "kb_files" {
  bucket = aws_s3_bucket.kb_files.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable versioning
resource "aws_s3_bucket_versioning" "kb_files" {
  bucket = aws_s3_bucket.kb_files.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Enable encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "kb_files" {
  bucket = aws_s3_bucket.kb_files.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lifecycle policy
resource "aws_s3_bucket_lifecycle_configuration" "kb_files" {
  bucket = aws_s3_bucket.kb_files.id

  rule {
    id     = "delete-old-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }

  rule {
    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# Bucket policy
resource "aws_s3_bucket_policy" "kb_files" {
  bucket = aws_s3_bucket.kb_files.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowBedrockKBRole"
        Effect = "Allow"
        Principal = {
          AWS = var.bedrock_kb_role_arn
        }
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.kb_files.arn,
          "${aws_s3_bucket.kb_files.arn}/*"
        ]
      },
      {
        Sid    = "AllowLambdaRole"
        Effect = "Allow"
        Principal = {
          AWS = var.lambda_role_arn
        }
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.kb_files.arn,
          "${aws_s3_bucket.kb_files.arn}/*"
        ]
      }
      # 임시로 주석 처리 - ECS Task Role과 Local Dev User 정책
      # {
      #   Sid    = "AllowECSTaskRole"
      #   Effect = "Allow"
      #   Principal = {
      #     AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.project_name}-ecs-task-role"
      #   }
      #   Action = [
      #     "s3:GetObject",
      #     "s3:PutObject",
      #     "s3:DeleteObject",
      #     "s3:ListBucket"
      #   ]
      #   Resource = [
      #     aws_s3_bucket.kb_files.arn,
      #     "${aws_s3_bucket.kb_files.arn}/*"
      #   ]
      # },
      # {
      #   Sid    = "AllowLocalDevelopment"
      #   Effect = "Allow"
      #   Principal = {
      #     AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:user/${var.local_dev_user}"
      #   }
      #   Action = [
      #     "s3:GetObject",
      #     "s3:PutObject",
      #     "s3:DeleteObject",
      #     "s3:ListBucket"
      #   ]
      #   Resource = [
      #     aws_s3_bucket.kb_files.arn,
      #     "${aws_s3_bucket.kb_files.arn}/*"
      #   ]
      # }
    ]
  })
}

# ============================================================================
# Playground Agent Code Bucket
# ============================================================================

resource "aws_s3_bucket" "playground_agent_code" {
  # 버킷 이름 63자 제한으로 축약: playground-agent-code → pg-agent-code
  bucket = "${var.project_name}-pg-agent-code-${local.bucket_suffix}-${var.environment}"

  tags = {
    Name        = "${var.project_name}-pg-agent-code-${local.bucket_suffix}-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Purpose     = "Playground agent code storage"
  }
}

resource "aws_s3_bucket_public_access_block" "playground_agent_code" {
  bucket = aws_s3_bucket.playground_agent_code.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "playground_agent_code" {
  bucket = aws_s3_bucket.playground_agent_code.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "playground_agent_code" {
  bucket = aws_s3_bucket.playground_agent_code.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "playground_agent_code" {
  bucket = aws_s3_bucket.playground_agent_code.id

  rule {
    id     = "delete-old-code"
    status = "Enabled"

    filter {}

    expiration {
      days = 7
    }
  }

  rule {
    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# ============================================================================
# Playground Sessions Bucket
# ============================================================================

resource "aws_s3_bucket" "playground_sessions" {
  # 버킷 이름 63자 제한으로 축약: playground-sessions → pg-sessions
  bucket = "${var.project_name}-pg-sessions-${local.bucket_suffix}-${var.environment}"

  tags = {
    Name        = "${var.project_name}-pg-sessions-${local.bucket_suffix}-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Purpose     = "Playground conversation sessions storage"
  }
}

resource "aws_s3_bucket_public_access_block" "playground_sessions" {
  bucket = aws_s3_bucket.playground_sessions.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "playground_sessions" {
  bucket = aws_s3_bucket.playground_sessions.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "playground_sessions" {
  bucket = aws_s3_bucket.playground_sessions.id

  rule {
    id     = "delete-old-sessions"
    status = "Enabled"

    filter {}

    expiration {
      days = 30
    }
  }

  rule {
    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# ============================================================================
# Agent Build Source Bucket
# ============================================================================

resource "aws_s3_bucket" "agent_build_source" {
  # 버킷 이름 63자 제한으로 축약: agent-build-source → build-src
  bucket = "${var.project_name}-build-src-${local.bucket_suffix}-${var.environment}"

  tags = {
    Name        = "${var.project_name}-build-src-${local.bucket_suffix}-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Purpose     = "Agent build source code temporary storage"
  }
}

resource "aws_s3_bucket_public_access_block" "agent_build_source" {
  bucket = aws_s3_bucket.agent_build_source.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "agent_build_source" {
  bucket = aws_s3_bucket.agent_build_source.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "agent_build_source" {
  bucket = aws_s3_bucket.agent_build_source.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "agent_build_source" {
  bucket = aws_s3_bucket.agent_build_source.id

  rule {
    id     = "delete-old-builds"
    status = "Enabled"

    filter {}

    expiration {
      days = 1
    }
  }

  rule {
    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}
