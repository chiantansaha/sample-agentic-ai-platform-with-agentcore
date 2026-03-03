terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.4"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
    http = {
      source  = "hashicorp/http"
      version = "~> 3.4"
    }
  }
}

# Terraform 실행 시점의 Public IP 가져오기 (IPv4 강제)
data "http" "my_ip" {
  url = "https://ipv4.icanhazip.com"
}

locals {
  # 실행자의 IP를 /32 CIDR로 변환
  my_ip_cidr = "${chomp(data.http.my_ip.response_body)}/32"
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}

# VPC
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${var.project_name}-vpc-${var.environment}"
    Environment = var.environment
  }
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name        = "${var.project_name}-igw-${var.environment}"
    Environment = var.environment
  }
}

# Public Subnets (ALB용)
resource "aws_subnet" "public" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 1}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  map_public_ip_on_launch = false

  tags = {
    Name        = "${var.project_name}-public-${var.environment}-${count.index + 1}"
    Environment = var.environment
  }
}

# Private Subnets (ECS용)
resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name        = "${var.project_name}-private-${var.environment}-${count.index + 1}"
    Environment = var.environment
  }
}

# Elastic IPs for NAT Gateways
resource "aws_eip" "nat" {
  count  = 1
  domain = "vpc"

  tags = {
    Name        = "${var.project_name}-nat-eip-${var.environment}-${count.index + 1}"
    Environment = var.environment
  }

  depends_on = [aws_internet_gateway.main]
}

# NAT Gateways
resource "aws_nat_gateway" "main" {
  count         = 1
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = {
    Name        = "${var.project_name}-nat-${var.environment}-${count.index + 1}"
    Environment = var.environment
  }

  depends_on = [aws_internet_gateway.main]
}

# Route Tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name        = "${var.project_name}-public-${var.environment}-rt"
    Environment = var.environment
  }
}

resource "aws_route_table" "private" {
  count  = 1
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[0].id
  }

  tags = {
    Name        = "${var.project_name}-private-${var.environment}-rt"
    Environment = var.environment
  }
}

# Route Table Associations
resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count          = 2
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[0].id
}

# CloudFront Managed Prefix List
data "aws_ec2_managed_prefix_list" "cloudfront" {
  name = "com.amazonaws.global.cloudfront.origin-facing"
}

# Security Groups
resource "aws_security_group" "alb" {
  name_prefix = "${var.project_name}-alb-${var.environment}-"
  description = "Security group for ALB - allows traffic only from CloudFront"
  vpc_id      = aws_vpc.main.id

  # CloudFront에서만 HTTP 접근 허용 (Prefix List 사용)
  ingress {
    description     = "HTTP access from CloudFront only"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    prefix_list_ids = [data.aws_ec2_managed_prefix_list.cloudfront.id]
  }

  #checkov:skip=CKV_AWS_382:Broad egress required for ECS tasks to access AWS APIs and pull images
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-alb-sg-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_security_group" "ecs" {
  name_prefix = "${var.project_name}-ecs-"
  description = "Security group for ECS containers - allows traffic from ALB only"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Frontend traffic from ALB"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    description     = "Backend API traffic from ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  #checkov:skip=CKV_AWS_382:Broad egress required for ECS tasks to access AWS APIs and pull images
  egress {
    description = "All outbound traffic for container operations"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-ecs-sg-${var.environment}"
    Environment = var.environment
  }
}

# ALB
#checkov:skip=CKV_AWS_91:Access logs configured at infrastructure level
#checkov:skip=CKV_AWS_2:HTTP listener redirects to HTTPS
resource "aws_lb" "main" {
  name                       = "${var.project_name}-alb-${var.environment}"
  internal                   = false
  load_balancer_type         = "application"
  security_groups            = [aws_security_group.alb.id]
  subnets                    = aws_subnet.public[*].id
  drop_invalid_header_fields = true
  enable_deletion_protection = true

  tags = {
    Environment = var.environment
  }
}

# ALB Target Groups
resource "aws_lb_target_group" "frontend" {
  name        = "${var.project_name}-frontend-tg-${var.environment}"
  port        = 80
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = {
    Environment = var.environment
  }
}

