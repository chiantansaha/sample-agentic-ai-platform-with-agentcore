# Agentic AI Platform - System Architecture

## Overview

The Agentic AI Platform is a comprehensive AWS-based solution for building, deploying, and managing AI agents powered by Amazon Bedrock and Model Context Protocol (MCP). The platform combines a React frontend with a FastAPI backend to provide a unified interface for agent management, knowledge base administration, MCP server orchestration, and playground testing.

**Technology Stack:**
- Frontend: React 19 + TypeScript + Vite
- Backend: Python 3.11 + FastAPI
- Infrastructure: AWS (ECS Fargate, DynamoDB, S3, OpenSearch, Bedrock)
- Orchestration: Amazon Bedrock AgentCore, Strands Agents SDK
- Protocol: Model Context Protocol (MCP) with streamable-http transport

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Client Layer (Browser)                                │
└──────────────────────┬──────────────────────────────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │       CloudFront CDN          │
        │   (Origin: ALB/Frontend)      │
        └──────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │   Application Load Balancer    │
        │      (Multi-AZ)                │
        └──────────────────────────────┘
                       │
        ┌──────────────┬──────────────┐
        ▼              ▼              ▼
   ┌─────────┐   ┌─────────┐   ┌─────────┐
   │ Frontend │   │ Backend │   │MCP Proxy │
   │  Nginx   │   │ FastAPI │   │ FastAPI  │
   │ :8080    │   │ :8000   │   │ :5000    │
   │(React)   │   │(DDD)    │   │(Proxy)   │
   └─────────┘   └─────────┘   └─────────┘
   ECS Fargate   ECS Fargate   ECS Fargate

        ▼              ▼              ▼
┌─────────────────────────────────────────────┐
│          AWS Services Layer                  │
├─────────────────────────────────────────────┤
│ • DynamoDB (4 tables)      ▸ Agent, KB, MCP │
│ • S3 (3 buckets)           ▸ Files, Builds  │
│ • OpenSearch Serverless    ▸ Vector search  │
│ • Bedrock Agents/KB        ▸ LLM services   │
│ • Cognito                  ▸ Auth/OAuth2    │
│ • CodeBuild                ▸ Docker builds  │
│ • SQS + Lambda             ▸ Async jobs     │
│ • EventBridge + Lambda     ▸ Scheduled jobs │
│ • CloudWatch               ▸ Logging/APM    │
└─────────────────────────────────────────────┘
        ▼
┌─────────────────────────────────────────────┐
│     AWS Bedrock AgentCore Runtime           │
│     (Agent deployment & execution)          │
└─────────────────────────────────────────────┘
        ▼
┌─────────────────────────────────────────────┐
│  MCP Servers (Docker on ECR/AgentCore)      │
│  • EKS MCP Server                           │
│  • Cost Explorer MCP Server                 │
│  • AWS Network MCP Server                   │
│  • Custom MCP Servers                       │
└─────────────────────────────────────────────┘
```

---

## Domain-Driven Design (DDD) Architecture

The backend is organized using DDD principles with clear separation of concerns across four primary domains:

```
┌────────────────────────────────────────────────────────┐
│                   Presentation Layer                    │
│          (REST Controllers + Request Handlers)          │
├────────────────────────────────────────────────────────┤
│  /api/v1/agents  │  /api/v1/mcps  │  /api/v1/kbs  │   │
└────────────────────────────────────────────────────────┘
            │                │                │
    ┌───────▼─────────────────▼────────────────▼──────────┐
    │          Application Layer (Services)               │
    │  • AgentService      • MCPService    • KBService    │
    │  • LocalChatService  • PlaygroundSvc • DashboardSvc│
    └───────┬─────────────────┬────────────────┬──────────┘
            │                 │                │
    ┌───────▼──────┐  ┌───────▼──────┐  ┌────▼───────┐
    │ Agent Domain │  │ MCP Domain   │  │ KB Domain  │
    ├──────────────┤  ├──────────────┤  ├────────────┤
    │ Aggregates:  │  │ Aggregates:  │  │ Aggregates:│
    │ • Agent      │  │ • MCP        │  │ • KB       │
    │ • AgentVer   │  │ • MCPVersion │  │ • KBVer    │
    │              │  │              │  │            │
    │ Value Objs:  │  │ Value Objs:  │  │Value Objs: │
    │ • AgentId    │  │ • MCPId      │  │ • KBId     │
    │ • LLMModel   │  │ • Tool       │  │ • KBStatus │
    │ • Status     │  │ • MCPType    │  │ • SyncStat │
    └───────────────┘  └──────────────┘  └────────────┘

    ┌────────────────────────────────────────────────────┐
    │          Infrastructure Layer                      │
    │     (Repositories, Clients, External Adapters)     │
    ├────────────────────────────────────────────────────┤
    │ DynamoDB Repositories  │  AWS Clients              │
    │ • AgentRepository      │  • BedrockKBClient        │
    │ • MCPRepository        │  • OpenSearchHelper       │
    │ • KBRepository         │  • CodeBuildClient        │
    │ • VersionRepositories  │  • LambdaClient           │
    └────────────────────────────────────────────────────┘
            │
    ┌───────▼──────────────────────────────────────┐
    │       External Systems (AWS Services)        │
    │  DynamoDB  │  S3  │  ECR  │  Bedrock  │...   │
    └──────────────────────────────────────────────┘
