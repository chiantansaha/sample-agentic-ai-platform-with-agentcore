# Backend API Service 배포 아키텍처

## 개요
Backend API Service의 배포 아키텍처와 운영 환경 구성을 정의합니다.

## 배포 환경 구성

### 환경별 인프라 구성

#### Production Environment
```yaml
Environment: Production
├── VPC: 10.0.0.0/16
├── Subnets:
│   ├── Public: 10.0.1.0/24 (AZ-a), 10.0.2.0/24 (AZ-b)
│   └── Private: 10.0.3.0/24 (AZ-a), 10.0.4.0/24 (AZ-b)
├── ECS Cluster: backend-api-prod
├── Service: backend-api-service-prod
├── Task Count: 2-10 (Auto Scaling)
└── Domain: api.agentic-platform.com
```

#### Staging Environment
```yaml
Environment: Staging
├── VPC: 10.1.0.0/16
├── Subnets:
│   ├── Public: 10.1.1.0/24 (AZ-a), 10.1.2.0/24 (AZ-b)
│   └── Private: 10.1.3.0/24 (AZ-a), 10.1.4.0/24 (AZ-b)
├── ECS Cluster: backend-api-staging
├── Service: backend-api-service-staging
├── Task Count: 1-3 (Auto Scaling)
└── Domain: api-staging.agentic-platform.com
```

#### Development Environment
```yaml
Environment: Development
├── VPC: 10.2.0.0/16
├── Subnets:
│   ├── Public: 10.2.1.0/24 (AZ-a)
│   └── Private: 10.2.3.0/24 (AZ-a)
├── ECS Cluster: backend-api-dev
├── Service: backend-api-service-dev
├── Task Count: 1 (Fixed)
└── Domain: api-dev.agentic-platform.com
```

## 컨테이너 배포 아키텍처

### Docker 이미지 구성