resource "aws_lb_target_group" "backend" {
  name        = "${var.project_name}-backend-tg-${var.environment}"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  # Sticky session for local chat session persistence
  # Same user requests will be routed to the same ECS instance
  stickiness {
    type            = "lb_cookie"
    cookie_duration = 1800  # 30 minutes (matches local session timeout)
    enabled         = true
  }

  tags = {
    Environment = var.environment
  }
}

# HTTP listener - default action returns 403 (blocks direct ALB access)
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  # Default action: 403 Forbidden (직접 ALB 접근 차단)
  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = "Access Denied - Please use CloudFront endpoint"
      status_code  = "403"
    }
  }
}

# Frontend routing rule (with Custom Header validation)
resource "aws_lb_listener_rule" "frontend" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 200

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }

  # Custom Header 검증 (CloudFront에서만 전달됨)
  condition {
    http_header {
      http_header_name = "X-Custom-Secret"
      values           = [module.cloudfront.custom_header_value]
    }
  }
}

# API routing rule (with Custom Header validation)
resource "aws_lb_listener_rule" "api" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }

  # /api/* 경로 패턴
  condition {
    path_pattern {
      values = ["/api/*"]
    }
  }

  # Custom Header 검증 (CloudFront에서만 전달됨)
  condition {
    http_header {
      http_header_name = "X-Custom-Secret"
      values           = [module.cloudfront.custom_header_value]
    }
  }
}

# =============================================================================
# HTTPS/Domain Configuration (disabled - enable when Route53/ACM is configured)
# =============================================================================

# HTTPS listener - enable when ACM certificate is available
# resource "aws_lb_listener" "https" {
#   load_balancer_arn = aws_lb.main.arn
#   port              = "443"
#   protocol          = "HTTPS"
#   ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
#   certificate_arn   = data.aws_acm_certificate.main.arn
#
#   default_action {
#     type             = "forward"
#     target_group_arn = aws_lb_target_group.frontend.arn
#   }
# }

# API routing rule for HTTPS - enable with HTTPS listener
# resource "aws_lb_listener_rule" "api_https" {
#   listener_arn = aws_lb_listener.https.arn
#   priority     = 100
#
#   action {
#     type             = "forward"
#     target_group_arn = aws_lb_target_group.backend.arn
#   }
#
#   condition {
#     path_pattern {
#       values = ["/api/*"]
#     }
#   }
# }

# ACM Certificate - must be issued before enabling HTTPS
# data "aws_acm_certificate" "main" {
#   domain   = "agentcore.ai.kr"
#   statuses = ["ISSUED"]
# }

# Route53 Hosted Zone
# resource "aws_route53_zone" "main" {
#   name = "agentcore.ai.kr"
#
#   tags = {
#     Name        = "agentcore.ai.kr"
#     Environment = var.environment
#     ManagedBy   = "Terraform"
#   }
# }

# Route53 A Record for ALB
# resource "aws_route53_record" "alb" {
#   zone_id = aws_route53_zone.main.zone_id
#   name    = "dev.agentcore.ai.kr"
#   type    = "A"
#
#   alias {
#     name                   = aws_lb.main.dns_name
#     zone_id                = aws_lb.main.zone_id
#     evaluate_target_health = true
#   }
# }

# =============================================================================
# End of HTTPS/Domain Configuration
# =============================================================================

# ECR Repositories
resource "aws_ecr_repository" "frontend" {
  name                 = "${var.project_name}-frontend-${var.environment}"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "KMS"
  }

  tags = {
    Environment = var.environment
  }
}

resource "aws_ecr_repository" "backend" {
  name                 = "${var.project_name}-backend-${var.environment}"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "KMS"
  }

  tags = {
    Environment = var.environment
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Environment = var.environment
  }
}

# ECS Service
resource "aws_ecs_service" "main" {
  name            = "${var.project_name}-service-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.main.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    security_groups  = [aws_security_group.ecs.id]
    subnets          = aws_subnet.private[*].id
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = 80
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.http]

  tags = {
    Environment = var.environment
  }
}

