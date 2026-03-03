# Backend API Service 논리적 컴포넌트 설계

## 개요
Backend API Service의 논리적 컴포넌트 구조와 각 컴포넌트 간의 상호작용을 정의합니다.

## 전체 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────┐
│                    Application Load Balancer                    │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                   API Gateway Layer                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐              │
│  │  Request    │ │ Rate Limit  │ │   CORS      │              │
│  │ Validation  │ │ Middleware  │ │ Middleware  │              │
│  └─────────────┘ └─────────────┘ └─────────────┘              │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                 Business Logic Layer                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │    MCP      │ │ Knowledge   │ │   Agent     │ │Playground │ │
│  │  Service    │ │Base Service │ │  Service    │ │ Service   │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                 Data Access Layer                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │  DynamoDB   │ │ OpenSearch  │ │     S3      │ │   Redis   │ │
│  │  Repository │ │ Repository  │ │ Repository  │ │Repository │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│              External Service Integration                       │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │   Bedrock   │ │ AgentCore   │ │     SQS     │ │    SNS    │ │
│  │   Client    │ │   Client    │ │   Client    │ │  Client   │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 1. API Gateway Layer

### 1.1 요청 검증 미들웨어 (Request Validation Middleware)

#### 책임
- 요청 데이터 형식 검증
- 필수 헤더 확인
- 요청 크기 제한
- 악성 요청 필터링

#### 구현 세부사항
```python
class RequestValidationMiddleware:
    def __init__(self, max_request_size: int = 10_000_000):  # 10MB
        self.max_request_size = max_request_size
    
    async def __call__(self, request: Request, call_next):
        # 요청 크기 검증
        # 헤더 검증
        # 데이터 형식 검증
        pass
```

#### 의존성
- Pydantic (데이터 검증)

### 1.2 속도 제한 미들웨어 (Rate Limiting Middleware)

#### 책임
- API 호출 빈도 제한
- 사용자별/IP별 요청 수 추적
- 제한 초과 시 429 응답
- 슬라이딩 윈도우 알고리즘 구현

#### 구현 전략
- **기본 제한**: 분당 100 요청
- **파일 업로드**: 시간당 50 요청
- **채팅 API**: 분당 30 요청
- **IP 기반**: 동일 IP에서 분당 200 요청

#### 의존성
- Redis (요청 카운터)

### 1.3 CORS 미들웨어

#### 책임
- Cross-Origin 요청 처리
- 허용된 도메인 검증
- Preflight 요청 응답
- 보안 헤더 설정

#### 설정
```python
CORS_CONFIG = {
    "allow_origins": ["https://app.example.com"],
    "allow_methods": ["GET", "POST", "PUT", "DELETE"],
    "allow_headers": ["Authorization", "Content-Type"],
    "max_age": 86400
}
```

## 2. Business Logic Layer

### 2.1 MCP 서비스 (MCP Service)

#### 책임
- MCP 서버 등록 및 관리
- MCP 도구 검색 및 실행
- 서버 상태 모니터링
- 오류 처리 및 복구

#### 주요 메서드
```python
class MCPService:
    async def register_server(self, server_config: MCPServerConfig) -> MCPServer
    async def list_servers(self, workspace_id: str) -> List[MCPServer]
    async def execute_tool(self, tool_request: ToolRequest) -> ToolResponse
    async def health_check(self, server_id: str) -> HealthStatus
```

#### 의존성
- MCP Repository (DynamoDB)
- External MCP Client
- Circuit Breaker

### 2.2 지식베이스 서비스 (Knowledge Base Service)

#### 책임
- 지식베이스 생성 및 관리
- 파일 업로드 및 처리 오케스트레이션
- 검색 쿼리 처리
- 처리 상태 추적

#### 주요 메서드
```python
class KnowledgeBaseService:
    async def create_knowledge_base(self, kb_config: KBConfig) -> KnowledgeBase
    async def upload_file(self, file_data: FileUpload) -> ProcessingJob
    async def search_documents(self, query: SearchQuery) -> SearchResults
    async def get_processing_status(self, job_id: str) -> ProcessingStatus
```

#### 의존성
- Knowledge Base Repository (DynamoDB)
- S3 Repository
- OpenSearch Repository
- SQS Client (비동기 처리)

### 2.3 에이전트 서비스 (Agent Service)

#### 책임
- 에이전트 정의 및 관리
- AgentCore 통합
- 에이전트 실행 및 모니터링
- 결과 수집 및 저장

#### 주요 메서드
```python
class AgentService:
    async def create_agent(self, agent_config: AgentConfig) -> Agent
    async def execute_agent(self, execution_request: ExecutionRequest) -> ExecutionResult
    async def list_executions(self, agent_id: str) -> List[Execution]
    async def get_execution_logs(self, execution_id: str) -> ExecutionLogs
```

