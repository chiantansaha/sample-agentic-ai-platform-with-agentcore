# ECR Repository for Agentic AI Platform
# Playground Agent Container Images

resource "aws_ecr_repository" "playground_agents" {
  name                 = "${var.project_name}-playground-agents-${var.environment}"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "KMS"
  }

  tags = {
    Name        = "${var.project_name}-playground-agents-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Purpose     = "AgentCore Runtime Container Images"
  }
}

# Lifecycle policy to clean up old images
# Image tag format: {agent_id[:8]}-{version}-{deployment_id[:8]}
# Keep 20 images, remove old untagged images
resource "aws_ecr_lifecycle_policy" "playground_agents" {
  repository = aws_ecr_repository.playground_agents.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Remove untagged images older than 1 day"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Keep last ${var.image_retention_count} images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = var.image_retention_count
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# Repository policy for cross-account access (if needed)
resource "aws_ecr_repository_policy" "playground_agents" {
  count      = var.enable_cross_account_access ? 1 : 0
  repository = aws_ecr_repository.playground_agents.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowAgentCorePull"
        Effect = "Allow"
        Principal = {
          Service = "bedrock-agentcore.amazonaws.com"
        }
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability"
        ]
      }
    ]
  })
}

# ECR Repository for Internal MCP Server Images
resource "aws_ecr_repository" "mcp_server" {
  name                 = "${var.project_name}-mcp-server-${var.environment}"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "KMS"
  }

  tags = {
    Name        = "${var.project_name}-mcp-server-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Purpose     = "Internal MCP Server Container Images"
  }
}

# Lifecycle policy for MCP Server images
resource "aws_ecr_lifecycle_policy" "mcp_server" {
  repository = aws_ecr_repository.mcp_server.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Remove untagged images older than 1 day"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Keep last ${var.image_retention_count} images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = var.image_retention_count
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