#### Dockerfile 구조
```dockerfile
FROM python:3.11-slim

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 애플리케이션 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . /app
WORKDIR /app

# 헬스체크 설정
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 애플리케이션 실행
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 이미지 레이어 최적화
```yaml
Image Layers:
├── Base Layer: python:3.11-slim (150MB)
├── System Dependencies: gcc, curl (50MB)
├── Python Dependencies: FastAPI, boto3, etc. (200MB)
├── Application Code: Source code (10MB)
└── Total Size: ~410MB
```

### ECS Task Definition

#### Task Definition JSON
```json
{
  "family": "backend-api-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["EC2"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/backend-api-execution-role",
  "taskRoleArn": "arn:aws:iam::ACCOUNT:role/backend-api-task-role",
  "containerDefinitions": [
    {
      "name": "backend-api",
      "image": "ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/backend-api:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "production"
        },
        {
          "name": "AWS_DEFAULT_REGION",
          "value": "us-east-1"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:backend-api/database-url"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/backend-api",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": [
          "CMD-SHELL",
          "curl -f http://localhost:8000/health || exit 1"
        ],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

### ECS Service 구성

#### Service Definition
```yaml
Service Configuration:
├── Service Name: backend-api-service
├── Cluster: backend-api-cluster
├── Task Definition: backend-api-task:LATEST
├── Desired Count: 2
├── Launch Type: EC2
├── Network Configuration:
│   ├── VPC: vpc-12345678
│   ├── Subnets: [subnet-12345678, subnet-87654321]
│   ├── Security Groups: [sg-backend-api]
│   └── Assign Public IP: false
├── Load Balancer:
│   ├── Target Group: backend-api-targets
│   ├── Container Name: backend-api
│   ├── Container Port: 8000
│   └── Health Check Grace Period: 300s
└── Service Discovery:
    ├── Namespace: agentic-platform.local
    ├── Service Name: backend-api
    └── DNS Type: A
```

#### Auto Scaling 구성
```yaml
Auto Scaling Configuration:
├── Service Auto Scaling:
│   ├── Min Capacity: 2
│   ├── Max Capacity: 10
│   ├── Target Tracking Policies:
│   │   ├── CPU Utilization: 70%
│   │   ├── Memory Utilization: 80%
│   │   └── ALB Request Count: 1000 per target
│   ├── Scale Out Cooldown: 300s
│   └── Scale In Cooldown: 300s
└── Cluster Auto Scaling:
    ├── Capacity Provider: EC2
    ├── Target Capacity: 70%
    ├── Scale Out: When capacity > 70%
    └── Scale In: When capacity < 50%
```

## CI/CD 파이프라인 아키텍처

### GitHub Actions 워크플로우

#### 빌드 및 배포 파이프라인
```yaml
name: Backend API CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Run tests
        run: |
          pytest tests/ --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/develop'
    steps:
      - uses: actions/checkout@v3
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      - name: Login to ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1
      - name: Build and push image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          ECR_REPOSITORY: backend-api
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          docker tag $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG $ECR_REGISTRY/$ECR_REPOSITORY:latest
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    steps:
      - name: Deploy to staging
        run: |
          aws ecs update-service \
            --cluster backend-api-staging \
            --service backend-api-service-staging \
            --force-new-deployment

  deploy-production:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    steps:
      - name: Deploy to production
        run: |
          aws ecs update-service \
            --cluster backend-api-prod \
            --service backend-api-service-prod \
            --force-new-deployment
```

### 배포 전략

#### 롤링 배포 (Rolling Deployment)
```yaml
Rolling Deployment Strategy:
├── Deployment Type: Rolling Update
├── Minimum Healthy Percent: 50%
├── Maximum Percent: 200%
├── Health Check Grace Period: 300s
├── Deployment Steps:
│   1. Start new tasks (up to 200% capacity)
│   2. Wait for health checks to pass
│   3. Stop old tasks (maintain 50% minimum)
│   4. Repeat until all tasks updated
└── Rollback: Automatic on health check failure
```

#### 블루-그린 배포 (선택적)
```yaml
Blue-Green Deployment (Optional):
├── Blue Environment: Current production
├── Green Environment: New version deployment
├── Traffic Switch: ALB target group switch
├── Validation Period: 10 minutes
├── Rollback: Switch back to blue environment
└── Cleanup: Terminate green environment after validation
```

## 네트워크 아키텍처

### 로드 밸런서 구성

#### Application Load Balancer
```yaml
ALB Configuration:
├── Name: backend-api-alb
├── Scheme: Internet-facing
├── IP Address Type: IPv4
├── Subnets: Public subnets (Multi-AZ)
├── Security Groups: [sg-alb-backend-api]
├── Listeners:
│   ├── HTTP:80:
│   │   └── Action: Redirect to HTTPS
│   ├── HTTPS:443:
│   │   ├── SSL Certificate: *.agentic-platform.com
│   │   ├── Target Group: backend-api-targets
│   │   └── Health Check: GET /health
│   └── WebSocket:8080:
│       ├── Target Group: websocket-targets
│       ├── Stickiness: Enabled
│       └── Health Check: GET /ws/health
└── Access Logs: S3 bucket (7 days retention)
```

#### Target Group 구성
```yaml
Target Groups:
├── backend-api-targets:
│   ├── Protocol: HTTP
│   ├── Port: 8000
│   ├── VPC: vpc-12345678
│   ├── Health Check:
│   │   ├── Path: /health
│   │   ├── Interval: 30s
│   │   ├── Timeout: 5s
│   │   ├── Healthy Threshold: 2
│   │   └── Unhealthy Threshold: 5
│   ├── Deregistration Delay: 300s
│   └── Stickiness: Disabled
└── websocket-targets:
    ├── Protocol: HTTP
    ├── Port: 8080
    ├── Health Check: /ws/health
    ├── Stickiness: Enabled (1 hour)
    └── Connection Draining: 60s
```

### DNS 및 도메인 구성

#### Route 53 설정
```yaml
Route 53 Configuration:
├── Hosted Zone: agentic-platform.com
├── Records:
│   ├── api.agentic-platform.com:
│   │   ├── Type: A (Alias)
│   │   ├── Target: backend-api-alb
│   │   └── Health Check: Enabled
│   ├── api-staging.agentic-platform.com:
│   │   ├── Type: A (Alias)
│   │   └── Target: backend-api-staging-alb
│   └── api-dev.agentic-platform.com:
│       ├── Type: A (Alias)
│       └── Target: backend-api-dev-alb
└── SSL Certificates:
    ├── *.agentic-platform.com (ACM)
    ├── Auto-renewal: Enabled
    └── Validation: DNS
```

## 보안 아키텍처

### 네트워크 보안

#### Security Groups
```yaml
Security Groups:
├── sg-alb-backend-api:
│   ├── Inbound:
│   │   ├── HTTP (80) from 0.0.0.0/0
│   │   ├── HTTPS (443) from 0.0.0.0/0
│   │   └── WebSocket (8080) from 0.0.0.0/0
│   └── Outbound: All traffic to sg-backend-api
├── sg-backend-api:
│   ├── Inbound:
│   │   ├── HTTP (8000) from sg-alb-backend-api
│   │   └── WebSocket (8080) from sg-alb-backend-api
│   └── Outbound:
│       ├── HTTPS (443) to 0.0.0.0/0 (AWS APIs)
│       ├── Redis (6379) to sg-elasticache
│       └── OpenSearch (443) to sg-opensearch
└── sg-elasticache:
    ├── Inbound: Redis (6379) from sg-backend-api
    └── Outbound: None
```

#### Network ACLs
```yaml
Network ACLs:
├── Public Subnet NACL:
│   ├── Inbound:
│   │   ├── HTTP (80) from 0.0.0.0/0
│   │   ├── HTTPS (443) from 0.0.0.0/0
│   │   ├── WebSocket (8080) from 0.0.0.0/0
│   │   └── Ephemeral Ports (1024-65535) from 0.0.0.0/0
│   └── Outbound: All traffic
└── Private Subnet NACL:
    ├── Inbound:
    │   ├── HTTP (8000) from Public Subnets
    │   └── Ephemeral Ports from 0.0.0.0/0
    └── Outbound: All traffic
```

### 접근 제어

#### IAM 역할 및 정책
```yaml
IAM Roles:
├── backend-api-task-role:
│   ├── Trust Policy: ECS Tasks
│   ├── Policies:
│   │   ├── DynamoDBFullAccess (scoped to app tables)
│   │   ├── S3FullAccess (scoped to app buckets)
│   │   ├── SQSFullAccess (scoped to app queues)
│   │   ├── SNSPublishAccess (scoped to app topics)
│   │   ├── BedrockInvokeModel
│   │   ├── OpenSearchFullAccess (scoped to app domain)
│   │   ├── ElastiCacheFullAccess (scoped to app cluster)
│   │   └── CloudWatchPutMetricData
│   └── Session Duration: 1 hour
├── backend-api-execution-role:
│   ├── Trust Policy: ECS Tasks
│   ├── Policies:
│   │   ├── ECRReadOnlyAccess
│   │   ├── CloudWatchLogsFullAccess
│   │   ├── SecretsManagerReadWrite (scoped to app secrets)
│   │   └── KMSDecrypt (scoped to app keys)
│   └── Session Duration: 12 hours
└── github-actions-role:
    ├── Trust Policy: GitHub OIDC Provider
    ├── Policies:
    │   ├── ECRFullAccess (scoped to app repository)
    │   ├── ECSUpdateService
    │   └── PassRole (for ECS roles)
    └── Session Duration: 1 hour
```

## 모니터링 및 관찰성

### 로깅 아키텍처

#### 로그 수집 및 저장
```yaml
Logging Architecture:
├── Application Logs:
│   ├── Source: ECS Tasks (stdout/stderr)
│   ├── Driver: awslogs
│   ├── Destination: CloudWatch Logs
│   ├── Log Group: /ecs/backend-api
│   ├── Retention: 30 days
│   └── Format: JSON structured
├── Access Logs:
│   ├── Source: Application Load Balancer
│   ├── Destination: S3 bucket
│   ├── Format: Standard ALB format
│   └── Retention: 90 days
└── Infrastructure Logs:
    ├── Source: ECS Cluster, EC2 Instances
    ├── Agent: CloudWatch Agent
    ├── Destination: CloudWatch Logs
    └── Retention: 14 days
```

#### 로그 분석 및 검색
```yaml
Log Analysis:
├── CloudWatch Insights:
│   ├── Query Language: CloudWatch Insights Query
│   ├── Saved Queries: Error analysis, Performance analysis
│   └── Dashboards: Real-time log analysis
└── Metric Filters:
    ├── Error Rate: Count of ERROR level logs
    ├── Response Time: Extract response time from logs
    ├── Request Count: Count of request logs
    └── Custom Business Metrics: File processing, Chat messages
```

### 메트릭 및 알림

#### 핵심 메트릭
```yaml
Key Metrics:
├── Application Metrics:
│   ├── Request Rate: Requests per second
│   ├── Error Rate: Percentage of failed requests
│   ├── Response Time: P50, P95, P99 latencies
│   ├── Active Connections: WebSocket connections
│   └── Queue Depth: SQS message count
├── Infrastructure Metrics:
│   ├── CPU Utilization: ECS tasks and EC2 instances
│   ├── Memory Utilization: ECS tasks and EC2 instances
│   ├── Network I/O: Bytes in/out
│   └── Disk I/O: Read/write operations
└── Business Metrics:
    ├── Files Processed: Count per hour
    ├── Chat Messages: Count per hour
    ├── Agent Executions: Count per hour
    └── Active Workspaces: Unique count
```

#### 알림 구성
```yaml
Alerting Configuration:
├── Critical Alerts (PagerDuty):
│   ├── Service Down: 0 healthy targets
│   ├── High Error Rate: >10% for 5 minutes
│   ├── Database Errors: DynamoDB throttling
│   └── Memory Exhaustion: >95% for 2 minutes
├── Warning Alerts (Email):
│   ├── High Response Time: >2s average for 10 minutes
│   ├── High CPU: >80% for 15 minutes
│   ├── Queue Backlog: >100 messages for 30 minutes
│   └── Low Disk Space: <20% free space
└── Info Alerts (Slack):
    ├── Deployment Started/Completed
    ├── Auto Scaling Events
    ├── Scheduled Maintenance
    └── Daily/Weekly Reports
```

## 재해 복구 및 백업

### 백업 전략

#### 데이터 백업
```yaml
Backup Strategy:
├── DynamoDB:
│   ├── Point-in-Time Recovery: 35 days
│   ├── On-Demand Backups: Before major deployments
│   ├── Cross-Region Backup: us-west-2 (optional)
│   └── Automated Daily Backups: 7 days retention
├── S3:
│   ├── Versioning: Enabled
│   ├── Cross-Region Replication: us-west-2
│   ├── Lifecycle Policy: IA after 30 days, Glacier after 90 days
│   └── MFA Delete: Enabled for production
├── OpenSearch:
│   ├── Automated Snapshots: Daily to S3
│   ├── Manual Snapshots: Before major changes
│   ├── Cross-Region Snapshots: us-west-2
│   └── Retention: 30 days
└── ElastiCache:
    ├── Automatic Backups: 5 days retention
    ├── Manual Snapshots: Before major changes
    └── Cross-AZ Replication: Enabled
```

### 재해 복구 계획

#### RTO/RPO 목표
```yaml
Disaster Recovery Objectives:
├── RTO (Recovery Time Objective): 30 minutes
├── RPO (Recovery Point Objective): 5 minutes
├── Availability Target: 99.5%
└── Data Loss Tolerance: <5 minutes
```

#### 복구 절차
```yaml
Recovery Procedures:
├── Application Recovery:
│   1. Launch ECS tasks in backup AZ
│   2. Update ALB target groups
│   3. Verify health checks
│   4. Update DNS if needed
├── Database Recovery:
│   1. Restore DynamoDB from point-in-time
│   2. Restore OpenSearch from snapshot
│   3. Verify data integrity
│   4. Update application configuration
└── Full Site Recovery:
    1. Launch infrastructure in backup region
    2. Restore all data from backups
    3. Update DNS to point to backup region
    4. Verify full functionality
```

이 배포 아키텍처는 고가용성, 확장성, 보안을 보장하면서도 운영 효율성을 극대화하는 구조를 제공합니다.
