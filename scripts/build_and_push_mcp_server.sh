#!/bin/bash

# Docker 이미지 빌드 및 ECR 푸시 스크립트
# Usage: ./scripts/build_and_push_mcp_server.sh [IMAGE_TAG]

set -e

# Load environment variables (only AWS and ECR related)
if [ -f "apps/backend/.env.development" ]; then
    export $(cat apps/backend/.env.development | grep -v '^#' | grep -E '^(AWS_|ECR_)' | xargs)
fi

REGION=${AWS_REGION:-us-east-1}
REPOSITORY_NAME=${ECR_REPOSITORY_NAME:-aws-agentic-ai-mcp-server-dev}
IMAGE_TAG=${1:-latest}

echo "🐳 Building and pushing MCP server Docker image..."
echo "   Region: $REGION"
echo "   Repository: $REPOSITORY_NAME"
echo "   Tag: $IMAGE_TAG"
echo ""

# ECR 로그인
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region "$REGION" | \
    docker login --username AWS --password-stdin \
    "$(aws sts get-caller-identity --query Account --output text).dkr.ecr.$REGION.amazonaws.com"

# 레포지토리 URI 조회
REPOSITORY_URI=$(aws ecr describe-repositories \
    --repository-names "$REPOSITORY_NAME" \
    --region "$REGION" \
    --query 'repositories[0].repositoryUri' \
    --output text)

echo "✅ ECR login successful"
echo ""

# Docker 이미지 빌드 (ARM64 플랫폼 - AWS AgentCore 호환)
echo "🏗️  Building Docker image for linux/arm64..."
docker build --platform linux/arm64 -t "$REPOSITORY_NAME:$IMAGE_TAG" -f Dockerfile .

echo "✅ Docker build successful"
echo ""

# 이미지 태그
echo "🏷️  Tagging image..."
docker tag "$REPOSITORY_NAME:$IMAGE_TAG" "$REPOSITORY_URI:$IMAGE_TAG"

# ECR에 푸시
echo "⬆️  Pushing image to ECR..."
docker push "$REPOSITORY_URI:$IMAGE_TAG"

echo ""
echo "✅ Successfully pushed Docker image"
echo "   Image URI: $REPOSITORY_URI:$IMAGE_TAG"
echo ""
echo "📝 Use this image in your Internal MCP deployment:"
echo "   Repository: $REPOSITORY_URI"
echo "   Tag: $IMAGE_TAG"
