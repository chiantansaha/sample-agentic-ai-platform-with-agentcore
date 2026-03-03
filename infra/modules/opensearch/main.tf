# OpenSearch Serverless for Knowledge Base

# Encryption Policy
resource "aws_opensearchserverless_security_policy" "encryption" {
  name = "${var.project_name}-kb-${var.environment}-enc"
  type = "encryption"

  policy = jsonencode({
    Rules = [
      {
        ResourceType = "collection"
        Resource = [
          "collection/${var.project_name}-kb-${var.environment}"
        ]
      }
    ]
    AWSOwnedKey = true
  })
}

# Network Policy
resource "aws_opensearchserverless_security_policy" "network" {
  name = "${var.project_name}-kb-${var.environment}-net"
  type = "network"

  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "collection"
          Resource = [
            "collection/${var.project_name}-kb-${var.environment}"
          ]
        },
        {
          ResourceType = "dashboard"
          Resource = [
            "collection/${var.project_name}-kb-${var.environment}"
          ]
        }
      ]
      AllowFromPublic = true
    }
  ])
}

# Collection
resource "aws_opensearchserverless_collection" "kb" {
  name = "${var.project_name}-kb-${var.environment}"
  type = "VECTORSEARCH"

  depends_on = [
    aws_opensearchserverless_security_policy.encryption,
    aws_opensearchserverless_security_policy.network
  ]

  tags = {
    Name        = "${var.project_name}-kb-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Data Access Policy
resource "aws_opensearchserverless_access_policy" "data_access" {
  name = "${var.project_name}-kb-${var.environment}-data"
  type = "data"

  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "collection"
          Resource = [
            "collection/${var.project_name}-kb-${var.environment}"
          ]
          Permission = [
            "aoss:CreateCollectionItems",
            "aoss:UpdateCollectionItems",
            "aoss:DescribeCollectionItems"
          ]
        },
        {
          ResourceType = "index"
          Resource = [
            "index/${var.project_name}-kb-${var.environment}/*"
          ]
          Permission = [
            "aoss:CreateIndex",
            "aoss:DescribeIndex",
            "aoss:ReadDocument",
            "aoss:WriteDocument",
            "aoss:UpdateIndex",
            "aoss:DeleteIndex"
          ]
        }
      ]
      Principal = concat(
        [var.bedrock_kb_role_arn],
        [var.lambda_role_arn],
        var.additional_principal_arns
      )
    }
  ])

  depends_on = [aws_opensearchserverless_collection.kb]
}
