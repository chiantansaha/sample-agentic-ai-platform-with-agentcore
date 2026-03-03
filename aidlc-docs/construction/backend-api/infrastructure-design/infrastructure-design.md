# Backend API Service 인프라 설계

## 개요
Backend API Service의 논리적 컴포넌트를 AWS 클라우드 인프라 서비스에 매핑하여 실제 배포 가능한 아키텍처를 정의합니다.

## 전체 인프라 아키텍처

```
Internet Gateway
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                        VPC (10.0.0.0/16)                       │
│                                                                 │
│  ┌─────────────────┐                    ┌─────────────────┐    │
│  │  Public Subnet  │                    │  Public Subnet  │    │
│  │   (10.0.1.0/24) │                    │   (10.0.2.0/24) │    │
│  │       AZ-a      │                    │       AZ-b      │    │
│  │                 │                    │                 │    │
│  │ ┌─────────────┐ │                    │ ┌─────────────┐ │    │
│  │ │ NAT Gateway │ │                    │ │ NAT Gateway │ │    │
│  │ └─────────────┘ │                    │ └─────────────┘ │    │
│  └─────────────────┘                    └─────────────────┘    │
│           │                                       │             │
│           ▼                                       ▼             │
│  ┌─────────────────┐                    ┌─────────────────┐    │
│  │ Private Subnet  │                    │ Private Subnet  │    │
│  │  (10.0.3.0/24)  │                    │  (10.0.4.0/24)  │    │
│  │      AZ-a       │                    │      AZ-b       │    │
│  │                 │                    │                 │    │
│  │ ┌─────────────┐ │                    │ ┌─────────────┐ │    │
│  │ │ ECS Tasks   │ │                    │ │ ECS Tasks   │ │    │
│  │ │ (FastAPI)   │ │                    │ │ (FastAPI)   │ │    │
│  │ └─────────────┘ │                    │ └─────────────┘ │    │
│  └─────────────────┘                    └─────────────────┘    │
│                                                                 │
│  Application Load Balancer (ALB)                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Target Groups                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│  │  │   HTTP:80   │  │ HTTPS:443   │  │WebSocket:8080│    │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘

External AWS Services:
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  DynamoDB   │ │ OpenSearch  │ │     S3      │ │ElastiCache  │
│             │ │   Service   │ │             │ │ for Redis   │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘

┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│     SQS     │ │     SNS     │ │   Bedrock   │ │ AgentCore   │
│             │ │             │ │             │ │             │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

## 1. 배포 환경 설계

### 1.1 클라우드 제공자: Amazon Web Services (AWS)

#### 선택 근거
- **기술 스택 호환성**: Bedrock, AgentCore 등 필수 AI 서비스 제공
- **관리형 서비스**: DynamoDB, OpenSearch, ElastiCache 등 완전 관리형
- **확장성**: Auto Scaling 및 서버리스 옵션 풍부
- **보안**: VPC, IAM, KMS 등 엔터프라이즈급 보안 기능

#### 리전 선택
- **Primary Region**: us-east-1 (버지니아 북부)
- **근거**: Bedrock 서비스 가용성, 최신 기능 우선 제공, 비용 효율성

### 1.2 환경 분리 전략: VPC별 분리

#### 환경 구성
```
Production VPC (10.0.0.0/16)
├── Public Subnets: 10.0.1.0/24, 10.0.2.0/24
└── Private Subnets: 10.0.3.0/24, 10.0.4.0/24

Staging VPC (10.1.0.0/16)
├── Public Subnets: 10.1.1.0/24, 10.1.2.0/24
└── Private Subnets: 10.1.3.0/24, 10.1.4.0/24