#### 의존성
- Agent Repository (DynamoDB)
- AgentCore Client
- Circuit Breaker

### 2.4 플레이그라운드 서비스 (Playground Service)

#### 책임
- 채팅 세션 관리
- 실시간 메시지 처리
- LLM 통합 및 스트리밍
- 채팅 이력 저장

#### 주요 메서드
```python
class PlaygroundService:
    async def create_session(self, session_config: SessionConfig) -> ChatSession
    async def send_message(self, message: ChatMessage) -> AsyncIterator[ChatResponse]
    async def get_chat_history(self, session_id: str) -> List[ChatMessage]
    async def end_session(self, session_id: str) -> None
```

#### 의존성
- Chat Repository (DynamoDB)
- Bedrock Client
- WebSocket Manager
- Redis (임시 상태)

## 3. Data Access Layer

### 3.1 DynamoDB Repository

#### 책임
- DynamoDB 테이블 추상화
- CRUD 작업 구현
- 배치 작업 최적화
- 오류 처리 및 재시도

#### 테이블 구조
```python
TABLES = {
    "workspaces": {
        "partition_key": "workspace_id",
        "attributes": ["name", "description", "created_at", "settings"]
    },
    "mcp_servers": {
        "partition_key": "workspace_id",
        "sort_key": "server_id",
        "attributes": ["name", "url", "status", "tools"]
    },
    "knowledge_bases": {
        "partition_key": "workspace_id",
        "sort_key": "kb_id",
        "attributes": ["name", "description", "file_count", "status"]
    }
}
```

#### 구현 패턴
```python
class DynamoDBRepository:
    def __init__(self, table_name: str, dynamodb_client):
        self.table_name = table_name
        self.client = dynamodb_client
    
    async def get_item(self, key: Dict) -> Optional[Dict]
    async def put_item(self, item: Dict) -> None
    async def query(self, key_condition: str, **kwargs) -> List[Dict]
    async def batch_write(self, items: List[Dict]) -> None
```

### 3.2 OpenSearch Repository

#### 책임
- 검색 인덱스 관리
- 벡터 검색 구현
- 인덱싱 작업 처리
- 검색 결과 최적화

#### 인덱스 설계
```python
INDEX_MAPPINGS = {
    "knowledge_chunks": {
        "properties": {
            "content": {"type": "text", "analyzer": "standard"},
            "embedding": {"type": "dense_vector", "dims": 1536},
            "metadata": {"type": "object"},
            "workspace_id": {"type": "keyword"},
            "kb_id": {"type": "keyword"}
        }
    }
}
```

#### 검색 구현
```python
class OpenSearchRepository:
    async def index_document(self, doc: Document) -> str
    async def vector_search(self, query_vector: List[float], filters: Dict) -> SearchResults
    async def text_search(self, query: str, filters: Dict) -> SearchResults
    async def bulk_index(self, documents: List[Document]) -> BulkResponse
```

### 3.3 S3 Repository

#### 책임
- 파일 업로드/다운로드
- 멀티파트 업로드 관리
- 메타데이터 관리
- 접근 권한 제어

#### 버킷 구조
```
bucket-name/
├── workspaces/
│   └── {workspace_id}/
│       ├── knowledge-bases/
│       │   └── {kb_id}/
│       │       ├── files/          # 원본 파일
│       │       └── chunks/         # 처리된 청크
│       └── agents/
│           └── {agent_id}/
│               └── artifacts/      # 에이전트 아티팩트
```

#### 구현
```python
class S3Repository:
    async def upload_file(self, file_path: str, content: bytes) -> str
    async def download_file(self, file_path: str) -> bytes
    async def generate_presigned_url(self, file_path: str, expires: int) -> str
    async def list_files(self, prefix: str) -> List[str]
```

### 3.4 Redis Repository

#### 책임
- 캐시 데이터 관리
- 임시 데이터 저장
- 분산 락 구현
- 처리 상태 추적

#### 데이터 구조
```python
REDIS_KEYS = {
    "api_cache": "cache:api:{endpoint}:{params_hash}",
    "processing_status": "status:{job_id}",
    "rate_limit": "rate:{ip}:{endpoint}",
    "temp_data": "temp:{correlation_id}"
}
```

## 4. External Service Integration

### 4.1 Bedrock Client

#### 책임
- LLM 모델 호출
- 스트리밍 응답 처리
- 토큰 사용량 추적
- 오류 처리 및 재시도

