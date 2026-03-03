# Getting Started - Agentic AI Platform

Welcome to the Agentic AI Platform! This guide will help you set up the development environment and start building with our platform.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Clone and Install](#clone-and-install)
3. [Environment Configuration](#environment-configuration)
4. [Running Locally](#running-locally)
5. [Infrastructure Provisioning](#infrastructure-provisioning)
6. [Local Database Setup](#local-database-setup)
7. [TypeScript Type Generation](#typescript-type-generation)
8. [Verification](#verification)
9. [Troubleshooting](#troubleshooting)
10. [Next Steps](#next-steps)

## Prerequisites

Before you begin, ensure you have the following tools installed:

### Required Tools

- **Node.js 18+**: JavaScript/TypeScript runtime
  ```bash
  node --version  # v18.0.0 or higher
  ```

- **Python 3.11+**: Backend application runtime
  ```bash
  python --version  # Python 3.11.0 or higher
  ```

- **pnpm**: Fast and efficient package manager
  ```bash
  npm install -g pnpm
  pnpm --version
  ```

- **AWS CLI v2**: AWS resource management
  ```bash
  aws --version  # aws-cli/2.x.x
  aws configure  # Configure AWS credentials
  ```

- **Terraform 1.5+**: Infrastructure provisioning
  ```bash
  terraform --version  # Terraform v1.5.0 or higher
  ```

- **Docker**: MCP server image building
  ```bash
  docker --version
  ```

- **uv**: Python package manager (for MCP servers)
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  uv --version
  ```

## Clone and Install

### Clone the Repository

```bash
# Clone from GitLab
git clone git@ssh.gitlab.aws.dev:ssminji/agentic-ai-platform.git
cd agentic-ai-platform
```

### Install Frontend and Shared Packages

Install all frontend and shared package dependencies from the project root:

```bash
pnpm install
```

This command installs:
- `apps/frontend`: React + Vite frontend application
- `packages/shared`: Shared type definitions
- `packages/eslint-config`: ESLint configuration
- `packages/typescript-config`: TypeScript configuration

### Install Backend Dependencies

Install Python dependencies for the backend:

```bash
cd apps/backend

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Environment Configuration

### Backend Environment Variables

The backend uses a multi-file environment variable cascade:

```
.env → .env.{ENV_MODE} → .env.{ENV_MODE}.local (gitignored)
```

Create a `.env.development.local` file for your local development settings:

```bash
cd apps/backend
cp .env.development .env.development.local
```

**Key Environment Variables:**

```bash
# Execution mode
ENV_MODE=development

# AWS Configuration
AWS_REGION=us-east-1
AWS_PROFILE=your-aws-profile  # AWS CLI profile name
SKIP_AUTH=true  # Skip Okta authentication for local development

# DynamoDB Tables (with -dev/-prod suffix per environment)
AGENTCORE_TASK_TABLE=agentcore-task-dev
AGENTCORE_HISTORY_TABLE=agentcore-history-dev
FLOW_TABLE=agentic-ai-flow-dev
FLOW_VERSION_TABLE=agentic-ai-flow-version-dev
MCP_SERVER_CATALOG_TABLE=mcp-server-catalog-dev
MCP_TARGET_CONFIG_TABLE=mcp-target-config-dev
USER_TABLE=agentic-ai-user-dev

# S3 Buckets
FLOW_STORAGE_BUCKET=agentic-ai-flow-storage-dev
STATIC_ASSETS_BUCKET=agentic-ai-static-assets-dev

# ECR Repository
ECR_REPOSITORY_URI=<YOUR_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/aws-agentic-ai-mcp-server-dev

# Bedrock Models
DEFAULT_MODEL_ID=us.anthropic.claude-sonnet-4-0-v1:0
CHAT_MODEL_ID=us.anthropic.claude-sonnet-4-0-v1:0

# AgentCore Resource ARNs
AGENTCORE_AGENT_ARN=arn:aws:bedrock-agentcore:us-east-1:<YOUR_ACCOUNT_ID>:agent/xxx
AGENTCORE_KNOWLEDGE_BASE_ARN=arn:aws:bedrock-agentcore:us-east-1:<YOUR_ACCOUNT_ID>:knowledge-base/xxx

# Cognito (Optional - not needed if SKIP_AUTH=true)
COGNITO_USER_POOL_ID=us-east-1_xxx
COGNITO_CLIENT_ID=xxx
```

### Frontend Environment Variables

The frontend uses `.env.development` for local development:

```bash
cd apps/frontend
# Check existing .env.development
cat .env.development
```

```bash
# API Endpoint
VITE_API_BASE_URL=http://localhost:8000
```

Vite's proxy automatically forwards `/api` requests to the backend.

## Running Locally

### Run Frontend and Backend Together (Recommended)

From the project root:

```bash
pnpm dev
```

This starts both services concurrently:
- **Backend**: `http://localhost:8000` (FastAPI)
- **Frontend**: `http://localhost:5173` (Vite)

### Run Individually

**Backend (Port 8000):**

```bash
cd apps/backend
uvicorn app.main:app --reload --port 8000
```

**Frontend (Port 5173):**

```bash
cd apps/frontend
pnpm dev
```

## Infrastructure Provisioning

To provision AWS cloud resources, use Terraform. **Note**: This step creates actual AWS resources and may incur costs.

```bash
cd infra/environments/dev

# Initialize Terraform
terraform init

# Review the execution plan
terraform plan

# Create resources
terraform apply
```

### Resources Created by Terraform

- **VPC & Networking**: Subnets, route tables, NAT gateways, security groups
- **ECS Cluster**: Container orchestration
- **Application Load Balancer (ALB)**: Traffic distribution
- **DynamoDB Tables**: NoSQL database (8 tables)
  - agentcore-task
  - agentcore-history
  - agentic-ai-flow
  - agentic-ai-flow-version
  - mcp-server-catalog
  - mcp-target-config
  - agentic-ai-user
- **S3 Buckets**: File storage (3 buckets)
  - agentic-ai-flow-storage
  - agentic-ai-static-assets
- **ECR Repositories**: Docker image registries (5 repos)
- **IAM Roles & Policies**: Access control
- **CloudWatch Log Groups**: Logging and monitoring

## Local Database Setup

To create DynamoDB tables for local testing (if not using Terraform):

```bash
# From project root
python scripts/create_dynamodb_tables.py
```

This script creates all required DynamoDB tables in the `us-east-1` region.

## TypeScript Type Generation

Generate TypeScript types automatically from the backend OpenAPI specification:

```bash
# From project root
pnpm generate-types

# Or run the script directly
bash scripts/generate-types.sh
```

Generated types are saved to `packages/shared/src/types/api.ts`.

## Verification

After completing setup, verify everything is working:

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:5173 | React frontend application |
| **Backend API** | http://localhost:8000 | FastAPI backend server |
| **API Docs (Swagger)** | http://localhost:8000/docs | Interactive API documentation |
| **ReDoc** | http://localhost:8000/redoc | Alternative API documentation |
| **Health Check** | http://localhost:8000/health | Server status verification |

### Test Health Endpoint

```bash
curl http://localhost:8000/health
# Response: {"status": "healthy"}
```

## Troubleshooting

### Port Conflicts

Check if ports 8000 and 5173 are in use:

```bash
lsof -i :8000
lsof -i :5173
```

If ports are in use, either kill the processes or modify the port numbers in your run commands.

### AWS Credentials

Verify AWS CLI is configured correctly:

```bash
aws sts get-caller-identity
```

This should return your AWS account information. If it fails, run `aws configure` to set up credentials.

### Environment Variables

Check that environment variables are loaded correctly by reviewing backend logs:

```bash
cd apps/backend
uvicorn app.main:app --reload
```

Look for environment variable loading messages in the startup logs.

### Reinstall Dependencies

If you encounter dependency issues, try a clean reinstall:

```bash
# Frontend
pnpm install --force

# Backend
cd apps/backend
pip install -r requirements.txt --force-reinstall
```

### Common Issues

**Backend won't start:**
- Verify Python version is 3.11+
- Check all environment variables are set
- Ensure AWS credentials are valid
- Check that no other service is using port 8000

**Frontend won't load:**
- Verify Node.js version is 18+
- Check pnpm is installed and updated
- Clear node_modules and reinstall: `pnpm install --force`
- Ensure `VITE_API_BASE_URL` is set correctly

**API requests fail:**
- Verify backend is running (`http://localhost:8000/health`)
- Check browser network tab for actual error responses
- Ensure CORS is configured if testing from different domain

## Next Steps

Now that your development environment is set up, explore these resources:

### Documentation

- **[Architecture Guide](./architecture.md)**: Understand system architecture and components
- **[Development Guide](./development.md)**: Learn development workflows and coding standards
- **[Deployment Guide](./deployment.md)**: Learn production deployment processes
- **[API Documentation](./api.md)**: API endpoint reference

### Development Tasks

- **MCP Server Development**: Develop and deploy MCP servers independently via the platform's MCP Registry
- **Flow Development**: Implement agent workflows using AgentCore
- **API Development**: Add new endpoints in `apps/backend/app/api/routes/`
- **UI Development**: Build React components in `apps/frontend/src/`

### Resources

- Backend API docs: http://localhost:8000/docs (when running locally)
- Repository: https://ssh.gitlab.aws.dev/ssminji/agentic-ai-platform
- Team Documentation: [Link to wiki or docs]

---

**Happy Coding!**