Development VPC (10.2.0.0/16)
├── Public Subnets: 10.2.1.0/24, 10.2.2.0/24
└── Private Subnets: 10.2.3.0/24, 10.2.4.0/24
```

#### 분리 이점
- **네트워크 격리**: 환경 간 완전한 네트워크 분리
- **보안 강화**: 프로덕션 환경 접근 제어 강화
- **리소스 관리**: 환경별 독립적인 리소스 관리
- **비용 추적**: 환경별 명확한 비용 분석

### 1.3 가용 영역 (Availability Zone) 배치

#### 다중 AZ 구성
- **AZ-a (us-east-1a)**: 주 가용 영역
- **AZ-b (us-east-1b)**: 보조 가용 영역
- **고가용성**: 99.5% 가동시간 목표 달성
- **장애 복구**: AZ 장애 시 자동 장애 조치

## 2. 컴퓨팅 인프라 설계

### 2.1 컨테이너 오케스트레이션: Amazon ECS

#### 선택 근거
- **관리 용이성**: Kubernetes 대비 단순한 설정 및 관리
- **AWS 통합**: ALB, CloudWatch, IAM 등 네이티브 통합
- **비용 효율성**: 관리 오버헤드 없음
- **확장성**: Service Auto Scaling 지원

#### ECS 클러스터 구성
```yaml
ECS Cluster: backend-api-cluster
├── Capacity Provider: EC2
├── Instance Type: t3.medium (2 vCPU, 4GB RAM)
├── Min Capacity: 2 instances
├── Max Capacity: 10 instances
└── Target Capacity: 70%
```

### 2.2 컨테이너 서비스 구성

#### ECS Service 설정
```yaml
Service Name: backend-api-service
├── Task Definition: backend-api-task
├── Desired Count: 2 (minimum)
├── Max Count: 10 (maximum)
├── Deployment Type: Rolling Update
├── Health Check Grace Period: 300 seconds
└── Load Balancer: Application Load Balancer
```

#### Task Definition
```yaml
Task Definition: backend-api-task
├── CPU: 512 (0.5 vCPU)
├── Memory: 1024 MB (1 GB)
├── Network Mode: awsvpc
├── Container Port: 8000
├── Health Check: GET /health
└── Log Driver: awslogs
```

### 2.3 자동 확장 정책

#### Service Auto Scaling
```yaml
Auto Scaling Policy:
├── Target Tracking Scaling:
│   ├── CPU Utilization: 70%
│   ├── Memory Utilization: 80%
│   └── ALB Request Count: 1000 per target
├── Scale Out Cooldown: 300 seconds
├── Scale In Cooldown: 300 seconds
└── Scale In Protection: Enabled
```

#### Cluster Auto Scaling
```yaml
Cluster Auto Scaling:
├── Capacity Provider: EC2
├── Target Capacity: 70%
├── Scale Out: Add instance when capacity > 70%
├── Scale In: Remove instance when capacity < 50%
└── Instance Protection: Enabled during scale-in
```

## 3. 스토리지 인프라 설계

### 3.1 데이터베이스 서비스: Amazon DynamoDB

#### 테이블 구성
```yaml
DynamoDB Tables:
├── workspaces:
│   ├── Billing Mode: On-Demand
│   ├── Encryption: AWS KMS
│   └── Point-in-Time Recovery: Enabled
├── mcp_servers:
│   ├── Billing Mode: On-Demand
│   ├── GSI: workspace-status-index
│   └── TTL: Enabled (for temporary data)
├── knowledge_bases:
│   ├── Billing Mode: On-Demand
│   ├── GSI: workspace-created-index
│   └── Stream: Enabled (for OpenSearch sync)
├── agents:
│   ├── Billing Mode: On-Demand
│   ├── GSI: workspace-type-index
│   └── Encryption: AWS KMS
└── chat_sessions:
    ├── Billing Mode: On-Demand
    ├── TTL: 30 days (configurable)
    └── Stream: Enabled (for analytics)