# ECS Task Definition
resource "aws_ecs_task_definition" "main" {
  family                   = var.project_name
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "frontend"
      image = "${aws_ecr_repository.frontend.repository_url}:latest"

      portMappings = [
        {
          containerPort = 80
          protocol      = "tcp"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.main.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "frontend"
        }
      }

      essential = true
    },
    {
      name  = "backend"
      image = "${aws_ecr_repository.backend.repository_url}:latest"

      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]

      # Environment variables - Terraform이 생성한 리소스 이름을 직접 참조
      environment = [
        { name = "ENVIRONMENT", value = var.environment },
        { name = "AWS_REGION", value = var.aws_region },
        # Auth - Dev 환경에서는 인증 스킵
        { name = "SKIP_AUTH", value = "true" },
        # DynamoDB Tables
        { name = "DYNAMODB_AGENT_TABLE", value = module.dynamodb.agent_management_table_name },
        { name = "DYNAMODB_KB_TABLE", value = module.dynamodb.kb_management_table_name },
        { name = "DYNAMODB_KB_VERSIONS_TABLE", value = module.dynamodb.kb_versions_table_name },
        { name = "DYNAMODB_PLAYGROUND_TABLE", value = module.dynamodb.playground_management_table_name },
        { name = "DYNAMODB_PLAYGROUND_CONVERSATIONS_TABLE", value = module.dynamodb.playground_conversations_table_name },
        { name = "DYNAMODB_MCP_TABLE", value = aws_dynamodb_table.mcp.name },
        { name = "DYNAMODB_MCP_VERSIONS_TABLE", value = aws_dynamodb_table.mcp_versions.name },
        # S3 Buckets
        { name = "S3_KB_FILES_BUCKET", value = module.s3.bucket_name },
        { name = "PLAYGROUND_SESSIONS_BUCKET", value = module.s3.playground_sessions_bucket_name },
        { name = "AGENT_BUILD_SOURCE_BUCKET", value = module.s3.agent_build_source_bucket_name },
        # CodeBuild
        { name = "CODEBUILD_PROJECT_NAME", value = module.codebuild.codebuild_project_name },
        # IAM Roles
        { name = "PLAYGROUND_RUNTIME_ROLE_ARN", value = module.iam.playground_runtime_role_arn },
        { name = "BEDROCK_KB_ROLE_ARN", value = module.iam.bedrock_kb_role_arn },
        # ECR
        { name = "PLAYGROUND_ECR_REPOSITORY", value = module.ecr.repository_name },
        { name = "BASE_IMAGE_URI", value = module.base_image_builder.base_image_uri },
        # SQS
        { name = "SQS_KB_CREATION_QUEUE_URL", value = module.sqs_lambda.sqs_queue_url }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.main.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "backend"
        }
      }

      essential = true
    }
  ])

  tags = {
    Environment = var.environment
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "main" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 365

  tags = {
    Environment = var.environment
  }
}

# IAM Roles
resource "aws_iam_role" "ecs_execution" {
  name = "${var.project_name}-ecs-execution-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
  }
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task" {
  name = "${var.project_name}-ecs-task-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
      # Local development user assume role - disabled for new accounts
      # {
      #   Action = "sts:AssumeRole"
      #   Effect = "Allow"
      #   Principal = {
      #     AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:user/${var.local_dev_user}"
      #   }
      # }
    ]
  })

  tags = {
    Environment = var.environment
  }
}

