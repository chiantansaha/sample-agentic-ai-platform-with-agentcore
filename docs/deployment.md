# Agentic AI Platform - Deployment Guide

This guide covers the complete deployment architecture, CI/CD pipeline, infrastructure setup, and operational procedures for the Agentic AI Platform.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [CI/CD Pipeline](#cicd-pipeline)
- [Infrastructure as Code](#infrastructure-as-code)
- [Container Builds](#container-builds)
- [MCP Server Deployment](#mcp-server-deployment)
- [Monitoring & Observability](#monitoring--observability)
- [Manual Deployment](#manual-deployment)
- [Troubleshooting](#troubleshooting)
- [Rollback Procedures](#rollback-procedures)

---

## Overview

The Agentic AI Platform uses a modern, cloud-native deployment architecture with:

- **Git-driven deployments**: Main branch → Dev environment, Release branches → Production
- **Automated CI/CD**: GitLab CI/CD with Kaniko for container builds and ECS for orchestration
- **Infrastructure as Code**: Terraform modules for all AWS resources
- **Multi-environment support**: Dev, Staging, and Production environments
- **AWS Services**: ECS Fargate, ALB, DynamoDB, S3, ECR, OpenSearch, Lambda, SQS, and more
- **Observability**: CloudWatch Logs, Container Insights, and ADOT/OpenTelemetry

### Key Technologies

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Container Orchestration | ECS Fargate | Run frontend and backend services |
| Load Balancing | Application Load Balancer (ALB) | Distribute traffic to containers |
| CDN | CloudFront | Global content delivery |
| Database | DynamoDB | NoSQL data storage |
| Search | OpenSearch Serverless | Vector search and analytics |
| Storage | S3 | Object storage for files and artifacts |
| Image Registry | ECR | Container image storage |
| Container Builds | Kaniko | Buildkit-compatible builds in Kubernetes |
| CI/CD | GitLab CI/CD | Pipeline automation |
| Observability | CloudWatch + ADOT | Logs, metrics, and distributed tracing |

---

## Architecture

### Network Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Internet Users                       │
└────────────────────────┬────────────────────────────────┘
                         │
                    HTTPS (TLS)
                         │
        ┌────────────────▼────────────────┐
        │    CloudFront CDN               │
        │  (Custom Header Validation)     │
        └────────────────┬────────────────┘
                         │
                    HTTP (Custom Header)
                         │
        ┌────────────────▼─────────────────────────┐
        │   Application Load Balancer (ALB)        │
        │  (Port 80, returns 403 by default)       │
        └────────────────┬──────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
    ┌─────▼──┐    ┌─────▼──┐    ┌─────▼──┐
    │Frontend │    │Backend │    │ Rules  │
    │TG:80    │    │TG:8000 │    │Config  │
    └─────┬──┘    └─────┬──┘    └────────┘
          │             │
    ┌─────▼──────┬─────▼──────┐
    │             │             │
┌───▼────┐   ┌───▼────┐   ┌───▼────┐
│ ECS    │   │ ECS    │   │ ECS    │
│Task 1  │   │Task 2  │   │Task 3  │
│(Private)   │(Private)   │(Private)
└────────┘   └────────┘   └────────┘
```

### Environment Topology

| Resource | Dev | Prod |
|----------|-----|------|
| NAT Gateways | 1 (Single AZ) | Multi-AZ (High Availability) |
| ECS Tasks | 2 desired | Configurable (Auto-scaling ready) |
| DynamoDB PITR | Disabled | Enabled |
| DynamoDB Deletion Protection | Off | On |
| CloudWatch Retention | 365 days | 365 days |
| Image Scanning | Enabled | Enabled |

---

## CI/CD Pipeline

### Pipeline Stages

The GitLab CI/CD pipeline consists of three main stages:

```
Detect Changes → Build (Kaniko) → Deploy (ECS Update)
```

### Trigger Rules

- **Dev Environment**: Commits to `main` branch
- **Production Environment**: Commits to `release/*` branches
- **Force Deploy**: Add `[force-deploy]` in commit message or set `FORCE_DEPLOY=true` variable

### Stage 1: Detect Changes

**File**: `.gitlab-ci.yml` (detect-changes job)

This stage determines which services have changed and need rebuilding:

```bash
# Triggered on: main, release/*

# Outputs:
BUILD_MODE=production|development    # Based on branch
ENV_SUFFIX=prod|dev                  # Environment suffix
PROJECT_NAME=aws-agentic-ai-prod|dev # Full project name
FRONTEND_CHANGED=true|false          # Frontend changes detected
BACKEND_CHANGED=true|false           # Backend changes detected
IMAGE_TAG={short-sha}-{unix-timestamp} # Unique image tag
```

**Change Detection Logic**:
- Compares files in `apps/frontend/` for frontend changes
- Compares files in `apps/backend/` for backend changes
- Force deploy flag (`[force-deploy]` or `FORCE_DEPLOY=true`) rebuilds both

### Stage 2: Build

Two parallel build jobs use **Kaniko** for container builds:

#### Frontend Build

```yaml
build-frontend:
  image: gcr.io/kaniko-project/executor:debug
  script:
    # Builds from apps/frontend/Dockerfile
    # Destination: {ECR_REGISTRY}/aws-agentic-ai-frontend-{dev|prod}:{IMAGE_TAG}
    # Build args: BUILD_MODE
```

**Frontend Dockerfile** (`apps/frontend/Dockerfile`):
- Multi-stage build: Node.js builder → Nginx production
- Node 20 Alpine builder with pnpm
- Nginx Alpine runtime (non-root user: appuser:1001)
- Port: 8080
- Build mode: development | production

#### Backend Build

```yaml
build-backend:
  image: gcr.io/kaniko-project/executor:debug
  script:
    # Builds from apps/backend/Dockerfile
    # Destination: {ECR_REGISTRY}/aws-agentic-ai-backend-{dev|prod}:{IMAGE_TAG}
    # Build args: ENV_MODE
```

**Backend Dockerfile** (`apps/backend/Dockerfile`):
- Python 3.11 Slim base image
- Installs system dependencies (curl)
- Non-root user: appuser:1001
- Port: 8000
- Runtime: uvicorn with --reload in development

### Stage 3: Deploy

The deploy stage updates ECS with new container images:

```yaml
deploy-ecs:
  script:
    # 1. Discover ECS cluster by name pattern
    CLUSTER_NAME=aws-agentic-ai-cluster-{dev|prod}

    # 2. Get ECS service in the cluster
    # 3. Retrieve current task definition
    # 4. Update container images (frontend/backend)
    # 5. Register new task definition revision
    # 6. Update ECS service
    # 7. Wait for service to stabilize
```

**Key Features**:
- **Dynamic Discovery**: Finds cluster/service using name patterns (no hardcoding)
- **Incremental Updates**: Only updates images for changed services
- **Latest Image Fallback**: Uses latest ECR image if service unchanged
- **Sticky Sessions**: ALB uses cookies for 30-minute session persistence
- **Wait for Stability**: Blocks until ECS reports `services-stable` status

### Image Tagging Strategy

```
Format: {git-short-sha}-{unix-timestamp}

Example: a1b2c3d-1704067200

Benefits:
- Unique per commit
- Sortable by timestamp
- Traceable to git commit
- Deterministic for git-log lookup
```

### ECR Repositories

| Repository Name | Format | Purpose |
|-----------------|--------|---------|
| Frontend | `aws-agentic-ai-frontend-{env}` | React app images |
| Backend | `aws-agentic-ai-backend-{env}` | Python FastAPI images |
| MCP Servers | `aws-agentic-ai-mcp-{type}-{env}` | MCP server images |
| Playground | `aws-agentic-ai-playground-{env}` | User-generated agents |

**Repository Settings**:
- Image tag immutability: ON
- Image scanning on push: ON
- KMS encryption: ON

---

## Infrastructure as Code

### Terraform Structure

```
infra/
├── environments/
│   ├── dev/
│   │   ├── main.tf              # Main resources
│   │   ├── backend_modules.tf   # Backend-specific modules
│   │   ├── variables.tf         # Input variables
│   │   └── terraform.tfvars     # Environment-specific values
│   ├── prod/
│   │   └── ...                  # Same structure
│   └── staging/
│       └── ...                  # Same structure
└── modules/
    ├── dynamodb/                # DynamoDB tables
    ├── s3/                      # S3 buckets
    ├── ecr/                     # ECR repositories
    ├── iam/                     # IAM roles and policies
    ├── opensearch/              # OpenSearch Serverless
    ├── sqs_lambda/              # SQS + Lambda functions
    ├── eventbridge_lambda/      # EventBridge + Lambda
    ├── codebuild/               # CodeBuild projects
    ├── base-image-builder/      # Base image builder
    └── cloudfront/              # CloudFront distribution
```

### Initialization & Deployment

```bash
# 1. Initialize Terraform backend
cd infra/environments/dev
terraform init

# 2. Review planned changes
terraform plan

# 3. Apply configuration
terraform apply

# 4. Retrieve outputs
terraform output
```

### Key AWS Resources

#### VPC & Networking

- **VPC**: 10.0.0.0/16 with public and private subnets
- **Public Subnets**: 2x /24 for ALB (no public IPs)
- **Private Subnets**: 2x /24 for ECS tasks
- **NAT Gateway**: 1x in dev, Multi-AZ in prod
- **Internet Gateway**: For outbound traffic from NAT
- **Security Groups**: Restrictive - CloudFront → ALB → ECS only

#### Compute

- **ECS Cluster**: `aws-agentic-ai-cluster-{env}`
- **ECS Service**: 2 desired tasks (configurable)
- **Task Definition**: 1024 CPU / 2048 MB memory per task (Fargate compatible)
- **Launch Type**: Fargate (serverless containers)

#### Load Balancing

- **ALB**: Internal security group, CloudFront-only access
- **Target Groups**:
  - Frontend (port 80)
  - Backend (port 8000)
- **Health Checks**:
  - Frontend: GET / (200)
  - Backend: GET /health (200)
- **Custom Header**: X-Custom-Secret validation for CloudFront protection

#### Storage & Database

- **DynamoDB Tables**: 8 tables (Agent, KB, Playground, MCP, etc.)
- **S3 Buckets**: 3 buckets (KB files, Playground sessions, Agent build source)
- **OpenSearch**: Serverless for vector search
- **ECR Repositories**: 5+ repositories for containers

#### Monitoring & Observability

- **CloudWatch Log Group**: `/ecs/aws-agentic-ai`
- **Container Insights**: Enabled on ECS cluster
- **Log Retention**: 365 days
- **ADOT**: OpenTelemetry auto-instrumentation for AgentCore

#### Networking & Security

- **CloudFront Distribution**: HTTPS termination, custom header validation
- **Cognito User Pool**: OAuth for MCP authentication
- **Resource Server**: Defines scopes (read, write, invoke)
- **App Client**: Machine-to-machine credentials

### Environment Variables

Environment variables are managed in two ways:

1. **ECS Task Definition** (for containers):
   ```bash
   # DynamoDB Tables
   DYNAMODB_AGENT_TABLE
   DYNAMODB_KB_TABLE
   DYNAMODB_PLAYGROUND_TABLE
   DYNAMODB_MCP_TABLE
   # ... and more

   # S3 Buckets
   S3_KB_FILES_BUCKET
   PLAYGROUND_SESSIONS_BUCKET
   AGENT_BUILD_SOURCE_BUCKET

   # AWS Services
   AWS_REGION
   ENVIRONMENT
   ```

2. **Local Development** (`.env.development`):
   - Auto-generated by Terraform
   - Populated from module outputs
   - Located at `apps/backend/.env.development`

---

## Container Builds

### Frontend Build

**Dockerfile**: `apps/frontend/Dockerfile`

```dockerfile
# Multi-stage build pattern
# Stage 1: Node builder
FROM node:20-alpine AS builder
# - Install pnpm
# - Copy workspace files
# - Install dependencies
# - Build with specified BUILD_MODE

# Stage 2: Nginx runtime
FROM nginx:alpine
# - Create non-root user (appuser:1001)
# - Copy nginx config
# - Copy built files from builder
# - Expose port 8080
# - Run as non-root
```

**Build Command**:
```bash
docker build \
  --build-arg BUILD_MODE=production \
  -t aws-agentic-ai-frontend-dev:latest \
  apps/frontend/
```

**Nginx Configuration**:
- Serves from `/usr/share/nginx/html`
- Non-root user with /tmp/nginx for pid file
- Port 8080

### Backend Build

**Dockerfile**: `apps/backend/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

ARG ENV_MODE=development
ENV ENV_MODE=$ENV_MODE

# Install system dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user (appuser:1001)
RUN groupadd -r appgroup && useradd -r -g appgroup -u 1001 appuser
RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

**Build Command**:
```bash
docker build \
  --build-arg ENV_MODE=production \
  -t aws-agentic-ai-backend-dev:latest \
  apps/backend/
```

### Build Security

- **Non-root User**: Both containers run as non-root (appuser:1001)
- **Minimal Base Images**: python:3.11-slim, nginx:alpine
- **No Cache**: Backend builds use `--cache=false` for consistency
- **Image Scanning**: ECR scans all images on push
- **Immutable Tags**: ECR image tags are immutable

---

## MCP Server Deployment

MCP Servers are deployed as containerized services within the AgentCore Runtime. Special considerations apply for MCP deployments.

### Architecture Requirements

**CRITICAL**: MCP Servers for AgentCore Runtime must be built for **ARM64** architecture only.

```bash
# CORRECT - ARM64 (required)
docker build --platform linux/arm64 -t mcp-server:v1 .

# WRONG - AMD64 (will fail with ValidationException)
docker build --platform linux/amd64 -t mcp-server:v1 .
```

### MCP Server Dockerfile Template

**File**: `Dockerfile` (in your MCP server repository)

```dockerfile
# Multi-stage build with uv for fast dependency installation
FROM public.ecr.aws/amazonlinux/amazonlinux AS uv

# Stage 1: Build dependencies
RUN dnf install -y shadow-utils python3 python3-devel gcc
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_PREFERENCE=only-managed UV_FROZEN=true

COPY pyproject.toml uv.lock uv-requirements.txt ./
RUN python3 -m ensurepip && python3 -m pip install --require-hashes --requirement uv-requirements.txt
RUN uv sync --python 3.13 --frozen --no-install-project --no-dev --no-editable

# Stage 2: Runtime
FROM public.ecr.aws/amazonlinux/amazonlinux

ENV PATH="/app/.venv/bin:$PATH:/usr/sbin" \
    PYTHONUNBUFFERED=1 \
    MCP_TRANSPORT=streamable-http \
    FASTMCP_HOST=0.0.0.0 \
    FASTMCP_PORT=8000 \
    AWS_REGION=us-east-1 \
    # ADOT configuration
    AGENT_OBSERVABILITY_ENABLED=true \
    OTEL_PYTHON_DISTRO=aws_distro \
    OTEL_PYTHON_CONFIGURATOR=aws_configurator

RUN dnf install -y shadow-utils procps && dnf clean all
RUN groupadd --force --system app && useradd app -g app -d /app

COPY --from=uv --chown=app:app /root/.local /root/.local
COPY --from=uv --chown=app:app /app/.venv /app/.venv

USER app

EXPOSE 8000

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -sf http://localhost:8000/mcp || exit 1

ENTRYPOINT ["opentelemetry-instrument", "awslabs.eks-mcp-server"]
```

### MCP Server Dependencies

**Requirements**: `pyproject.toml`

```toml
dependencies = [
    "mcp[cli]>=1.22.0",              # MCP SDK with CLI support
    "aws-opentelemetry-distro>=0.10.1",  # ADOT for observability
    "pydantic>=2.10.6",
    "boto3>=1.34.0",
    "loguru>=0.7.0",
]
```

**IMPORTANT**: Use `mcp[cli]` package, NOT `fastmcp` package. They are different:
- `mcp.server.fastmcp.FastMCP`: Anthropic official SDK (streamable-http compatible)
- `fastmcp` package: Community package (different API, incompatible)

### MCP Server Build & Push

```bash
# 1. Build for ARM64 (REQUIRED for AgentCore Runtime)
cd your-mcp-server-directory
docker build --platform linux/arm64 -t eks-mcp-server:v4 .

# 2. Tag for ECR
docker tag eks-mcp-server:v4 \
  <YOUR_ECR_URI>:eks-mcp-server-v4

# 3. Get ECR login credentials
ECR_PASSWORD=$(aws ecr get-login-password --region us-east-1)
echo "$ECR_PASSWORD" | docker login --username AWS --password-stdin <YOUR_ECR_URI>

# 4. Push to ECR
docker push <YOUR_ECR_URI>:eks-mcp-server-v4

# 5. Verify architecture
aws ecr batch-get-image --repository-name <YOUR_ECR_REPO_NAME> \
  --image-ids imageTag=eks-mcp-server-v4 --region us-east-1 \
  --query 'images[0].imageManifest' --output text | jq -r '.manifests[0].platform.architecture'
# Output should be: arm64
```

### MCP Server Registration with AgentCore Runtime

After building and pushing, register the MCP Server as a Gateway Target:

```bash
# Create MCP Server Runtime
aws bedrock-agentcore create-agent-runtime \
  --agent-runtime-name my-mcp-runtime \
  --mcps-server-uri docker://<YOUR_ECR_URI>:eks-mcp-server-v4 \
  --region us-east-1

# Create Gateway Target (connects MCP to Agent)
aws bedrock-agentcore create-gateway-target \
  --agent-gateway-id <gateway-id> \
  --target-type mcpServer \
  --mcp-server-uri docker://<YOUR_ECR_URI>:eks-mcp-server-v4 \
  --credential-provider-type OAUTH \
  --scopes mcp-api/read mcp-api/write mcp-api/invoke \
  --region us-east-1
```

### MCP Server Tools (Example: EKS MCP Server)

The EKS MCP Server provides 16 tools:

| Tool | Purpose |
|------|---------|
| `get_cloudwatch_logs` | Retrieve CloudWatch logs |
| `get_cloudwatch_metrics` | Get CloudWatch metrics |
| `search_eks_troubleshoot_guide` | Search EKS troubleshooting |
| `manage_eks_stacks` | Manage EKS CloudFormation stacks |
| `list_k8s_resources` | List Kubernetes resources |
| `get_pod_logs` | Get Pod logs |
| `get_k8s_events` | Retrieve Kubernetes events |
| `list_api_versions` | List API versions |
| `manage_k8s_resource` | Manage K8s resources |
| `apply_yaml` | Apply YAML manifests |
| `generate_app_manifest` | Generate app manifests |
| `add_inline_policy` | Add IAM inline policy |
| `get_policies_for_role` | Get IAM role policies |
| `get_eks_metrics_guidance` | Get EKS metrics guidance |
| `get_eks_vpc_config` | Get EKS VPC config |
| `get_eks_insights` | Get EKS insights |

---

## Monitoring & Observability

### CloudWatch Logs

All containers log to CloudWatch:

**Log Group**: `/ecs/aws-agentic-ai`

**Log Streams**:
- `frontend/...` - React/Nginx frontend logs
- `backend/...` - Python FastAPI backend logs

**Retention**: 365 days

**Access**:
```bash
# View recent logs
aws logs tail /ecs/aws-agentic-ai --follow

# Search logs
aws logs filter-log-events \
  --log-group-name /ecs/aws-agentic-ai \
  --filter-pattern "ERROR"
```

### Container Insights

**Status**: Enabled on ECS cluster

**Metrics Visible**:
- CPU utilization
- Memory utilization
- Container count
- Task count

**Access**: AWS Console → CloudWatch → Container Insights

### ADOT (AWS Distro for OpenTelemetry)

**Status**: Enabled on MCP Server containers

**Configuration**:
```dockerfile
ENV AGENT_OBSERVABILITY_ENABLED=true \
    OTEL_PYTHON_DISTRO=aws_distro \
    OTEL_PYTHON_CONFIGURATOR=aws_configurator \
    OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf \
    OTEL_TRACES_EXPORTER=otlp

ENTRYPOINT ["opentelemetry-instrument", "command-to-run"]
```

**Logs Sent To**:
- CloudWatch Logs: `/aws/bedrock-agentcore/runtimes/{runtime-id}`
- CloudWatch Application Signals (APM) for Transaction Search

**Transaction Search**: AWS Console → CloudWatch → Application Signals → Transaction Search

### Health Checks

**ALB Health Checks**:

| Target Group | Path | Port | Interval | Timeout |
|--------------|------|------|----------|---------|
| Frontend | `/` | 80 | 30s | 5s |
| Backend | `/health` | 8000 | 30s | 5s |
| MCP Server | `/mcp` | 8000 | 60s | 10s |

**Healthy Threshold**: 2 consecutive successes

**Unhealthy Threshold**: 2 consecutive failures

---

## Manual Deployment

### Emergency ECS Update

If automated deployment fails or you need immediate changes:

```bash
# 1. Get current ECS cluster and service
CLUSTER_NAME="aws-agentic-ai-cluster-dev"
SERVICE_NAME="aws-agentic-ai-service-dev"

# 2. Force new deployment
aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service $SERVICE_NAME \
  --force-new-deployment \
  --region us-east-1

# 3. Monitor deployment
aws ecs describe-services \
  --cluster $CLUSTER_NAME \
  --services $SERVICE_NAME \
  --region us-east-1 \
  --query 'services[0].deployments'

# 4. Wait for stability (blocking)
aws ecs wait services-stable \
  --cluster $CLUSTER_NAME \
  --services $SERVICE_NAME \
  --region us-east-1
```

### Manual Task Definition Update

```bash
# 1. Get current task definition
TASK_DEF="aws-agentic-ai"
TASK=$(aws ecs describe-task-definition --task-definition $TASK_DEF --region us-east-1)

# 2. Create new task definition JSON (modify as needed)
NEW_TASK=$(echo "$TASK" | jq '.taskDefinition | del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .registeredAt, .registeredBy, .compatibilities)')

# 3. Update container image
NEW_TASK=$(echo "$NEW_TASK" | jq --arg IMG "my-image:tag" \
  '(.containerDefinitions[] | select(.name=="backend") | .image) = $IMG')

# 4. Register new task definition
aws ecs register-task-definition \
  --region us-east-1 \
  --cli-input-json file://new-task.json

# 5. Update service to use new task definition
aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service $SERVICE_NAME \
  --task-definition $TASK_DEF:$NEW_REVISION \
  --region us-east-1
```

### Local Container Testing

```bash
# 1. Build container
docker build -t my-app:test apps/backend/

# 2. Run container
docker run --rm -it \
  -p 8000:8000 \
  -e ENV_MODE=development \
  my-app:test

# 3. Test endpoint
curl http://localhost:8000/health
```

---

## Troubleshooting

### Common Issues

#### 1. ECR Image Not Found

**Problem**: Deploy fails with "Image not found in ECR"

**Solutions**:
```bash
# Check if repository exists
aws ecr describe-repositories --region us-east-1 | grep frontend

# List images in repository
aws ecr describe-images \
  --repository-name aws-agentic-ai-frontend-dev \
  --region us-east-1

# Check latest image tag
aws ecr describe-images \
  --repository-name aws-agentic-ai-frontend-dev \
  --query 'sort_by(imageDetails,&imagePushedAt)[-1]' \
  --region us-east-1
```

#### 2. ECS Task Not Starting

**Problem**: Tasks are stuck in PROVISIONING or PENDING

**Diagnostics**:
```bash
# Check task status
aws ecs list-tasks --cluster aws-agentic-ai-cluster-dev --region us-east-1
aws ecs describe-tasks \
  --cluster aws-agentic-ai-cluster-dev \
  --tasks <task-arn> \
  --region us-east-1

# Check CloudWatch logs
aws logs tail /ecs/aws-agentic-ai --follow

# Check container logs
docker logs <container-id>
```

**Common Causes**:
- Missing environment variables → Check task definition
- Image not found → Check ECR repositories
- Security group issues → Check ALB health check configuration
- Memory/CPU constraints → Increase task definition resources

#### 3. ALB Health Check Failing

**Problem**: Targets show "Unhealthy" in ALB

**Diagnostics**:
```bash
# Check target health
aws elbv2 describe-target-health \
  --target-group-arn <tg-arn> \
  --region us-east-1

# Check ALB logs (if configured)
# Check container logs
aws logs tail /ecs/aws-agentic-ai --follow

# Manually test health endpoint
aws ecs describe-tasks \
  --cluster aws-agentic-ai-cluster-dev \
  --tasks <task-arn> \
  --region us-east-1 \
  --query 'tasks[0].containerInstanceArn'
```

**Common Causes**:
- Application not ready → Check logs for startup errors
- Port not exposed → Verify Dockerfile EXPOSE
- Health check endpoint broken → Check GET /health handler
- Security group blocking → Verify ECS security group ingress rules

#### 4. Deployment Stuck in Rolling Update

**Problem**: Deployment hangs with old and new tasks both running

**Solutions**:
```bash
# Check service events
aws ecs describe-services \
  --cluster aws-agentic-ai-cluster-dev \
  --services aws-agentic-ai-service-dev \
  --region us-east-1 \
  --query 'services[0].events[:10]'

# Force new deployment (stops old tasks)
aws ecs update-service \
  --cluster aws-agentic-ai-cluster-dev \
  --service aws-agentic-ai-service-dev \
  --force-new-deployment \
  --region us-east-1

# Stop specific task manually
aws ecs stop-task \
  --cluster aws-agentic-ai-cluster-dev \
  --task <task-arn> \
  --reason "Manual stop for deployment" \
  --region us-east-1
```

#### 5. Image Scanning Failures

**Problem**: ECR image scan shows HIGH/CRITICAL vulnerabilities

**Resolution**:
```bash
# View scan results
aws ecr describe-images \
  --repository-name aws-agentic-ai-backend-dev \
  --region us-east-1 \
  --query 'imageDetails[0].imageScanStatus'

# Get detailed findings
aws ecr describe-image-scan-findings \
  --repository-name aws-agentic-ai-backend-dev \
  --image-id imageTag=<tag> \
  --region us-east-1

# Common fixes:
# 1. Update base image: pip install --upgrade package-name
# 2. Use newer Python version
# 3. Rebuild and rescan: docker build --no-cache ...
```

---

## Rollback Procedures

### Scenario 1: Rollback After Bad Deployment

```bash
# 1. Identify previous task definition revision
aws ecs describe-task-definition \
  --task-definition aws-agentic-ai \
  --region us-east-1 \
  --query 'taskDefinition.revision'

# 2. Update service to use previous revision
aws ecs update-service \
  --cluster aws-agentic-ai-cluster-dev \
  --service aws-agentic-ai-service-dev \
  --task-definition aws-agentic-ai:123 \
  --region us-east-1

# 3. Monitor rollback
aws ecs describe-services \
  --cluster aws-agentic-ai-cluster-dev \
  --services aws-agentic-ai-service-dev \
  --region us-east-1 \
  --query 'services[0].{Status:status, DesiredCount:desiredCount, RunningCount:runningCount}'

# 4. Verify health
aws elbv2 describe-target-health \
  --target-group-arn <frontend-tg-arn> \
  --region us-east-1
```

### Scenario 2: Rollback in Git

If deployment was triggered by a bad commit:

```bash
# 1. Revert the commit
git revert <bad-commit-hash>

# 2. Push to main (for dev) or release/* (for prod)
git push origin main

# 3. GitLab CI/CD automatically triggers new deployment with previous working state
# 4. Verify deployment in GitLab Pipelines
```

### Scenario 3: Emergency Database Rollback

For data-related issues, use DynamoDB backups:

```bash
# 1. List available backups
aws dynamodb list-backups \
  --table-name aws-agentic-ai-kb-management-dev \
  --region us-east-1

# 2. Restore from backup
aws dynamodb restore-table-from-backup \
  --target-table-name aws-agentic-ai-kb-management-dev-restored \
  --backup-arn <backup-arn> \
  --region us-east-1

# 3. Verify restored data
# 4. Update application to point to restored table (if needed)
# 5. Delete original table and rename restored table
```

### Scenario 4: Container Image Rollback

If a specific ECR image causes issues:

```bash
# 1. Get previous image tag
aws ecr describe-images \
  --repository-name aws-agentic-ai-backend-dev \
  --query 'sort_by(imageDetails,&imagePushedAt)[-2].imageTags[0]' \
  --region us-east-1

# 2. Manually update task definition to use previous image
# 3. Update ECS service
aws ecs update-service \
  --cluster aws-agentic-ai-cluster-dev \
  --service aws-agentic-ai-service-dev \
  --force-new-deployment \
  --region us-east-1
```

---

## Best Practices

### Deployment

1. **Always test in dev first**: Verify changes work in development before releasing to production
2. **Use semantic versioning**: Tag releases as `release/v1.2.3` for production
3. **Review GitLab CI logs**: Check pipeline output for warnings/errors
4. **Monitor after deployment**: Watch CloudWatch logs and metrics for 10-15 minutes after deploy

### Infrastructure

1. **Plan before apply**: Always run `terraform plan` before `terraform apply`
2. **Use variables**: Never hardcode values; use `terraform.tfvars`
3. **State backup**: Regularly backup Terraform state file
4. **Document changes**: Add comments to Terraform code explaining non-obvious decisions

### Containers

1. **Scan images**: Always check ECR scan results before using in production
2. **Use non-root users**: All containers must run as non-root user
3. **Minimize layers**: Reduce Dockerfile layers to reduce image size
4. **Pin dependencies**: Use exact versions in requirements.txt/package.json, not ranges

### Security

1. **Least privilege**: IAM roles only grant permissions actually needed
2. **Secure secrets**: Use AWS Secrets Manager for sensitive data, never in environment variables
3. **Network isolation**: Private subnets for containers, ALB only accessible through CloudFront
4. **Encryption**: Enable encryption for DynamoDB, S3, EBS volumes

### Monitoring

1. **Set up alerts**: Configure CloudWatch alarms for critical metrics
2. **Log retention**: Ensure log retention is set appropriately (365 days standard)
3. **Health checks**: Regularly verify ALB health check endpoints are working
4. **Performance tracking**: Monitor CloudWatch metrics during peak traffic

---

## Additional Resources

- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest)
- [GitLab CI/CD](https://docs.gitlab.com/ee/ci/)
- [CloudWatch Monitoring](https://docs.aws.amazon.com/cloudwatch/)
- [AWS Bedrock AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/)
- [OpenTelemetry ADOT](https://aws-otel.github.io/)

---

**Last Updated**: 2024-03

For questions or issues, contact the platform team or refer to the project README.