```

### Domain Structure

```
app/
├── agent/
│   ├── domain/
│   │   ├── entities/
│   │   │   ├── agent.py              # Agent aggregate root
│   │   │   └── agent_version.py
│   │   ├── repositories/
│   │   │   ├── agent_repository.py   # Repository interface
│   │   │   └── agent_version_repository.py
│   │   ├── value_objects/
│   │   │   ├── agent_id.py
│   │   │   └── ...
│   │   └── services/
│   │       └── agent_version_service.py
│   ├── application/
│   │   ├── service.py                # Use cases
│   │   ├── mapper.py                 # DTO mapping
│   │   └── local_chat_service.py     # Local chat execution
│   ├── infrastructure/
│   │   ├── repositories/
│   │   │   ├── dynamodb_agent_repository.py    # DynamoDB impl
│   │   │   ├── mock_agent_repository.py        # Test impl
│   │   │   └── ...
│   │   ├── clients/
│   │   ├── local_agent_runner.py     # Local execution
│   │   └── ...
│   ├── presentation/
│   │   ├── controller.py             # REST endpoints
│   │   └── local_chat_controller.py
│   ├── dto/
│   │   └── response.py               # Data transfer objects
│   ├── exception/
│   │   └── exceptions.py
│   └── tests/
│       ├── unit/
│       └── integration/
│
├── mcp/                              # MCP Server Management
│   ├── domain/
│   │   ├── entities/
│   │   │   ├── mcp.py               # MCP aggregate root
│   │   │   └── ...
│   │   ├── value_objects.py         # MCPId, MCPType, Tool, etc.
│   │   └── repositories/
│   ├── application/
│   ├── infrastructure/
│   │   ├── mcp_repository_impl.py
│   │   ├── external_mcp_service.py
│   │   └── dynamodb_client.py
│   ├── presentation/
│   │   └── controller.py
│   └── tests/
│
├── knowledge_bases/                 # KB Management
│   ├── domain/
│   │   ├── entities/
│   │   │   ├── knowledge_base.py    # KB aggregate root
│   │   │   └── knowledge_base_version.py
│   │   └── value_objects/
│   │       ├── knowledge_base_file.py
│   │       ├── sync_status.py
│   │       └── version_changes.py
│   ├── application/
│   │   ├── service.py
│   │   └── mapper.py
│   ├── infrastructure/
│   │   ├── clients/
│   │   │   ├── bedrock_kb_client.py # Bedrock integration
│   │   │   └── opensearch_helper.py # OpenSearch indexing
│   │   └── repositories/
│   │       ├── dynamodb_kb_repository.py
│   │       └── dynamodb_version_repository.py
│   ├── presentation/
│   │   └── controller.py
│   └── tests/
│
├── playground/                      # Playground (Code Generation & Testing)
│   ├── domain/
│   │   ├── entities/
│   │   │   ├── conversation.py
│   │   │   ├── session.py
│   │   │   └── deployment.py
│   │   └── repositories/
│   ├── application/
│   │   └── service.py
│   ├── infrastructure/
│   │   └── repositories/
│   │       ├── dynamodb_conversation_repository.py
│   │       ├── dynamodb_session_repository.py
│   │       └── dynamodb_deployment_repository.py
│   ├── presentation/
│   │   └── controller.py
│   └── tests/
│
├── dashboard/
│   ├── controllers.py               # Dashboard statistics
│   └── ...
│
├── middleware/
│   ├── auth.py                      # Authentication/Authorization
│   └── ...
│
├── shared/
│   ├── utils/
│   │   ├── timestamp.py
│   │   └── ...
│   └── exceptions/
│
├── config.py                        # Configuration management
└── main.py                          # FastAPI entry point
```

---

## Four Core Domains

### 1. Agent Domain

Manages AI agents powered by Amazon Bedrock and Strands Agents SDK.

**Key Entities:**
- `Agent`: Aggregate root representing a single AI agent
- `AgentVersion`: Immutable version history for agents

**Value Objects:**
- `AgentId`: Unique identifier
- `LLMModel`: Enum for supported models (Claude, Nova, etc.)
- `AgentStatus`: ENABLED, DISABLED, DRAFT
- `Instruction`: Agent system prompt

**Capabilities:**
- Create/read/update/delete agents
- Version management and history
- Local execution via Strands SDK for testing
- Integration with knowledge bases and MCP servers
- Deployment to AgentCore Runtime

**Data Flow:**
```
Create Agent → DynamoDB → Serialize to Bedrock format
            ↘ Deploy to AgentCore Runtime
              ↓
         Local Chat/Testing (Optional)
              ↓
         Production Execution