```

#### 백업 및 복구
- **Point-in-Time Recovery**: 35일 보관
- **On-Demand Backup**: 주요 배포 전 수동 백업
- **Cross-Region Backup**: 재해 복구용 (선택적)

### 3.2 검색 엔진: Amazon OpenSearch Service

#### 클러스터 구성
```yaml
OpenSearch Cluster:
├── Version: 2.11
├── Instance Type: t3.small.search
├── Instance Count: 2 (Multi-AZ)
├── Master Nodes: 3 x t3.small.search
├── Storage: 20 GB EBS (gp3)
├── Encryption: At rest and in transit
└── Access Policy: VPC-based
```

#### 인덱스 설계
```yaml
Indices:
├── knowledge-chunks-{workspace-id}:
│   ├── Shards: 1 (small workspaces)
│   ├── Replicas: 1
│   └── Refresh Interval: 30s
└── chat-history-{workspace-id}:
    ├── Shards: 1
    ├── Replicas: 1
    └── Index Lifecycle: 90 days retention
```

### 3.3 파일 저장소: Amazon S3

#### 버킷 구성
```yaml
S3 Buckets:
├── agentic-ai-platform-files-prod:
│   ├── Versioning: Enabled
│   ├── Encryption: SSE-KMS
│   ├── Lifecycle Policy: IA after 30 days, Glacier after 90 days
│   └── CORS: Enabled for direct uploads
└── agentic-ai-platform-backups-prod:
    ├── Versioning: Enabled
    ├── Encryption: SSE-KMS
    └── Lifecycle Policy: Glacier after 7 days
```

#### 폴더 구조
```
agentic-ai-platform-files-prod/
├── workspaces/
│   └── {workspace-id}/
│       ├── knowledge-bases/
│       │   └── {kb-id}/
│       │       ├── files/          # 원본 파일
│       │       └── chunks/         # 처리된 청크
│       └── agents/
│           └── {agent-id}/
│               └── artifacts/      # 에이전트 아티팩트
└── temp/                          # 임시 파일 (1일 TTL)
```

### 3.4 캐시 인프라: Amazon ElastiCache for Redis

#### 클러스터 구성
```yaml
ElastiCache Redis:
├── Engine Version: 7.0
├── Node Type: cache.t3.micro
├── Cluster Mode: Disabled (single shard)
├── Multi-AZ: Enabled
├── Automatic Failover: Enabled
├── Backup Retention: 5 days
└── Encryption: In transit and at rest
```

#### 메모리 할당 전략
```yaml
Memory Allocation:
├── API Response Cache: 40% (400MB)
├── Session Data: 30% (300MB)
├── Rate Limiting: 20% (200MB)
└── Temporary Data: 10% (100MB)
```

## 4. 메시징 인프라 설계

### 4.1 메시지 큐: Amazon SQS

#### 큐 구성
```yaml
SQS Queues:
├── file-processing-queue:
│   ├── Type: Standard
│   ├── Visibility Timeout: 600 seconds (10분)
│   ├── Message Retention: 14 days
│   ├── DLQ: file-processing-dlq (3 retries)
│   └── Encryption: SSE-SQS
├── embedding-generation-queue:
│   ├── Type: Standard
│   ├── Visibility Timeout: 300 seconds (5분)
│   ├── Message Retention: 7 days
│   ├── DLQ: embedding-generation-dlq (2 retries)
│   └── Batch Size: 10 messages
└── notification-queue:
    ├── Type: Standard
    ├── Visibility Timeout: 60 seconds
    ├── Message Retention: 1 day
    └── Encryption: SSE-SQS
```

### 4.2 이벤트 발행: Amazon SNS

#### 토픽 구성
```yaml
SNS Topics:
├── file-processing-events:
│   ├── Type: Standard
│   ├── Encryption: SSE-SNS
│   ├── Subscriptions:
│   │   ├── SQS: notification-queue
│   │   └── Lambda: websocket-notifier
│   └── Filter Policy: event_type
└── system-alerts:
    ├── Type: Standard
    ├── Encryption: SSE-SNS
    ├── Subscriptions:
    │   ├── Email: ops-team@company.com
    │   └── SQS: alert-processing-queue
    └── Filter Policy: severity
