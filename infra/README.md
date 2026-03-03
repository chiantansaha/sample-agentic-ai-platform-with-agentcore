# Infrastructure Deployment Guide

## 📁 Directory Structure

```
infra/
├── environments/
│   ├── dev/                    # Development environment
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── terraform.tfvars
│   └── prod/                   # Production environment
│       ├── main.tf
│       ├── variables.tf
│       ├── outputs.tf
│       └── terraform.tfvars
└── README.md
```

## 🚀 Deployment Commands

### Dev Environment
```bash
cd infra/environments/dev
terraform init
terraform plan
terraform apply
```

### Prod Environment
```bash
cd infra/environments/prod
terraform init
terraform plan
terraform apply
```

## 🔧 Environment Differences

| Resource | Dev | Prod |
|----------|-----|------|
| **VPC CIDR** | 10.0.0.0/16 | 10.1.0.0/16 |
| **Project Name** | agentic-ai-dev | agentic-ai-prod |
| **ECS Tasks** | 2 | 2 |
| **CPU/Memory** | 512/1024 | 1024/2048 |
| **Log Retention** | 7 days | 30 days |

## 🔒 Security

Both environments are completely isolated:
- Separate VPCs with different CIDR blocks (10.0.x.x vs 10.1.x.x)
- Separate ECR repositories
- Separate ECS clusters and services
- Environment-specific IAM roles and security groups
- Complete Security Group descriptions and Name tags (prod only)

## 💰 Cost Optimization

- **Dev:** Lower resource allocation, shorter log retention, minimal configuration
- **Prod:** Higher resource allocation, longer log retention, internal service optimized (2 tasks)

## 📦 생성되는 AWS 리소스

### 네트워크 (VPC)
| 리소스 | 이름 패턴 | 설명 |
|--------|----------|------|
| VPC | `{project_name}-vpc` | 메인 VPC (10.0.0.0/16) |
| Public Subnet | `{project_name}-public-{1,2}` | ALB용 퍼블릭 서브넷 (2개 AZ) |
| Private Subnet | `{project_name}-private-{1,2}` | ECS용 프라이빗 서브넷 (2개 AZ) |
| Internet Gateway | `{project_name}-igw` | 인터넷 게이트웨이 |
| NAT Gateway | `{project_name}-nat-{1,2}` | NAT 게이트웨이 (2개) |
| Elastic IP | `{project_name}-nat-eip-{1,2}` | NAT용 EIP (2개) |

### 로드밸런서 (ALB)
| 리소스 | 이름 패턴 | 설명 |
|--------|----------|------|
| ALB | `{project_name}-alb` | Application Load Balancer |
| Target Group | `{project_name}-frontend-tg` | 프론트엔드 타겟 그룹 (포트 80) |
| Target Group | `{project_name}-backend-tg` | 백엔드 타겟 그룹 (포트 8000) |

### 컨테이너 (ECS)
| 리소스 | 이름 패턴 | 설명 |
|--------|----------|------|
| ECS Cluster | `{project_name}-cluster` | Fargate 클러스터 |
| ECS Service | `{project_name}-service` | 프론트엔드 + 백엔드 서비스 |
| Task Definition | `{project_name}` | 컨테이너 정의 |

### 컨테이너 레지스트리 (ECR)
| 리소스 | 이름 | 설명 |
|--------|------|------|
| ECR Repository | `{project_name}-frontend` | 프론트엔드 이미지 |
| ECR Repository | `{project_name}-backend` | 백엔드 이미지 |
| ECR Repository | `agentic-ai/mcp-server` | Internal MCP Deploy 이미지 |

### 데이터베이스 (DynamoDB)
| 리소스 | 이름 패턴 | 설명 |
|--------|----------|------|
| DynamoDB Table | `{project_name}-mcp` | MCP 메인 테이블 (PK: id, GSI: team-tags-index, created-at-index) |
| DynamoDB Table | `{project_name}-mcp-versions` | MCP 버전 테이블 (PK: mcp_id, SK: version) |
| DynamoDB Table | `{project_name}-api-catalog` | API Catalog 테이블 (PK: id) |

### 인증 (Cognito)
| 리소스 | 이름 | 설명 |
|--------|------|------|
| User Pool | `agentic-mcp-pool` | MCP OAuth 인증용 |
| User Pool Domain | `mcp-{environment}` | OAuth 토큰 엔드포인트 |
| Resource Server | `mcp-api` | OAuth 스코프 정의 (read/write/invoke) |
| App Client | `mcp-gateway-oauth-client` | M2M 인증 클라이언트 |

### 보안 (Security Groups)
| 리소스 | 이름 패턴 | 설명 |
|--------|----------|------|
| Security Group | `{project_name}-alb-sg` | ALB용 (HTTP/HTTPS 인바운드 허용) |
| Security Group | `{project_name}-ecs-sg` | ECS용 (ALB에서만 접근 허용) |

### IAM
| 리소스 | 이름 패턴 | 설명 |
|--------|----------|------|
| IAM Role | `{project_name}-ecs-execution-role` | ECS Task Execution Role |
| IAM Role | `{project_name}-ecs-task-role` | ECS Task Role |
| IAM Policy | `{project_name}-ecs-task-additional` | DynamoDB, ECR, Cognito, AgentCore 권한 |

### 로깅 (CloudWatch)
| 리소스 | 이름 패턴 | 설명 |
|--------|----------|------|
| Log Group | `/ecs/{project_name}` | ECS 컨테이너 로그 |

## 📤 Outputs

배포 후 확인 가능한 값들:

```bash
terraform output
```

| Output | 설명 |
|--------|------|
| `alb_dns_name` | ALB DNS 주소 |
| `frontend_ecr_repository_url` | 프론트엔드 ECR URL |
| `backend_ecr_repository_url` | 백엔드 ECR URL |
| `mcp_server_ecr_repository_url` | MCP Server ECR URL |
| `dynamodb_mcp_table_name` | MCP DynamoDB 테이블 이름 |
| `dynamodb_mcp_versions_table_name` | MCP Versions 테이블 이름 |
| `dynamodb_api_catalog_table_name` | API Catalog 테이블 이름 |
| `cognito_user_pool_id` | Cognito User Pool ID |
| `cognito_client_id` | Cognito App Client ID |
| `cognito_oauth_token_url` | OAuth 토큰 엔드포인트 |
| `cognito_discovery_url` | OpenID Connect Discovery URL |

## ⚠️ 주의사항

1. **IAM Role은 글로벌**: 리전이 달라도 같은 이름의 IAM Role은 충돌합니다
2. **Cognito Domain은 글로벌**: User Pool Domain은 전체 AWS에서 고유해야 합니다
3. **NAT Gateway 비용**: 각 NAT Gateway는 시간당 비용이 발생합니다