```

**Repositories:**
- `DynamoDBAgentRepository`: Stores agent metadata
- `DynamoDBAgentVersionRepository`: Version history

### 2. MCP Domain

Manages Model Context Protocol servers with three deployment patterns.

**Three MCP Types:**

```
┌──────────────────────┐
│  External MCP        │
├──────────────────────┤
│ • External endpoint  │
│ • OAuth2 / No-Auth   │
│ • Manual tool config │
│ • Third-party APIs   │
└──────────────────────┘

┌──────────────────────┐
│  Internal Deploy     │
├──────────────────────┤
│ • Docker image       │
│ • ECR repository     │
│ • AgentCore Runtime  │
│ • Auto tool discovery│
└──────────────────────┘

┌──────────────────────┐
│  Internal Create     │
├──────────────────────┤
│ • OpenAPI schema     │
│ • Generate MCP tools │
│ • Docker build       │
│ • AgentCore Runtime  │
└──────────────────────┘
```

**Key Entities:**
- `MCP`: Aggregate root for MCP servers
- `MCPVersion`: Version snapshot with tool list

**Value Objects:**
- `MCPId`: Unique identifier
- `MCPType`: EXTERNAL, INTERNAL_DEPLOY, INTERNAL_CREATE
- `Tool`: MCP tool definition with input schema
- `ToolEndpoint`: Individual API endpoint
- `AuthConfig`: OAuth2 / API key configuration

**Capabilities:**
- Register external MCP endpoints
- Deploy Docker-based MCP servers to AgentCore Runtime
- Auto-generate MCP tools from OpenAPI schemas
- Tool discovery and management
- Version history and rollback

**Data Flow:**
```
External MCP:
  Register Endpoint → Validate → DynamoDB → Available

Internal Deploy:
  Docker Image (ECR) → Deploy to Runtime → Tool Discovery → DynamoDB

Internal Create:
  OpenAPI Schema → Generate Tools → Docker Build → Deploy → DynamoDB