```

## 5. 네트워킹 인프라 설계

### 5.1 로드 밸런서: Application Load Balancer (ALB)

#### ALB 구성
```yaml
Application Load Balancer:
├── Scheme: Internet-facing
├── IP Address Type: IPv4
├── Subnets: Public subnets (Multi-AZ)
├── Security Groups: alb-security-group
├── Listeners:
│   ├── HTTP:80 → Redirect to HTTPS
│   ├── HTTPS:443 → backend-api-targets
│   └── WebSocket:8080 → websocket-targets
└── SSL Certificate: AWS Certificate Manager
```

#### Target Groups
```yaml
Target Groups:
├── backend-api-targets:
│   ├── Protocol: HTTP
│   ├── Port: 8000
│   ├── Health Check: GET /health
│   ├── Health Check Interval: 30 seconds
│   └── Healthy Threshold: 2
└── websocket-targets:
    ├── Protocol: HTTP
    ├── Port: 8080
    ├── Health Check: GET /ws/health
    └── Stickiness: Enabled (WebSocket sessions)
```

### 5.2 보안 그룹 구성

#### Security Groups
```yaml
Security Groups:
├── alb-security-group:
│   ├── Inbound:
│   │   ├── HTTP (80) from 0.0.0.0/0
│   │   ├── HTTPS (443) from 0.0.0.0/0
│   │   └── WebSocket (8080) from 0.0.0.0/0
│   └── Outbound: All traffic
├── ecs-security-group:
│   ├── Inbound:
│   │   ├── HTTP (8000) from alb-security-group
│   │   └── WebSocket (8080) from alb-security-group
│   └── Outbound: All traffic
└── database-security-group:
    ├── Inbound:
    │   ├── DynamoDB: VPC Endpoint
    │   ├── OpenSearch (443) from ecs-security-group
    │   └── Redis (6379) from ecs-security-group
    └── Outbound: None
```

### 5.3 VPC Endpoints

#### 프라이빗 연결
```yaml
VPC Endpoints:
├── DynamoDB:
│   ├── Type: Gateway Endpoint
│   ├── Route Tables: Private subnet route tables
│   └── Policy: Full access for ECS tasks
├── S3:
│   ├── Type: Gateway Endpoint
│   ├── Route Tables: Private subnet route tables
│   └── Policy: Bucket-specific access
└── SQS:
    ├── Type: Interface Endpoint
    ├── Subnets: Private subnets
    └── Security Group: vpc-endpoint-sg
```

## 6. 모니터링 인프라 설계

### 6.1 로깅: Amazon CloudWatch Logs

#### 로그 그룹 구성
```yaml
CloudWatch Log Groups:
├── /ecs/backend-api:
│   ├── Retention: 30 days
│   ├── Encryption: AWS KMS
│   └── Metric Filters: Error rate, Response time
├── /aws/lambda/file-processor:
│   ├── Retention: 14 days
│   └── Metric Filters: Processing failures
└── /aws/apigateway/access-logs:
    ├── Retention: 90 days
    └── Format: JSON structured logs
```

### 6.2 메트릭: Amazon CloudWatch Metrics

#### 커스텀 메트릭
```yaml
Custom Metrics:
├── Application Metrics:
│   ├── api.response_time (Average, P95, P99)
│   ├── api.request_count (Sum)
│   ├── api.error_rate (Percentage)
│   └── websocket.active_connections (Count)
├── Business Metrics:
│   ├── files.processed_count (Sum)
│   ├── chat.messages_count (Sum)
│   ├── agents.execution_count (Sum)
│   └── workspaces.active_count (Count)
└── Infrastructure Metrics:
    ├── ecs.cpu_utilization (Average)
    ├── ecs.memory_utilization (Average)
    ├── alb.target_response_time (Average)
    └── dynamodb.consumed_capacity (Sum)
