# Development Guide

This guide covers setup, development workflows, and key architectural patterns for the Agentic AI Platform.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Project Structure](#project-structure)
3. [Backend Development](#backend-development)
4. [Frontend Development](#frontend-development)
5. [MCP Server Development](#mcp-server-development)
6. [Configuration & Environment](#configuration--environment)
7. [Utility Scripts](#utility-scripts)
8. [Database Setup](#database-setup)
9. [Common Workflows](#common-workflows)
10. [Troubleshooting](#troubleshooting)

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- AWS CLI configured
- pnpm (Node package manager)
- Docker (for MCP server development and testing)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd agentic-ai-platform

# Install dependencies
pnpm install

# Optional: Install Python backend dependencies
cd apps/backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ../..
```

### Run Development Servers

```bash
# Run all services (frontend + backend)
pnpm dev

# Or run individually:
# Terminal 1: Backend
cd apps/backend
SKIP_AUTH=true ENV_MODE=development uvicorn app.main:app --reload

# Terminal 2: Frontend
cd apps/frontend
pnpm dev
```

The frontend runs on `http://localhost:5173` and proxies API requests to the backend at `http://localhost:8000`.

## Project Structure

```
agentic-ai-platform/
├── apps/
│   ├── backend/                    # FastAPI Python 3.11 service
│   │   ├── app/
│   │   │   ├── agent/              # Agent domain (DDD)
│   │   │   ├── mcp/                # MCP registry domain
│   │   │   ├── knowledge_bases/    # Knowledge base domain
│   │   │   ├── playground/         # Agent playground domain
│   │   │   ├── dashboard/          # Dashboard domain
│   │   │   ├── main.py             # FastAPI entry point
│   │   │   └── config.py           # Settings management
│   │   └── requirements.txt
│   └── frontend/                   # React 19 + TypeScript, Vite
│       ├── src/
│       │   ├── pages/              # React pages/routes
│       │   ├── components/         # Reusable components
│       │   ├── hooks/              # Custom React hooks
│       │   ├── stores/             # Zustand state stores
│       │   └── main.tsx            # React entry point
│       └── vite.config.ts
├── packages/                       # Shared code
│   ├── api-client/                 # Axios HTTP client
│   ├── shared-types/               # TypeScript types (auto-generated)
│   ├── shared-constants/           # Constants
│   └── shared-utils/               # Utilities
├── infra/                          # Terraform infrastructure
├── scripts/                        # Automation scripts
├── docs/                           # Documentation
└── package.json / pnpm-workspace.yaml
```

Note: MCP servers are developed and deployed independently via the platform's MCP Registry, not included in this repository.

## Backend Development

### Architecture Pattern: Domain-Driven Design (DDD)

Each domain follows this structure:

```
domain_name/
├── domain/                # Core business logic
│   ├── entities/          # Domain entities (e.g., Agent, MCP)
│   ├── services/          # Domain services
│   └── value_objects/     # Value objects
├── application/           # Use case orchestration
│   ├── service.py         # ApplicationService (orchestrates domain + infra)
│   └── dto/               # Data Transfer Objects
├── infrastructure/        # External integrations
│   ├── repositories/      # DynamoDB data access
│   ├── clients/           # AWS SDK clients
│   └── dynamodb_client.py # DynamoDB wrapper
├── presentation/          # API Controllers (FastAPI routers)
│   ├── controller.py      # REST endpoints
│   └── local_chat_controller.py  # Domain-specific routes
├── dto/                   # Request/Response DTOs
├── exception/             # Domain-specific exceptions
└── tests/                 # Unit & integration tests
```

### Domains in the Platform

| Domain | Purpose | Key Classes |
|--------|---------|-------------|
| **agent** | AI agent management | Agent, AgentVersion, AgentConfig |
| **mcp** | MCP server registry & deployment | MCPServer, MCPTool, MCPDeployment |
| **knowledge_bases** | RAG via Bedrock KB | KnowledgeBase, KBDocument |
| **playground** | Agent interaction/testing | AgentSession, PlaygroundMessage |
| **dashboard** | Analytics & monitoring | DashboardMetrics, SystemStats |

### Adding a New Domain

1. Create the directory structure under `apps/backend/app/{domain_name}/`
2. Implement domain entities and services
3. Create DTOs for API contracts
4. Create a `presentation/controller.py` with FastAPI routers
5. Register the router in `apps/backend/app/main.py`:

```python
from app.new_domain.presentation import controller as new_domain_controller

app.include_router(
    new_domain_controller.router,
    prefix="/api/new-domain",
    tags=["new-domain"]
)
```

### Configuration Management

Configuration uses environment variables with a cascade approach:

```bash
# apps/backend/.env files (loaded automatically)
# Priority: .env.{ENV_MODE} > .env.local > .env

# Required env vars
AWS_REGION=us-east-1
AWS_PROFILE=your-profile  # Optional for named profiles

# Development
SKIP_AUTH=true  # Bypass Okta token validation
ENV_MODE=development

# Database
DYNAMODB_TABLE_PREFIX=dev-agentic

# Bedrock
BEDROCK_REGION=us-east-1
DEFAULT_MODEL=claude-3-5-sonnet-20241022
```

Load settings in code:

```python
from app.config import settings

# Access config
print(settings.AWS_REGION)
print(settings.DYNAMODB_TABLE_PREFIX)
```

### Key Technologies

- **FastAPI**: REST API framework with async support
- **Pydantic**: Data validation and serialization
- **boto3**: AWS SDK (synchronous, wrapped in async context)
- **DynamoDB**: Primary data store
- **Bedrock Runtime**: LLM inference
- **Strands Agents SDK**: Agent orchestration

### Running Tests

```bash
cd apps/backend

# Run all tests
pytest

# Run specific test file
pytest app/agent/tests/test_service.py

# With coverage
pytest --cov=app
```

### Accessing API Documentation

```bash
# Start the backend with SKIP_AUTH=true
SKIP_AUTH=true uvicorn app.main:app --reload

# Visit http://localhost:8000/docs for Swagger UI
# or http://localhost:8000/redoc for ReDoc
```

## Frontend Development

### Technology Stack

- **React 19**: UI framework
- **TypeScript**: Type safety
- **Vite**: Build tool (fast HMR)
- **Tailwind CSS**: Utility-first styling
- **Zustand**: State management
- **@tanstack/react-query**: Data fetching & caching
- **React Router DOM**: Client-side routing
- **Axios**: HTTP client
- **Lucide React**: Icon library
- **Recharts**: Charts and graphs

### Project Structure

```
apps/frontend/src/
├── pages/              # Page components (route-level)
├── components/         # Reusable UI components
├── hooks/              # Custom React hooks
├── stores/             # Zustand stores (global state)
├── lib/                # Utilities & helpers
└── main.tsx            # Entry point
```

### Pages

Current application pages:

| Route | Component | Purpose |
|-------|-----------|---------|
| `/` | Dashboard | Overview, analytics, metrics |
| `/mcps` | MCP Registry | View, create, manage MCP servers |
| `/agents` | Agent Management | Create, deploy, manage agents |
| `/knowledge-bases` | Knowledge Bases | Manage Bedrock knowledge bases |
| `/playground` | Agent Playground | Test agents interactively |
| `/settings` | Settings | Configuration, preferences |

### Creating a New Page

1. Create component in `src/pages/YourPage.tsx`:

```tsx
import React from 'react';
import { useYourStore } from '../stores/yourStore';

export default function YourPage() {
  const { data } = useYourStore();

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold">Your Page</h1>
      {/* Content */}
    </div>
  );
}
```

2. Add route in `src/main.tsx` or router configuration:

```tsx
import YourPage from './pages/YourPage';

const router = createBrowserRouter([
  {
    path: '/your-page',
    element: <YourPage />,
  },
]);
```

### Creating Custom Hooks

Use React Query for data fetching:

```typescript
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api-client';

export function useYourData() {
  return useQuery({
    queryKey: ['your-data'],
    queryFn: async () => {
      const { data } = await api.get('/api/your-endpoint');
      return data;
    },
  });
}
```

### API Client

Use the shared `@agentic-ai/api-client` package:

```typescript
import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '@agentic-ai/api-client';

// GET request
const { data } = useQuery({
  queryKey: ['agents'],
  queryFn: () => api.get('/api/agents'),
});

// POST request
const mutation = useMutation({
  mutationFn: (payload) => api.post('/api/agents', payload),
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ['agents'] }),
});
```

### Shared Type Definitions

TypeScript types are auto-generated from the OpenAPI schema:

```typescript
import type { Agent, AgentResponse } from '@agentic-ai/shared-types';

// Use generated types
const agent: Agent = {
  id: 'agent-123',
  name: 'My Agent',
  // ...
};
```

Run `pnpm generate-types` to regenerate types after API changes.

### Styling with Tailwind

Apply Tailwind classes directly to components:

```tsx
<button className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
  Click me
</button>
```

## MCP Server Development

Model Context Protocol (MCP) servers expose tools that agents can invoke. MCP servers are developed separately from this platform and deployed via the platform's MCP Registry. Implement using Anthropic's FastMCP SDK.

### Basic MCP Server Structure

```python
from mcp.server.fastmcp import FastMCP

# Create MCP instance (module-level, required)
mcp = FastMCP(host="0.0.0.0", port=8000, stateless_http=True)

# Register tools with @mcp.tool() decorator
@mcp.tool()
def my_tool(param: str) -> str:
    """
    Tool description for agents.

    Args:
        param: Parameter description

    Returns:
        Tool result
    """
    result = f"Processing {param}"
    return result

def main():
    # Start server with streamable-http transport
    mcp.run(transport='streamable-http')

if __name__ == '__main__':
    main()
```

### Tool Definition Rules

1. **Use type hints**: Parameters and return types must be fully typed
2. **Descriptive docstrings**: First line is the tool description, then Args/Returns
3. **Simple return types**: Return strings, dicts, or lists (JSON-serializable)
4. **Error handling**: Catch exceptions and return meaningful error messages

Example:

```python
@mcp.tool()
def describe_resource(resource_id: str, detail_level: str = "basic") -> dict:
    """
    Get detailed information about a resource.

    Args:
        resource_id: The unique identifier of the resource
        detail_level: Level of detail ('basic', 'detailed', 'full')

    Returns:
        Dictionary with resource information
    """
    try:
        # Implementation
        return {
            "id": resource_id,
            "name": "Resource Name",
            "status": "active",
        }
    except Exception as e:
        return {"error": str(e)}
```

### Key Requirements

- **Package**: Use `mcp[cli]>=1.22.0` (NOT `fastmcp` community package)
- **Transport**: Always use `transport='streamable-http'` for AgentCore Runtime
- **Host/Port**: Set `host="0.0.0.0"` and `port=8000` in FastMCP constructor
- **Stateless HTTP**: Set `stateless_http=True` for AgentCore compatibility
- **Environment Variables**: Configuration via `os.environ` (no argparse)

### Local Testing

Start the server:

```bash
cd your-mcp-server-directory
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Test with environment variables
AWS_REGION=us-east-1 python server.py
```

Test with curl in another terminal:

```bash
# Initialize (handshake)
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "id":1,
    "method":"initialize",
    "params":{
      "protocolVersion":"2024-11-05",
      "capabilities":{},
      "clientInfo":{"name":"test","version":"1.0"}
    }
  }'

# List tools
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'

# Call a tool
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "id":3,
    "method":"tools/call",
    "params":{
      "name":"my_tool",
      "arguments":{"param":"value"}
    }
  }'
```

### Building and Pushing Docker Image

```bash
cd your-mcp-server-directory

# CRITICAL: Build for arm64 (AgentCore Runtime requirement)
docker build --platform linux/arm64 -t your-mcp-server:v1 .

# Push to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <YOUR_ECR_URI>

docker tag your-mcp-server:v1 <YOUR_ECR_URI>/your-mcp-server:v1
docker push <YOUR_ECR_URI>/your-mcp-server:v1

# Verify architecture
aws ecr batch-get-image \
  --repository-name <YOUR_ECR_REPO_NAME> \
  --image-ids imageTag=v1 \
  --region us-east-1 \
  --query 'images[0].imageManifest' --output text | jq '.manifests[0].platform.architecture'
# Should output: arm64
```

Once built and pushed, register your MCP server via the platform's MCP Registry interface or API.

**Important**: Building with `--platform linux/amd64` will cause AgentCore Runtime to reject the image with "Architecture incompatible" error.

### Dockerfile Template

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Configuration
ENV PYTHONUNBUFFERED=1 \
    AWS_REGION=us-east-1

# Healthcheck
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -sf http://localhost:8000/mcp || exit 1

# Start server with streamable-http
ENTRYPOINT ["python", "-m", "your_mcp_server"]
```

## Configuration & Environment

### Environment Variables

Create or update `.env` files in `apps/backend`:

```bash
# .env (defaults)
AWS_REGION=us-east-1
DYNAMODB_TABLE_PREFIX=local

# .env.local (your local overrides, gitignored)
AWS_PROFILE=my-profile
SKIP_AUTH=true

# .env.development (development-specific)
LOG_LEVEL=DEBUG
```

Loading priority: `.env.{ENV_MODE}` > `.env.local` > `.env`

### Common Configuration

| Variable | Purpose | Example |
|----------|---------|---------|
| `AWS_REGION` | AWS region for all services | `us-east-1` |
| `AWS_PROFILE` | Named AWS profile | `my-profile` |
| `ENV_MODE` | Environment mode | `development`, `staging`, `production` |
| `SKIP_AUTH` | Bypass authentication (dev only) | `true` |
| `DYNAMODB_TABLE_PREFIX` | DynamoDB table name prefix | `dev-agentic` |
| `CORS_ORIGINS` | CORS allowed origins | `["http://localhost:5173"]` |
| `BEDROCK_REGION` | Bedrock service region | `us-east-1` |
| `DEFAULT_MODEL` | Default LLM model ID | `claude-3-5-sonnet-20241022` |

### Settings Class

Access settings in code:

```python
from app.config import settings

# Read from environment with type validation
print(settings.aws_region)        # str
print(settings.skip_auth)         # bool
print(settings.cors_origins)      # list[str]
```

Settings are validated using Pydantic, providing type safety and documentation.

## Utility Scripts

### 1. Generate TypeScript Types

```bash
pnpm generate-types

# What it does:
# 1. Starts backend with SKIP_AUTH=true
# 2. Fetches OpenAPI schema from http://localhost:8000/openapi.json
# 3. Generates TypeScript types using openapi-typescript
# 4. Outputs to packages/shared-types/src/generated.types.ts
```

**Run after API changes** to keep frontend types synchronized.

### 2. Create DynamoDB Tables

```bash
# From project root
python scripts/create_dynamodb_tables.py

# Creates tables:
# - {prefix}-mcp
# - {prefix}-agents
# - {prefix}-knowledge-bases
# - {prefix}-playground-sessions
# - {prefix}-dashboard-metrics
```

**Run once per AWS account/region** to bootstrap the database.

### 3. Build and Push MCP Server

MCP servers are built and deployed separately. Use standard Docker build commands with the `--platform linux/arm64` flag (required for AgentCore Runtime), then register via the platform's MCP Registry.

### 4. Export API Catalog

```bash
# Export API definitions to JSON
python scripts/export_api_catalog.py

# Output: api_catalog.json
```

### 5. Import API Catalog

```bash
# Import API catalog to database
python scripts/import_api_catalog.py api_catalog.json
```

## Database Setup

### DynamoDB Tables

The platform uses DynamoDB for all persistence. Tables are created automatically by `create_dynamodb_tables.py`:

```bash
python scripts/create_dynamodb_tables.py
```

**Tables created**:

| Table Name | Primary Key | Purpose |
|------------|------------|---------|
| `{prefix}-mcp` | `id` (MCP server ID) | MCP server registry |
| `{prefix}-agents` | `id` (Agent ID) | Agent definitions |
| `{prefix}-knowledge-bases` | `id` (KB ID) | Knowledge base metadata |
| `{prefix}-playground-sessions` | `id` (Session ID) | Agent test sessions |
| `{prefix}-dashboard-metrics` | `id` (Metric ID) | Metrics and analytics |

### Local Development with LocalStack

For local development without AWS credentials:

```bash
# Start LocalStack
docker-compose up -d localstack

# Set AWS credentials to dummy values
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
export AWS_ENDPOINT_URL=http://localhost:4566

# Create tables
python scripts/create_dynamodb_tables.py
```

## Common Workflows

### Adding a New API Endpoint

1. **Create DTO** in `app/domain/dto/request.py`:

```python
from pydantic import BaseModel

class CreateItemRequest(BaseModel):
    name: str
    description: str = ""
```

2. **Implement service** in `app/domain/application/service.py`:

```python
from app.domain.dto.request import CreateItemRequest

class DomainService:
    async def create_item(self, request: CreateItemRequest) -> ItemResponse:
        # Implement business logic
        pass
```

3. **Create controller** in `app/domain/presentation/controller.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from app.domain.dto.request import CreateItemRequest
from app.domain.application.service import DomainService

router = APIRouter()
service = DomainService()

@router.post("/items", response_model=ItemResponse)
async def create_item(request: CreateItemRequest):
    """Create a new item."""
    return await service.create_item(request)
```

4. **Register in main.py**:

```python
from app.domain.presentation import controller

app.include_router(
    controller.router,
    prefix="/api/domain",
    tags=["domain"]
)
```

5. **Generate types**:

```bash
pnpm generate-types
```

### Testing an Agent Integration

1. Navigate to `/playground`
2. Select agent and knowledge bases
3. Submit a query
4. View response and tool invocations in the interface

### Deploying to Production

Backend and frontend are deployed via GitLab CI/CD:

```bash
# Push to main branch for development environment
git push origin main

# Push to release/* branch for production
git push origin release/v1.0.0

# Force full rebuild (add to commit message)
git push --force-with-lease  # Include [force-deploy] in commit message
```

## Troubleshooting

### Backend Won't Start

**Error**: `ModuleNotFoundError: No module named 'app'`

**Solution**: Ensure you're in the `apps/backend` directory or add it to PYTHONPATH:

```bash
export PYTHONPATH="${PYTHONPATH}:/path/to/apps/backend"
python -m uvicorn app.main:app --reload
```

### Frontend API Calls Fail

**Error**: `ERR_CONNECTION_REFUSED` or CORS errors

**Check**:
1. Backend is running on `http://localhost:8000`
2. `CORS_ORIGINS` includes frontend URL in backend config
3. `SKIP_AUTH=true` if testing without Okta

```bash
# Backend should show
SKIP_AUTH=true ENV_MODE=development uvicorn app.main:app --reload
# Listening at http://0.0.0.0:8000
```

### DynamoDB Connection Issues

**Error**: `Unable to locate credentials` or `ValidationError`

**Solution**:
1. Verify AWS credentials: `aws sts get-caller-identity`
2. Verify table exists: `aws dynamodb list-tables`
3. Check table prefix: Confirm `DYNAMODB_TABLE_PREFIX` matches created tables

```bash
# List tables with specific prefix
aws dynamodb list-tables | jq '.TableNames[] | select(startswith("dev-agentic"))'
```

### Type Generation Fails

**Error**: `Port 8000 already in use` or `Timeout waiting for backend`

**Solution**:
1. Kill existing backend process: `lsof -i :8000 | grep -v PID | awk '{print $2}' | xargs kill`
2. Run type generation: `pnpm generate-types`

### MCP Server Deployment Rejects Image

**Error**: `ValidationException: Architecture incompatible for uri. Supported architectures: [arm64]`

**Solution**: Build with correct platform:

```bash
# WRONG (will fail)
docker build -t server:v1 .

# CORRECT
docker build --platform linux/arm64 -t server:v1 .
```

### OpenAPI Schema Not Generated

**Error**: `404 Not Found` when fetching `/openapi.json`

**Solution**:
1. Verify FastAPI app is configured with OpenAPI docs:

```python
app = FastAPI(
    openapi_url="/openapi.json",  # Must be present
    docs_url="/docs",
)
```

2. Ensure all routers are registered before starting

---

## Additional Resources

- **FastAPI Documentation**: https://fastapi.tiangolo.com
- **React Documentation**: https://react.dev
- **AWS SDK for Python**: https://boto3.amazonaws.com
- **Model Context Protocol**: https://modelcontextprotocol.io
- **Tailwind CSS**: https://tailwindcss.com
- **Zustand**: https://github.com/pmndrs/zustand
- **React Query**: https://tanstack.com/query/latest

For questions, refer to the project README or contact the development team.