```

**Repositories:**
- `DynamoDBMCPRepository`: MCP metadata
- `DynamoDBMCPVersionRepository`: Version history

### 3. Knowledge Base Domain

Manages Bedrock Knowledge Bases with file uploads and vector indexing.

**Key Entities:**
- `KnowledgeBase`: Aggregate root for KB instances
- `KnowledgeBaseVersion`: Version snapshots
- `KnowledgeBaseFile`: Uploaded files

**Value Objects:**
- `KBId`: Unique identifier
- `KBStatus`: ENABLED, DISABLED
- `SyncStatus`: uploaded, syncing, completed, failed
- `VersionChanges`: Track file changes per version

**Capabilities:**
- Create knowledge bases
- Upload files (PDF, TXT, DOCX, etc.)
- Automatic sync to Bedrock KB service
- Vector indexing in OpenSearch Serverless
- Version management
- File upload progress tracking

**Data Flow:**
```
Upload Files → S3 → SQS → Lambda → Bedrock KB Service
                              ↓
                        OpenSearch Indexing
                              ↓
                        Status Update (DynamoDB)
```

**Architecture:**
- Files stored in S3: `s3://kb-bucket/kb-{id}/{file}`
- Bedrock KB auto-syncs files via data source
- OpenSearch provides semantic search capability
- DynamoDB tracks sync status and versions

**Repositories:**
- `DynamoDBKBRepository`: KB metadata
- `DynamoDBVersionRepository`: Version history

### 4. Playground Domain

Interactive testing environment for agents and code generation.

**Key Entities:**
- `Session`: Chat session state
- `Conversation`: Message history
- `Deployment`: Generated code deployment

**Capabilities:**
- Create chat sessions with agents
- Send messages and receive responses
- Code generation from agent conversations
- CodeBuild integration for Docker builds
- Artifact management (generated code, test results)

**Data Flow:**
```
Chat Input → FastAPI → Bedrock Agent → Response → Store in DynamoDB
                               ↓
                        Session Management
                               ↓
                        Code Generation (Optional)
                               ↓
                        CodeBuild Trigger
                               ↓
                        Docker Build & Push to ECR
```

**Repositories:**
- `DynamoDBSessionRepository`: Session state
- `DynamoDBConversationRepository`: Message history
- `DynamoDBDeploymentRepository`: Generated artifacts

---

## Data Storage & DynamoDB Schema

### DynamoDB Tables

#### 1. Agent Management Table
- **Name**: `{project}-agent-management-{env}`
- **Hash Key**: `PK` (String)
- **Range Key**: `SK` (String)
- **Indexes**: GSI1 (by team), GSI2 (by status/date)
- **TTL**: None
- **Purpose**: Stores agents and agent versions

```
PK Format:  AGENT#{agent_id}
SK Format:  METADATA | VERSION#{version}

Attributes:
{
  PK: "AGENT#agent-123",
  SK: "METADATA",
  id: "agent-123",
  name: "Customer Service Bot",
  description: "...",
  llm_model: "claude-3-sonnet",
  instruction: "You are a helpful customer service agent",
  knowledge_bases: ["kb-1", "kb-2"],
  mcps: ["mcp-1"],
  status: "ENABLED",
  current_version: "1.0.0",
  team_tags: ["sales", "support"],
  created_at: 1704067200,
  updated_at: 1704067200,
  created_by: "user@company.com",
  updated_by: "user@company.com"
}
```

#### 2. Knowledge Base Management Table
- **Name**: `{project}-kb-management-{env}`
- **Hash Key**: `PK` (String)
- **Range Key**: `SK` (String)
- **Purpose**: Stores knowledge bases and file metadata

```
PK Format:  KB#{kb_id}
SK Format:  METADATA | FILE#{file_id}

Attributes:
{
  PK: "KB#kb-123",
  SK: "METADATA",
  id: "kb-123",
  name: "Product Documentation",
  bedrock_kb_id: "XYZABC123",
  s3_bucket: "my-kb-bucket",
  s3_prefix: "kb-123/",
  data_source_id: "DS123",
  status: "ENABLED",
  sync_status: "completed",
  current_version: 2,
  team_tags: ["product"],
  created_at: 1704067200,
  updated_at: 1704067200
}
```

#### 3. MCP Management Table
- **Name**: `{project}-mcp-management-{env}`
- **Hash Key**: `PK` (String)
- **Range Key**: `SK` (String)
- **Purpose**: Stores MCP servers and versions