#### 구현
```python
class BedrockClient:
    def __init__(self, region: str, model_id: str):
        self.client = boto3.client('bedrock-runtime', region_name=region)
        self.model_id = model_id
    
    async def invoke_model(self, prompt: str, **kwargs) -> ModelResponse
    async def invoke_model_stream(self, prompt: str, **kwargs) -> AsyncIterator[str]
```

### 4.2 AgentCore Client

#### 책임
- 에이전트 실행 요청
- 실행 상태 모니터링
- 결과 수집
- 오류 처리

#### 구현
```python
class AgentCoreClient:
    async def create_execution(self, agent_config: Dict) -> str
    async def get_execution_status(self, execution_id: str) -> ExecutionStatus
    async def get_execution_result(self, execution_id: str) -> ExecutionResult
    async def cancel_execution(self, execution_id: str) -> None
```

### 4.3 SQS Client

#### 책임
- 메시지 큐 관리
- 비동기 작업 전송
- 배치 처리
- DLQ 관리

#### 큐 구조
```python
QUEUES = {
    "file_processing": {
        "visibility_timeout": 600,  # 10분
        "message_retention": 1209600,  # 14일
        "dlq_max_receives": 3
    },
    "embedding_generation": {
        "visibility_timeout": 300,  # 5분
        "message_retention": 86400,  # 1일
        "dlq_max_receives": 2
    }
}
```

### 4.4 SNS Client

#### 책임
- 이벤트 발행
- 알림 전송
- 팬아웃 메시징
- 구독 관리

#### 토픽 구조
```python
TOPICS = {
    "file_processing_events": {
        "subscribers": ["websocket_handler", "email_notifier"],
        "filter_policy": {"event_type": ["started", "completed", "failed"]}
    },
    "system_alerts": {
        "subscribers": ["ops_team", "monitoring_system"],
        "filter_policy": {"severity": ["high", "critical"]}
    }
}
```

## 5. 컴포넌트 간 상호작용

### 5.1 파일 처리 워크플로우

```
1. 사용자 파일 업로드 요청
   ↓
2. API Gateway → Knowledge Base Service
   ↓
3. S3 Repository에 파일 저장
   ↓
4. SQS에 처리 작업 메시지 전송
   ↓
5. Lambda 함수가 메시지 처리
   ↓
6. 처리 상태를 DynamoDB에 업데이트
   ↓
7. SNS로 완료 이벤트 발행
   ↓
8. WebSocket으로 사용자에게 알림
```

### 5.2 채팅 메시지 처리

```
1. WebSocket 메시지 수신
   ↓
2. Playground Service에서 메시지 처리
   ↓
3. Chat Repository에 메시지 저장
   ↓
4. Bedrock Client로 LLM 호출
   ↓
5. 스트리밍 응답을 WebSocket으로 전송
   ↓
6. 최종 응답을 Chat Repository에 저장
```

### 5.3 에이전트 실행 워크플로우

```
1. 에이전트 실행 요청
   ↓
2. Agent Service에서 요청 검증
   ↓
3. AgentCore Client로 실행 요청
   ↓
4. 실행 상태를 주기적으로 폴링
   ↓
5. 결과를 Agent Repository에 저장
   ↓
6. 완료 알림을 클라이언트에게 전송
```

## 6. 오류 처리 및 복구

### 6.1 서비스 레벨 오류 처리

#### 각 서비스별 오류 처리 전략
- **MCP Service**: 외부 서버 연결 실패 시 캐시된 도구 목록 반환
- **Knowledge Base Service**: 처리 실패 시 부분 결과 보존 및 재시도
- **Agent Service**: 실행 실패 시 상세 로그 수집 및 클라이언트 알림
- **Playground Service**: LLM 호출 실패 시 기본 응답 제공

### 6.2 데이터 일관성 보장

#### 보상 트랜잭션 패턴
```python
class CompensationTransaction:
    async def execute_with_compensation(self, operations: List[Operation]):
        completed_operations = []
        try:
            for operation in operations:
                await operation.execute()
                completed_operations.append(operation)
        except Exception as e:
            # 완료된 작업들을 역순으로 보상
            for operation in reversed(completed_operations):
                await operation.compensate()
            raise e
```

### 6.3 모니터링 및 알림

#### 컴포넌트별 헬스 체크
```python
class HealthChecker:
    async def check_component_health(self) -> HealthStatus:
        checks = {
            "database": await self.check_dynamodb(),
            "search": await self.check_opensearch(),
            "cache": await self.check_redis(),
            "storage": await self.check_s3(),
            "external_services": await self.check_external_services()
        }
        return HealthStatus(checks)
```

이 논리적 컴포넌트 설계는 NFR 요구사항을 충족하면서도 확장 가능하고 유지보수가 용이한 아키텍처를 제공합니다.
