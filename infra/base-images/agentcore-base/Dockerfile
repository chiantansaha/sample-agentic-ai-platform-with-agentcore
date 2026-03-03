# AgentCore Base Image
# Base image for all AgentCore Runtime deployments
# Pre-installs common dependencies to speed up agent-specific builds
#
# Build: docker buildx build --platform linux/arm64 -t agentcore-base:latest .
# Test:  docker run --platform linux/arm64 agentcore-base:latest python --version

# =============================================================================
# Using Amazon ECR Public Gallery to avoid Docker Hub rate limits
# =============================================================================
FROM --platform=linux/arm64 public.ecr.aws/docker/library/python:3.13-slim

LABEL maintainer="AWS Agentic AI Platform"
LABEL description="Base image for AgentCore Runtime agents"
LABEL version="1.0.0"

# Set working directory
WORKDIR /app

# Install system dependencies required for building Python packages
# These are commonly needed for native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install common Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Verify installation
RUN python --version && \
    pip list && \
    echo "Base image built successfully"

# Default command (will be overridden by agent-specific Dockerfile)
CMD ["python", "--version"]