```
PK Format:  MCP#{mcp_id}
SK Format:  METADATA | VERSION#{version}

Attributes:
{
  PK: "MCP#mcp-123",
  SK: "METADATA",
  id: "mcp-123",
  name: "AWS EKS MCP",
  type: "internal-deploy",
  endpoint: "mcp-eks.example.com",
  version: "1.0.0",
  status: "ENABLED",
  tool_list: [
    {
      name: "get_eks_clusters",
      description: "Get EKS clusters",
      input_schema: {...}
    }
  ],
  ecr_repository: "my-ecr/eks-mcp",
  image_tag: "v1.0.0",
  team_tags: ["devops"],
  created_at: 1704067200,
  created_by: "user@company.com"
}
```

#### 4. Playground Management Table
- **Name**: `{project}-playground-management-{env}`
- **Purpose**: Stores playground sessions, conversations, and deployments

```
PK Format:  SESSION#{session_id} | DEPLOYMENT#{deployment_id}
SK Format:  METADATA | CONVERSATION#{message_id}
```

#### 5. KB Versions Table
- **Name**: `{project}-kb-versions-{env}`
- **Hash Key**: `kb_id` (String)
- **Range Key**: `version` (Number)
- **Purpose**: Immutable version history for knowledge bases

```
Attributes:
{
  kb_id: "kb-123",
  version: 1,
  changes: {
    added: ["file1.pdf", "file2.docx"],
    removed: [],
    modified: []
  },
  sync_status: "completed",
  created_at: 1704067200,
  created_by: "user@company.com"
}
```

#### 6. Playground Conversations Table
- **Name**: `{project}-playground-conversations-{env}`
- **Hash Key**: `PK` (String)
- **Range Key**: `SK` (String)
- **GSI**: UserConversationsIndex (GSI1PK, GSI1SK)
- **TTL**: Enabled (auto-cleanup after 30 days)
- **Purpose**: Chat message history

```
PK Format:  CONVERSATION#{conversation_id}
SK Format:  MESSAGE#{timestamp}

Attributes:
{
  PK: "CONVERSATION#conv-123",
  SK: "MESSAGE#1704067200",
  conversation_id: "conv-123",
  session_id: "session-123",
  role: "user",
  content: "What is the status of my order?",
  created_at: 1704067200,
  GSI1PK: "USER#user@company.com",
  GSI1SK: "1704067200",
  TTL: 1736745600  # Unix timestamp for 30 days from now
}
```

---

## AWS Services Integration

### Core Services

| Service | Purpose | Integration |
|---------|---------|-------------|
| **ECS Fargate** | Containerized workloads | Frontend, Backend, MCP-Proxy |
| **Application Load Balancer** | Traffic routing | Distributes to Fargate tasks |
| **CloudFront** | CDN | Origin: ALB, caches frontend |
| **DynamoDB** | Operational data store | Agents, MCPs, KBs, Playground |
| **S3** | File storage | KB files, build artifacts, logs |
| **OpenSearch Serverless** | Vector search | KB semantic search |
| **Bedrock** | LLM services | Agent execution, KB sync |
| **Bedrock AgentCore** | Agent orchestration | Agent deployment & execution |
| **ECR** | Docker registry | MCP server images, Agent builds |
| **CodeBuild** | Docker builds | Build MCP servers, playgrounds |
| **Cognito** | Authentication | OAuth2, user pools |
| **Lambda** | Serverless functions | KB sync jobs, async processing |
| **SQS** | Message queue | Async job queue |
| **EventBridge** | Event routing | Scheduled jobs, triggers |
| **CloudWatch** | Observability | Logs, metrics, APM |

### Data Flow for Key Operations

#### Agent Deployment Flow
```
Frontend: Create/Update Agent
    ↓
Backend: AgentService.create_or_update()
    ↓
DynamoDB: Store agent metadata
    ↓
Bedrock AgentCore API: Register agent definition
    ↓
AgentCore Runtime: Deploy agent
    ↓
Frontend: Show deployment status (polling)
```