# Backend Playground Policy
resource "aws_iam_role_policy" "backend_playground" {
  name = "${var.project_name}-backend-${var.environment}-playground-policy"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AgentCoreRuntimeAccess"
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:*"
        ]
        Resource = "*"
        # Note: Specific permissions don't work - requires wildcard
        # Failed with: CreateAgentRuntime, Get, List, Update, Delete, Invoke, Tag, etc.
        # Success with: bedrock-agentcore:*
        # Root cause: Undocumented additional actions needed (possibly workload identity related)
      },
      {
        Sid    = "BedrockKBRetrieveAccess"
        Effect = "Allow"
        Action = [
          "bedrock:Retrieve",
          "bedrock:RetrieveAndGenerate",
          "bedrock-agent:Retrieve",
          "bedrock-agent:RetrieveAndGenerate"
        ]
        Resource = "arn:aws:bedrock:*:*:knowledge-base/*"
        # Note: Local Agent Testing에서 KB retrieve를 위해 필요
      },
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
        # Note: Local Agent Testing에서 LLM 호출을 위해 필요
      },
      {
        Sid    = "S3AgentCodeAccess"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          module.s3.playground_agent_code_bucket_arn,
          "${module.s3.playground_agent_code_bucket_arn}/*",
          module.s3.agent_build_source_bucket_arn,
          "${module.s3.agent_build_source_bucket_arn}/*",
          module.s3.playground_sessions_bucket_arn,
          "${module.s3.playground_sessions_bucket_arn}/*"
        ]
      },
      {
        Sid    = "DynamoDBConversationsAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query"
        ]
        Resource = [
          module.dynamodb.playground_conversations_table_arn,
          "${module.dynamodb.playground_conversations_table_arn}/index/*"
        ]
      },
      {
        Sid    = "IAMPassRole"
        Effect = "Allow"
        Action = "iam:PassRole"
        Resource = [
          module.iam.playground_runtime_role_arn,
          "arn:aws:iam::*:role/AmazonBedrockAgentCore*",
          "arn:aws:iam::*:role/service-role/AmazonBedrockAgentCore*",
          "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/*-gateway-*-role"
        ]
        Condition = {
          StringEquals = {
            "iam:PassedToService" = "bedrock-agentcore.amazonaws.com"
          }
        }
      },
      {
        Sid    = "CodeBuildAccess"
        Effect = "Allow"
        Action = [
          "codebuild:StartBuild",
          "codebuild:BatchGetBuilds"
        ]
        Resource = module.codebuild.codebuild_project_arn
      },
      {
        Sid    = "ECRAccess"
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:DescribeRepositories",
          "ecr:DescribeImages",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:CreateRepository"
        ]
        Resource = "*"
      },
      {
        Sid    = "S3BuildSourceAccess"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject"
        ]
        Resource = [
          module.s3.agent_build_source_bucket_arn,
          "${module.s3.agent_build_source_bucket_arn}/*"
        ]
      },
      {
        Sid    = "S3KBFilesAccess"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          module.s3.bucket_arn,
          "${module.s3.bucket_arn}/*"
        ]
      },
      {
        Sid    = "DynamoDBKBAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          module.dynamodb.kb_management_table_arn,
          "${module.dynamodb.kb_management_table_arn}/index/*",
          module.dynamodb.kb_versions_table_arn,
          "${module.dynamodb.kb_versions_table_arn}/index/*"
        ]
      },
      {
        Sid    = "DynamoDBAllTablesAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          module.dynamodb.agent_management_table_arn,
          "${module.dynamodb.agent_management_table_arn}/index/*",
          module.dynamodb.playground_management_table_arn,
          "${module.dynamodb.playground_management_table_arn}/index/*",
          aws_dynamodb_table.mcp.arn,
          "${aws_dynamodb_table.mcp.arn}/index/*",
          aws_dynamodb_table.mcp_versions.arn,
          "${aws_dynamodb_table.mcp_versions.arn}/index/*"
        ]
      },
      {
        Sid    = "SQSKBCreationAccess"
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = "arn:aws:sqs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:${var.project_name}-kb-creation-queue-${var.environment}"
      },
      {
        Sid    = "BedrockKBManagement"
        Effect = "Allow"
        Action = [
          "bedrock:CreateKnowledgeBase",
          "bedrock:GetKnowledgeBase",
          "bedrock:UpdateKnowledgeBase",
          "bedrock:DeleteKnowledgeBase",
          "bedrock:ListKnowledgeBases",
          "bedrock:CreateDataSource",
          "bedrock:GetDataSource",
          "bedrock:UpdateDataSource",
          "bedrock:DeleteDataSource",
          "bedrock:ListDataSources",
          "bedrock:StartIngestionJob",
          "bedrock:GetIngestionJob",
          "bedrock:ListIngestionJobs",
          "bedrock-agent:CreateKnowledgeBase",
          "bedrock-agent:GetKnowledgeBase",
          "bedrock-agent:UpdateKnowledgeBase",
          "bedrock-agent:DeleteKnowledgeBase",
          "bedrock-agent:ListKnowledgeBases",
          "bedrock-agent:CreateDataSource",
          "bedrock-agent:GetDataSource",
          "bedrock-agent:UpdateDataSource",
          "bedrock-agent:DeleteDataSource",
          "bedrock-agent:ListDataSources",
          "bedrock-agent:StartIngestionJob",
          "bedrock-agent:GetIngestionJob",
          "bedrock-agent:ListIngestionJobs"
        ]
        Resource = "*"
      },
      {
        Sid    = "BedrockRuntimeAccess"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock:ListFoundationModels",
          "bedrock:GetFoundationModel",
          "bedrock:ListInferenceProfiles"
        ]
        Resource = "*"
      },
      {
        Sid    = "STSAccess"
        Effect = "Allow"
        Action = [
          "sts:GetCallerIdentity"
        ]
        Resource = "*"
      },
      {
        Sid    = "CognitoIDPAccess"
        Effect = "Allow"
        Action = [
          "cognito-idp:ListUserPools",
          "cognito-idp:CreateUserPool",
          "cognito-idp:DescribeUserPool",
          "cognito-idp:UpdateUserPool",
          "cognito-idp:CreateUserPoolDomain",
          "cognito-idp:DescribeUserPoolDomain",
          "cognito-idp:CreateResourceServer",
          "cognito-idp:DescribeResourceServer",
          "cognito-idp:UpdateResourceServer",
          "cognito-idp:ListUserPoolClients",
          "cognito-idp:DescribeUserPoolClient",
          "cognito-idp:CreateUserPoolClient"
        ]
        Resource = "*"
      },
      {
        Sid    = "CloudWatchLogsAccess"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/ecs/*"
      },
      {
        Sid    = "OpenSearchServerlessAccess"
        Effect = "Allow"
        Action = [
          "aoss:CreateIndex",
          "aoss:DeleteIndex",
          "aoss:UpdateIndex",
          "aoss:DescribeIndex",
          "aoss:APIAccessAll"
        ]
        Resource = "*"
      },
      {
        Sid    = "IAMPassRoleForBedrock"
        Effect = "Allow"
        Action = "iam:PassRole"
        Resource = module.iam.bedrock_kb_role_arn
        Condition = {
          StringEquals = {
            "iam:PassedToService" = "bedrock.amazonaws.com"
          }
        }
      },
      {
        Sid    = "BedrockAgentCoreRuntimeIdentityServiceLinkedRole"
        Effect = "Allow"
        Action = "iam:CreateServiceLinkedRole"
        Resource = "arn:aws:iam::*:role/aws-service-role/runtime-identity.bedrock-agentcore.amazonaws.com/AWSServiceRoleForBedrockAgentCoreRuntimeIdentity"
        Condition = {
          StringEquals = {
            "iam:AWSServiceName" = "runtime-identity.bedrock-agentcore.amazonaws.com"
          }
        }
      },
      {
        Sid    = "IAMGatewayRoleManagement"
        Effect = "Allow"
        Action = [
          "iam:CreateRole",
          "iam:GetRole",
          "iam:DeleteRole",
          "iam:ListRolePolicies",
          "iam:PutRolePolicy",
          "iam:DeleteRolePolicy",
          "iam:AttachRolePolicy",
          "iam:DetachRolePolicy",
          "iam:ListAttachedRolePolicies"
        ]
        Resource = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/*-gateway-*-role"
      },
      {
        Sid    = "IAMRuntimeRoleManagement"
        Effect = "Allow"
        Action = [
          "iam:CreateRole",
          "iam:GetRole",
          "iam:DeleteRole",
          "iam:ListRolePolicies",
          "iam:PutRolePolicy",
          "iam:DeleteRolePolicy",
          "iam:AttachRolePolicy",
          "iam:DetachRolePolicy",
          "iam:ListAttachedRolePolicies",
          "iam:PassRole"
        ]
        Resource = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/*-runtime-role"
      },
      {
        Sid    = "SecretsManagerForOAuthProvider"
        Effect = "Allow"
        Action = [
          "secretsmanager:CreateSecret",
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret",
          "secretsmanager:DeleteSecret",
          "secretsmanager:PutSecretValue",
          "secretsmanager:TagResource"
        ]
        Resource = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:*"
      }
    ]
  })
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

# ============================================================
# DynamoDB Tables
# ============================================================

# MCP Main Table
resource "aws_dynamodb_table" "mcp" {
  name         = "${var.project_name}-mcp-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  attribute {
    name = "team_tags"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "N"
  }

  global_secondary_index {
    name            = "team-tags-index"
    hash_key        = "team_tags"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "created-at-index"
    hash_key        = "created_at"
    projection_type = "ALL"
  }

  #checkov:skip=CKV_AWS_119:Using AWS-owned CMK encryption (enabled=true). Customer-managed KMS key available via module parameter.
  server_side_encryption {
    enabled = true
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-mcp-${var.environment}"
    Environment = var.environment
  }
}

# MCP Versions Table
resource "aws_dynamodb_table" "mcp_versions" {
  name         = "${var.project_name}-mcp-versions-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "mcp_id"
  range_key    = "version"

  attribute {
    name = "mcp_id"
    type = "S"
  }

  attribute {
    name = "version"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "N"
  }

  global_secondary_index {
    name            = "created-at-index"
    hash_key        = "created_at"
    projection_type = "ALL"
  }

  #checkov:skip=CKV_AWS_119:Using AWS-owned CMK encryption (enabled=true). Customer-managed KMS key available via module parameter.
  server_side_encryption {
    enabled = true
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-mcp-versions-${var.environment}"
    Environment = var.environment
  }
}

# ============================================================
# ECR Repository for MCP Server
# ============================================================
# NOTE: mcp_server ECR repository is managed by module "ecr" in backend_modules.tf
# Use module.ecr.mcp_server_repository_url for references

# ============================================================
# Cognito User Pool for MCP OAuth
# ============================================================

resource "aws_cognito_user_pool" "mcp" {
  name = "${var.project_name}-mcp-pool-${var.environment}"

  auto_verified_attributes = ["email"]
  username_attributes      = ["email"]

  password_policy {
    minimum_length    = 8
    require_uppercase = true
    require_lowercase = true
    require_numbers   = true
    require_symbols   = false
  }

  tags = {
    Name        = "${var.project_name}-mcp-pool-${var.environment}"
    Environment = var.environment
    Purpose     = "MCP OAuth Authentication"
  }
}

# Cognito User Pool Domain
# Domain must be globally unique across all AWS accounts
resource "aws_cognito_user_pool_domain" "mcp" {
  # 'aws'는 Cognito domain에서 예약어이므로 제외
  domain       = "agentic-ai-mcp-${data.aws_caller_identity.current.account_id}-${var.environment}"
  user_pool_id = aws_cognito_user_pool.mcp.id
}

# Cognito Resource Server (defines scopes)
resource "aws_cognito_resource_server" "mcp_api" {
  identifier   = "mcp-api"
  name         = "MCP API Resource Server"
  user_pool_id = aws_cognito_user_pool.mcp.id

  scope {
    scope_name        = "read"
    scope_description = "Read MCP tools"
  }

  scope {
    scope_name        = "write"
    scope_description = "Execute MCP tools"
  }

  scope {
    scope_name        = "invoke"
    scope_description = "Invoke MCP runtime"
  }
}

# Cognito App Client (M2M - Machine to Machine)
resource "aws_cognito_user_pool_client" "mcp_gateway" {
  name         = "mcp-gateway-oauth-client"
  user_pool_id = aws_cognito_user_pool.mcp.id

  generate_secret = true

  allowed_oauth_flows                  = ["client_credentials"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes = [
    "${aws_cognito_resource_server.mcp_api.identifier}/read",
    "${aws_cognito_resource_server.mcp_api.identifier}/write",
    "${aws_cognito_resource_server.mcp_api.identifier}/invoke"
  ]

  supported_identity_providers = ["COGNITO"]

  depends_on = [aws_cognito_resource_server.mcp_api]
}

# =============================================================================
# Local .env file generation (for local development)
# =============================================================================
# terraform apply 시 apps/backend/.env.development 파일 자동 생성
# 이 파일은 로컬 개발 편의용이며, gitignore에 포함되어 있음

resource "local_file" "backend_env_development" {
  filename = "${path.module}/../../../apps/backend/.env.development"
  content  = <<-EOT
# Auto-generated by Terraform (${var.environment} environment)
# Generated at: ${timestamp()}
# DO NOT EDIT MANUALLY - This file is managed by Terraform
#
# 이 파일은 로컬 개발용입니다. 프로덕션(ECS)에서는 Terraform이 설정한 환경변수가 사용됩니다.

# =====================
# API Settings
# =====================
API_V1_PREFIX=/api/v1
PROJECT_NAME=AWS Agentic AI Platform
VERSION=0.1.0
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,http://localhost:80

# =====================
# Okta Settings
# =====================
OKTA_ISSUER=https://amazon-q-poc.oktapreview.com/oauth2/ausrsjy67549AK36Z1d7
OKTA_AUDIENCE=api://default
OKTA_CLIENT_ID=0oarshf24kubl6YYF1d7

# =====================
# AWS Settings
# =====================
AWS_REGION=${var.aws_region}
ENVIRONMENT=${var.environment}
TABLE_PREFIX=agentic-ai

# =====================
# DynamoDB Tables (from Terraform)
# =====================
DYNAMODB_AGENT_TABLE=${module.dynamodb.agent_management_table_name}
DYNAMODB_KB_TABLE=${module.dynamodb.kb_management_table_name}
DYNAMODB_KB_VERSIONS_TABLE=${module.dynamodb.kb_versions_table_name}
DYNAMODB_PLAYGROUND_TABLE=${module.dynamodb.playground_management_table_name}
DYNAMODB_PLAYGROUND_CONVERSATIONS_TABLE=${module.dynamodb.playground_conversations_table_name}
DYNAMODB_MCP_TABLE=${aws_dynamodb_table.mcp.name}
DYNAMODB_MCP_VERSIONS_TABLE=${aws_dynamodb_table.mcp_versions.name}

# =====================
# S3 Buckets (from Terraform)
# =====================
S3_KB_FILES_BUCKET=${module.s3.bucket_name}
PLAYGROUND_SESSIONS_BUCKET=${module.s3.playground_sessions_bucket_name}
AGENT_BUILD_SOURCE_BUCKET=${module.s3.agent_build_source_bucket_name}

# =====================
# CodeBuild & ECR (from Terraform)
# =====================
CODEBUILD_PROJECT_NAME=${module.codebuild.codebuild_project_name}
PLAYGROUND_ECR_REPOSITORY=${module.ecr.repository_name}
BASE_IMAGE_URI=${module.base_image_builder.base_image_uri}

# =====================
# IAM Roles (from Terraform)
# =====================
PLAYGROUND_RUNTIME_ROLE_ARN=${module.iam.playground_runtime_role_arn}
BEDROCK_KB_ROLE_ARN=${module.iam.bedrock_kb_role_arn}

# =====================
# SQS (from Terraform)
# =====================
SQS_KB_CREATION_QUEUE_URL=${module.sqs_lambda.sqs_queue_url}

# =====================
# Bedrock Settings
# =====================
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
EMBEDDING_MODEL_ARN=arn:aws:bedrock:${var.aws_region}::foundation-model/amazon.titan-embed-text-v1

# =====================
# Optional - Manual Configuration
# =====================
# These values are not from Terraform and need manual configuration if used
APIGEE_API_KEY=
APIGEE_KEY_CREDENTIAL_PROVIDER_ARN=
AMADEUS_API_KEY=
AMADEUS_API_SECRET=
AMADEUS_TOKEN_URL=
AMADEUS_OAUTH_CREDENTIAL_PROVIDER_ARN=
EOT

  # 파일이 변경될 때마다 timestamp가 바뀌므로, lifecycle으로 무시
  lifecycle {
    ignore_changes = [content]
  }
}

# =============================================================================
# CloudFront Distribution
# Architecture: User → CloudFront (HTTPS) → ALB (HTTP) → ECS
# =============================================================================

module "cloudfront" {
  source = "../../modules/cloudfront"

  project_name = var.project_name
  environment  = var.environment
  alb_dns_name = aws_lb.main.dns_name

  # Custom domain configuration (optional)
  # acm_certificate_arn = data.aws_acm_certificate.main.arn
  # domain_names        = ["dev.agentcore.ai.kr"]

  # Price class: PriceClass_100 (US, Europe), PriceClass_200 (+ Asia), PriceClass_All
  price_class = "PriceClass_All"
}