```

### 6.3 알림: Amazon CloudWatch Alarms

#### 알림 구성
```yaml
CloudWatch Alarms:
├── High Error Rate:
│   ├── Metric: api.error_rate
│   ├── Threshold: > 5%
│   ├── Period: 5 minutes
│   └── Action: SNS notification
├── High Response Time:
│   ├── Metric: api.response_time
│   ├── Threshold: > 2 seconds (average)
│   ├── Period: 5 minutes
│   └── Action: Auto scaling trigger
├── Low Availability:
│   ├── Metric: alb.healthy_host_count
│   ├── Threshold: < 1
│   ├── Period: 1 minute
│   └── Action: SNS critical alert
└── High CPU Usage:
    ├── Metric: ecs.cpu_utilization
    ├── Threshold: > 80%
    ├── Period: 10 minutes
    └── Action: Auto scaling trigger
```

### 6.4 대시보드: Amazon CloudWatch Dashboard

#### 대시보드 구성
```yaml
CloudWatch Dashboards:
├── System Overview:
│   ├── ECS Service Health
│   ├── ALB Request Metrics
│   ├── Database Performance
│   └── Error Rate Trends
├── Application Performance:
│   ├── API Response Times
│   ├── WebSocket Connections
│   ├── File Processing Status
│   └── Cache Hit Rates
└── Business Metrics:
    ├── Active Users
    ├── File Processing Volume
    ├── Chat Message Volume
    └── Agent Execution Volume
```

## 7. 보안 및 규정 준수

### 7.1 IAM 역할 및 정책

#### ECS Task Role
```yaml
ECS Task Role: backend-api-task-role
├── DynamoDB: Read/Write access to application tables
├── S3: Read/Write access to application buckets
├── SQS: Send/Receive messages from application queues
├── SNS: Publish to application topics
├── Bedrock: InvokeModel permissions
├── OpenSearch: Read/Write access to indices
├── ElastiCache: Connect and execute commands
└── CloudWatch: PutMetricData and CreateLogStream
```

#### ECS Execution Role
```yaml
ECS Execution Role: backend-api-execution-role
├── ECR: Pull container images
├── CloudWatch Logs: Create log groups and streams
├── Secrets Manager: Retrieve application secrets
└── KMS: Decrypt encrypted environment variables
```

### 7.2 암호화 및 키 관리

#### AWS KMS 키
```yaml
KMS Keys:
├── application-data-key:
│   ├── Usage: DynamoDB, S3, ElastiCache encryption
│   ├── Key Policy: ECS tasks and Lambda functions
│   └── Rotation: Annual
└── logs-encryption-key:
    ├── Usage: CloudWatch Logs encryption
    ├── Key Policy: CloudWatch service
    └── Rotation: Annual
```

### 7.3 네트워크 보안

#### WAF (Web Application Firewall)
```yaml
AWS WAF Rules:
├── Rate Limiting: 1000 requests per 5 minutes per IP
├── SQL Injection Protection: Block common SQL injection patterns
├── XSS Protection: Block cross-site scripting attempts
├── IP Whitelist: Allow specific IP ranges (optional)
└── Geographic Blocking: Block specific countries (optional)
```

## 8. 비용 최적화

### 8.1 리소스 크기 조정

#### 초기 배포 크기
```yaml
Initial Deployment:
├── ECS Tasks: 2 instances (t3.medium)
├── DynamoDB: On-Demand (예상 $50/월)
├── OpenSearch: t3.small.search x 2 (예상 $100/월)
├── ElastiCache: cache.t3.micro (예상 $15/월)
├── S3: 100GB 저장 (예상 $25/월)
└── Data Transfer: 1TB/월 (예상 $90/월)
```

### 8.2 비용 모니터링

#### AWS Cost Explorer 설정
- 일일 비용 알림: $50 초과 시
- 월간 예산: $500 (80% 도달 시 알림)
- 서비스별 비용 추적
- 태그 기반 비용 할당

이 인프라 설계는 NFR 요구사항을 충족하면서도 비용 효율적이고 확장 가능한 아키텍처를 제공합니다.