#### MCP Internal Deploy Flow
```
Frontend: Register Docker image
    ↓
Backend: MCPService.deploy_internal_mcp()
    ↓
Bedrock AgentCore API: Create runtime target
    ↓
AgentCore Runtime: Pull image from ECR, start container
    ↓
Backend: Auto-discover tools (POST /mcp tools/list)
    ↓
DynamoDB: Store tool definitions
    ↓
Frontend: Display available tools
```

#### Knowledge Base Sync Flow
```
Frontend: Upload files to S3 via Backend
    ↓
Backend: S3 PutObject event → SNS/SQS
    ↓
Lambda: Process file upload
    ↓
Bedrock KB: Sync data source (auto)
    ↓
OpenSearch: Index vectors (optional)
    ↓
DynamoDB: Update sync_status
    ↓
Frontend: Show sync progress (polling)
```

#### Playground Code Generation Flow
```
Frontend: Send chat message to Playground
    ↓
Backend: PlaygroundService.send_message()
    ↓
Bedrock: Execute agent with context
    ↓
Response: Agent reply + artifacts
    ↓
DynamoDB: Store conversation
    ↓
CodeBuild (Optional): Trigger build if code generated
    ↓
Frontend: Display response + generated artifacts
```

---

## Network Architecture

### VPC Configuration
```
VPC: 10.0.0.0/16

Public Subnets (ALB):
  AZ-1: 10.0.1.0/24 (2a)
  AZ-2: 10.0.2.0/24 (2b)

Private Subnets (ECS):
  AZ-1: 10.0.10.0/24 (2a)
  AZ-2: 10.0.11.0/24 (2b)

NAT Gateway: Public subnet → Private egress
```

### Security Groups

**ALB Security Group:**
- Ingress: 80 (HTTP), 443 (HTTPS) from 0.0.0.0/0
- Egress: All traffic to ECS security group

**ECS Security Group:**
- Ingress: 8000 (Backend), 8080 (Frontend), 5000 (MCP-Proxy) from ALB
- Egress: All traffic (to AWS services)

**RDS Security Group (if applicable):**
- Ingress: 3306/5432 from ECS security group
- Egress: None needed

---

## Security Architecture

### Authentication & Authorization

**User Authentication:**
- **OAuth2 via Cognito**: JWT tokens for frontend users
- **API Key**: For backend-to-backend communication
- **IAM Roles**: For AWS service access

**MCP Authentication (External):**
- **NO_AUTH**: Public Cognito user pool
- **OAUTH**: Custom user pool with OAuth2 flow

**JWT Validation:**
```python
# middleware/auth.py
- Verify JWT signature using Cognito public keys
- Check token expiration
- Extract user info (sub, email, roles)
- Attach to request context
```

### Authorization (RBAC)

**User Roles:**
- `ADMIN`: Full platform access
- `DEVELOPER`: Create/manage agents, MCPs, KBs
- `VIEWER`: Read-only access
- `OPERATOR`: Manage deployments

**Team Tags:**
- Resources tagged with team IDs
- Users can only access their team's resources
- Admins can access all resources

### Data Security

**Encryption in Transit:**
- HTTPS/TLS for all communication
- Secure WebSocket for real-time updates

**Encryption at Rest:**
- DynamoDB: AWS-managed encryption
- S3: Default encryption enabled
- Secrets: AWS Secrets Manager (API keys, tokens)

**IAM Least Privilege:**
- Each service has minimal permissions
- Resource-based policies for cross-service access
- No wildcard permissions

### Container Security

**Docker Best Practices:**
- Non-root user (UID 1001) in all containers
- Read-only root filesystem (where applicable)
- No hardcoded credentials (use IAM roles)
- Regular base image updates

**ECS Task Security:**
- IAM task role for AWS API calls
- Security groups restrict network access
- CloudWatch logging enabled
- Container health checks

---

## Frontend Architecture (React)

