#!/bin/bash

# Multi-MCP Proxy Docker Build & Push Script
# Usage: ./apps/mcp-proxy/build_and_push.sh [IMAGE_TAG]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [ -f "$PROJECT_ROOT/apps/backend/.env.development" ]; then
    export $(cat "$PROJECT_ROOT/apps/backend/.env.development" | grep -v '^#' | grep -E '^(AWS_|ECR_)' | xargs)
fi

REGION=${AWS_REGION:-us-east-1}
REPOSITORY_NAME="aws-agentic-ai-mcp-proxy-dev"
IMAGE_TAG=${1:-latest}

echo "============================================================"
echo "Multi-MCP Proxy Docker Build & Push"
echo "============================================================"
echo "   Repository: $REPOSITORY_NAME"
echo "   Tag: $IMAGE_TAG"

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws ecr get-login-password --region "$REGION" | \
    docker login --username AWS --password-stdin \
    "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

if ! aws ecr describe-repositories --repository-names "$REPOSITORY_NAME" --region "$REGION" 2>/dev/null; then
    aws ecr create-repository \
        --repository-name "$REPOSITORY_NAME" \
        --region "$REGION" \
        --image-scanning-configuration scanOnPush=true
fi

REPOSITORY_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPOSITORY_NAME"

docker build --platform linux/arm64 -t "$REPOSITORY_NAME:$IMAGE_TAG" "$SCRIPT_DIR"
docker tag "$REPOSITORY_NAME:$IMAGE_TAG" "$REPOSITORY_URI:$IMAGE_TAG"
docker push "$REPOSITORY_URI:$IMAGE_TAG"

echo ""
echo "============================================================"
echo "Successfully pushed: $REPOSITORY_URI:$IMAGE_TAG"
echo "============================================================"