```
src/
├── main.tsx                    # Entry point
├── App.tsx                     # Root component
├── pages/                      # Page components
│   ├── dashboard/
│   │   └── Dashboard.tsx
│   ├── agent/
│   │   ├── AgentList.tsx       # List agents
│   │   ├── AgentDetail.tsx     # View agent
│   │   ├── AgentForm.tsx       # Create/Edit
│   │   └── AgentCreate.tsx
│   ├── mcp/
│   │   ├── MCPList.tsx
│   │   ├── MCPDetail.tsx
│   │   ├── MCPCreate.tsx
│   │   └── MCPEdit.tsx
│   ├── kb/
│   │   ├── KBList.tsx
│   │   ├── KBDetail.tsx
│   │   ├── KBCreate.tsx
│   │   └── KBEdit.tsx
│   ├── playground/
│   │   └── Playground.tsx
│   └── settings/
│       └── Settings.tsx
├── components/
│   ├── layout/
│   │   ├── MainLayout.tsx
│   │   ├── Header.tsx
│   │   └── Sidebar.tsx
│   ├── agent/
│   │   ├── AgentCard.tsx
│   │   ├── ChatPanel.tsx
│   │   └── DeployModal.tsx
│   ├── mcp/
│   │   ├── MCPCard.tsx
│   │   ├── DeployProgress.tsx
│   │   └── StepProgress.tsx
│   ├── kb/
│   │   └── VersionHistory.tsx
│   ├── common/
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   ├── Modal.tsx
│   │   ├── LoadingSpinner.tsx
│   │   ├── ChatMessageList.tsx
│   │   ├── MarkdownContent.tsx
│   │   ├── StatusIndicator.tsx
│   │   ├── Badge.tsx
│   │   ├── ErrorBoundary.tsx
│   │   ├── FeedbackButton.tsx
│   │   └── ...
│   └── layout/
├── contexts/
│   └── ToastContext.tsx        # Global toast notifications
├── services/
│   ├── api.ts                  # API client (RTK Query)
│   └── ...
├── hooks/
│   ├── useAgent.ts
│   ├── useMCP.ts
│   └── ...
├── store/
│   └── index.ts                # Redux store
├── styles/
│   └── index.css
└── index.css                   # Global styles

Key Libraries:
- React Router: Navigation
- React Query (RTK Query): Server state management
- Redux Toolkit: Global state
- Axios: HTTP client
- Tailwind CSS: Styling
- React Hot Toast: Notifications
```

### Frontend State Management

**Global State (Redux):**
- User authentication state
- Sidebar collapse state
- Theme preferences

**Server State (React Query):**
- Agents, MCPs, KBs (cached)
- Auto-refetch on focus
- Optimistic updates

**Local State (React useState):**
- Form inputs
- Modal open/close
- UI toggles

---

## Deployment Strategy

### Container Images

| Service | Base | Size | Registry |
|---------|------|------|----------|
| Frontend | node:20 + nginx | ~50MB | ECR |
| Backend | python:3.11 | ~200MB | ECR |
| MCP-Proxy | python:3.11 | ~200MB | ECR |
| EKS MCP | python:3.11 | ~300MB | ECR |

### Deployment Pipeline

```
Code Commit → GitHub Actions / CodePipeline
    ↓
Lint & Test
    ↓
Build Docker Images
    ↓
Push to ECR
    ↓
Update ECS Task Definitions
    ↓
Deploy to ECS Fargate (blue-green)
    ↓
Health Checks & Smoke Tests
    ↓
Rollback on Failure (Automatic)
```

### Environment Variables

**Backend Configuration:**
```env
# AWS
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789

# Database
DYNAMODB_AGENT_TABLE=platform-agent-management-prod
DYNAMODB_KB_TABLE=platform-kb-management-prod
DYNAMODB_MCP_TABLE=platform-mcp-management-prod

# Services
BEDROCK_AGENT_ROLE_ARN=arn:aws:iam::...
AGENTCORE_REGION=us-east-1
ECR_REPOSITORY=platform-mcps

# Security
COGNITO_USER_POOL_ID=us-east-1_xxxxxxxxx
COGNITO_CLIENT_ID=xxxxxxxxxxxxx
JWT_SECRET=xxxxxxxxxxxxx

# CORS
CORS_ORIGINS=["https://example.com", "http://localhost:3000"]
```

---

## Observability

### Logging Strategy

**CloudWatch Logs:**
- `/aws/ecs/agentic-ai-backend` - Backend application logs
- `/aws/ecs/agentic-ai-frontend` - Frontend errors
- `/aws/lambda/kb-sync` - KB sync Lambda logs
- `/aws/bedrock-agentcore/runtimes/{id}` - AgentCore runtime logs

**Log Format:**
```json
{
  "timestamp": "2024-01-05T12:34:56.789Z",
  "level": "INFO",
  "logger": "app.agent.service",
  "message": "Agent created successfully",
  "request_id": "req-123",
  "user_id": "user@company.com",
  "agent_id": "agent-123",
  "duration_ms": 234
}
```

### Metrics

**Application Metrics:**
- Request latency (p50, p95, p99)
- Error rate by endpoint
- Database operation latency
- Bedrock API latency
- Cache hit rate

**Infrastructure Metrics:**
- CPU/Memory utilization
- Network I/O
- Disk usage
- Task count

### Distributed Tracing

**OpenTelemetry:**
- Auto-instrumentation for FastAPI
- Trace propagation via headers
- Export to CloudWatch X-Ray
- Service dependencies

---

## Scalability Considerations

### Horizontal Scaling

**ECS Fargate:**
- Auto-scaling based on CPU/memory
- Target tracking: 70% CPU utilization
- Min 2 tasks (HA), Max 10 tasks

**DynamoDB:**
- On-demand billing (auto-scaling)
- Supports millions of concurrent requests
- GSI auto-scaling for queries

**S3:**
- Unlimited storage
- Request rate partitioning
- Multi-region replication (optional)

### Rate Limiting

**API Rate Limits:**
- 100 req/min per user (authenticated)
- 10 req/min per IP (unauthenticated)
- 1000 req/min per service account
- Implemented via middleware

### Caching Strategy

**CloudFront:**
- Static assets (JS, CSS, images): 24 hours
- HTML: 5 minutes (no cache headers)
- API responses: Vary by auth header

**Application Cache:**
- Agent definitions: 5 minutes
- MCP tool lists: 10 minutes
- KB metadata: 15 minutes
- Redis not required (DynamoDB fast enough)

---

## Development Workflow

### Local Development Setup

```bash
# Backend
cd apps/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export ENV_MODE=development
uvicorn app.main:app --reload

# Frontend
cd apps/frontend
pnpm install
pnpm dev

# Both services accessible:
# Backend: http://localhost:8000
# Frontend: http://localhost:5173
# API Docs: http://localhost:8000/docs
```

### Testing Strategy

**Backend:**
- Unit tests: `test_*.py` in each domain
- Integration tests: End-to-end with DynamoDB Local
- Coverage target: 80%+
- Run: `pytest app/tests`

**Frontend:**
- Component tests: React Testing Library
- E2E tests: Cypress/Playwright
- Coverage target: 60%+

---

## Future Roadmap

1. **Multi-Region Deployment**: Active-active setup across regions
2. **GraphQL API**: Alternative to REST endpoints
3. **Workflow Automation**: YAML-based agent workflows
4. **Custom Integrations**: Pre-built connectors for Salesforce, HubSpot, etc.
5. **Fine-tuning UI**: Support for model fine-tuning
6. **Cost Analytics**: Detailed cost breakdown by agent/KB
7. **Version Control**: Git-like versioning for agent configurations
8. **A/B Testing**: Framework for testing agent variants

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `/apps/backend/app/main.py` | FastAPI app setup, router registration |
| `/apps/backend/app/config.py` | Configuration management |
| `/apps/backend/app/middleware/auth.py` | JWT validation |
| `/infra/modules/dynamodb/main.tf` | DynamoDB table definitions |
| `/infra/modules/ecr/main.tf` | ECR repository setup |
| `/apps/frontend/src/App.tsx` | Frontend routing |
| `/apps/frontend/src/pages/agent/AgentList.tsx` | Agent list UI |
| `CLAUDE.md` | MCP deployment notes |

---

## Related Documentation

- [MCP Deployment Guide](../CLAUDE.md)
- [Security Scanning](./security/SCAN_EXEMPTIONS.md)
- [API Reference](./api.md) (if available)
- [Development Guide](./DEVELOPMENT.md) (if available)
