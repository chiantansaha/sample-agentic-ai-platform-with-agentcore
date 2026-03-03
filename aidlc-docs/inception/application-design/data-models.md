# 데이터 모델 및 스키마 설계

## 데이터 저장소 아키텍처

### 저장소 전략
- **DynamoDB**: 메타데이터 및 구조화된 데이터
- **OpenSearch**: 벡터 검색 및 전문 검색
- **S3**: 파일 저장 및 정적 자산
- **ElastiCache**: 세션 및 캐시 데이터

---

## 1. MCP 관리 데이터 모델

### 1.1 MCP 메타데이터 (DynamoDB)

#### MCP 테이블
```python
class MCPModel:
    """MCP 메타데이터 모델"""
    
    # Primary Key
    mcp_id: str  # PK: "mcp#{uuid}"
    
    # 기본 정보
    name: str
    description: str
    type: MCPType  # INTERNAL, EXTERNAL
    status: MCPStatus  # ACTIVE, INACTIVE, DEPLOYING, ERROR
    
    # 버전 관리
    version: str
    created_at: datetime
    updated_at: datetime
    
    # 타입별 구성
    internal_config: Optional[InternalMCPConfig]
    external_config: Optional[ExternalMCPConfig]
    
    # 게이트웨이 정보
    gateway_id: Optional[str]
    gateway_targets: List[GatewayTarget]
    
    # 메타데이터
    tags: Dict[str, str]
    owner: str

class InternalMCPConfig:
    """내부 MCP 구성"""
    container_image_uri: str
    runtime_config: Dict[str, Any]
    deployment_status: DeploymentStatus
    resource_requirements: ResourceRequirements

class ExternalMCPConfig:
    """외부 MCP 구성"""
    endpoint_url: str
    authentication: AuthConfig
    connection_status: ConnectionStatus
    health_check_config: HealthCheckConfig

class GatewayTarget:
    """게이트웨이 타겟"""
    target_id: str
    target_type: str  # LAMBDA, OPENAPI, SMITHY
    endpoint: str
    version: str
```

#### MCP 도구 테이블
```python
class MCPToolModel:
    """MCP 도구 모델"""
    
    # Primary Key
    tool_id: str  # PK: "tool#{mcp_id}#{tool_name}"
    mcp_id: str   # GSI1PK
    
    # 도구 정보
    name: str
    description: str
    schema: Dict[str, Any]  # JSON Schema
    
    # 메타데이터
    created_at: datetime
    updated_at: datetime
```

### 1.2 MCP 인덱스 구조

#### 기본 테이블 인덱스
- **PK**: `mcp_id`
- **GSI1**: `type` (PK) + `status` (SK) - 타입별 상태 조회
- **GSI2**: `owner` (PK) + `created_at` (SK) - 소유자별 조회

#### 도구 테이블 인덱스
- **PK**: `tool_id`
- **GSI1**: `mcp_id` (PK) + `name` (SK) - MCP별 도구 조회

---

## 2. 지식베이스 관리 데이터 모델

### 2.1 지식베이스 메타데이터 (DynamoDB)

#### 지식베이스 테이블
```python
class KnowledgeBaseModel:
    """지식베이스 메타데이터 모델"""
    
    # Primary Key
    kb_id: str  # PK: "kb#{uuid}"
    
    # 기본 정보
    name: str
    description: str
    status: KBStatus  # ACTIVE, INACTIVE, PROCESSING, ERROR
    
    # 저장소 구성
    s3_bucket: str
    s3_prefix: str
    opensearch_index: str
    
    # 처리 구성
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    
    # 통계
    total_documents: int
    total_chunks: int
    last_processed_at: Optional[datetime]
    
    # 메타데이터
    created_at: datetime
    updated_at: datetime
    tags: Dict[str, str]
    owner: str

class DocumentModel:
    """문서 메타데이터 모델"""
    
    # Primary Key
    document_id: str  # PK: "doc#{kb_id}#{file_hash}"
    kb_id: str        # GSI1PK
    
    # 파일 정보
    filename: str
    file_size: int
    file_type: str
    s3_key: str
    
    # 처리 상태
    processing_status: ProcessingStatus  # PENDING, PROCESSING, COMPLETED, FAILED
    processing_started_at: Optional[datetime]
    processing_completed_at: Optional[datetime]
    error_message: Optional[str]
    
    # 청킹 정보
    total_chunks: int
    chunk_ids: List[str]
    
    # 메타데이터
    uploaded_at: datetime
    processed_at: Optional[datetime]
```

### 2.2 벡터 데이터 (OpenSearch)

#### 문서 청크 인덱스
```json
{
  "mappings": {
    "properties": {
      "chunk_id": {"type": "keyword"},
      "document_id": {"type": "keyword"},
      "kb_id": {"type": "keyword"},
      "content": {"type": "text"},
      "embedding": {
        "type": "dense_vector",
        "dims": 1536,
        "index": true,
        "similarity": "cosine"
      },
      "metadata": {
        "properties": {
          "filename": {"type": "keyword"},
          "page_number": {"type": "integer"},
          "chunk_index": {"type": "integer"},
          "created_at": {"type": "date"}
        }
      }
    }
  }
}
```

### 2.3 지식베이스 인덱스 구조

#### 기본 테이블 인덱스
- **PK**: `kb_id`
- **GSI1**: `owner` (PK) + `created_at` (SK) - 소유자별 조회
- **GSI2**: `status` (PK) + `updated_at` (SK) - 상태별 조회

#### 문서 테이블 인덱스
- **PK**: `document_id`
- **GSI1**: `kb_id` (PK) + `uploaded_at` (SK) - KB별 문서 조회
- **GSI2**: `processing_status` (PK) + `processing_started_at` (SK) - 처리 상태별 조회

---

## 3. 에이전트 관리 데이터 모델

### 3.1 에이전트 메타데이터 (DynamoDB)

#### 에이전트 테이블
```python
class AgentModel:
    """에이전트 메타데이터 모델"""
    
    # Primary Key
    agent_id: str  # PK: "agent#{uuid}"
    
    # 기본 정보
    name: str
    description: str
    status: AgentStatus  # DRAFT, ACTIVE, INACTIVE, DEPLOYING, ERROR
    
    # LLM 구성
    llm_model: str
    system_instructions: str
    temperature: float
    max_tokens: int
    
    # 도구 구성
    mcp_tools: List[MCPToolReference]
    kb_tools: List[KBToolReference]
    
    # 배포 정보
    deployment_status: DeploymentStatus
    agentcore_agent_id: Optional[str]
    deployment_config: Dict[str, Any]
    
    # 메타데이터
    created_at: datetime
    updated_at: datetime
    deployed_at: Optional[datetime]
    tags: Dict[str, str]
    owner: str

class MCPToolReference:
    """MCP 도구 참조"""
    mcp_id: str
    tool_names: List[str]  # 빈 리스트면 모든 도구
    configuration: Dict[str, Any]

class KBToolReference:
    """지식베이스 도구 참조"""
    kb_id: str
    search_config: SearchConfig

class SearchConfig:
    """검색 구성"""
    max_results: int
    similarity_threshold: float
    search_type: str  # VECTOR, HYBRID, KEYWORD
```

#### 에이전트 버전 테이블
```python
class AgentVersionModel:
    """에이전트 버전 모델"""
    
    # Primary Key
    version_id: str  # PK: "version#{agent_id}#{version}"
    agent_id: str    # GSI1PK
    
    # 버전 정보
    version: str
    is_active: bool
    
    # 구성 스냅샷
    configuration: AgentConfiguration
    
    # 메타데이터
    created_at: datetime
    created_by: str
```

### 3.2 에이전트 인덱스 구조

#### 기본 테이블 인덱스
- **PK**: `agent_id`
- **GSI1**: `owner` (PK) + `created_at` (SK) - 소유자별 조회
- **GSI2**: `status` (PK) + `updated_at` (SK) - 상태별 조회

#### 버전 테이블 인덱스
- **PK**: `version_id`
- **GSI1**: `agent_id` (PK) + `version` (SK) - 에이전트별 버전 조회

---

## 4. 플레이그라운드 데이터 모델

### 4.1 채팅 세션 (ElastiCache)

#### 세션 데이터 구조
```python
class ChatSession:
    """채팅 세션 모델"""
    
    # 세션 식별
    session_id: str
    agent_id: str
    user_id: str
    
    # 세션 상태
    status: SessionStatus  # ACTIVE, INACTIVE, EXPIRED
    created_at: datetime
    last_activity_at: datetime
    expires_at: datetime
    
    # 채팅 기록
    messages: List[ChatMessage]
    
    # 컨텍스트
    context: Dict[str, Any]
    
    # 설정
    max_messages: int
    ttl_seconds: int

class ChatMessage:
    """채팅 메시지 모델"""
    
    message_id: str
    timestamp: datetime
    role: MessageRole  # USER, ASSISTANT, SYSTEM
    content: str
    
    # 메타데이터
    token_count: Optional[int]
    processing_time: Optional[float]
    tool_calls: Optional[List[ToolCall]]
    
class ToolCall:
    """도구 호출 정보"""
    
    tool_name: str
    tool_type: str  # MCP, KB
    parameters: Dict[str, Any]
    result: Optional[Dict[str, Any]]
    execution_time: float
```

### 4.2 채팅 기록 (DynamoDB)

#### 채팅 기록 테이블 (장기 보관용)
```python
class ChatHistoryModel:
    """채팅 기록 모델 (장기 보관)"""
    
    # Primary Key
    history_id: str  # PK: "history#{session_id}#{timestamp}"
    session_id: str  # GSI1PK
    
    # 세션 정보
    agent_id: str
    user_id: str
    
    # 메시지 배치
    messages: List[ChatMessage]
    message_count: int
    
    # 통계
    total_tokens: int
    total_processing_time: float
    
    # 메타데이터
    created_at: datetime
    archived_at: datetime
```

---

## 5. 공통 데이터 모델

### 5.1 사용자 관리 (향후 확장용)

#### 사용자 테이블
```python
class UserModel:
    """사용자 모델 (향후 확장)"""
    
    # Primary Key
    user_id: str  # PK: "user#{uuid}"
    
    # 기본 정보
    username: str
    email: str
    display_name: str
    
    # 권한
    roles: List[str]
    permissions: List[str]
    
    # 메타데이터
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime]
```

### 5.2 시스템 구성

#### 시스템 구성 테이블
```python
class SystemConfigModel:
    """시스템 구성 모델"""
    
    # Primary Key
    config_key: str  # PK: "config#{category}#{key}"
    
    # 구성 값
    value: str
    value_type: str  # STRING, INTEGER, BOOLEAN, JSON
    
    # 메타데이터
    description: str
    is_sensitive: bool
    created_at: datetime
    updated_at: datetime
```

---

## 데이터 액세스 패턴

### 1. MCP 관리 패턴

#### 조회 패턴
```python
# 모든 MCP 조회 (페이지네이션)
query_params = {
    'IndexName': 'GSI1',
    'KeyConditionExpression': 'type = :type',
    'ExpressionAttributeValues': {':type': 'INTERNAL'}
}

# 사용자별 MCP 조회
query_params = {
    'IndexName': 'GSI2',
    'KeyConditionExpression': 'owner = :owner',
    'ExpressionAttributeValues': {':owner': 'user123'}
}

# MCP 도구 조회
query_params = {
    'IndexName': 'GSI1',
    'KeyConditionExpression': 'mcp_id = :mcp_id',
    'ExpressionAttributeValues': {':mcp_id': 'mcp#123'}
}
```

### 2. 지식베이스 관리 패턴

#### 벡터 검색 패턴
```python
# OpenSearch 벡터 검색
search_body = {
    "query": {
        "script_score": {
            "query": {"match_all": {}},
            "script": {
                "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                "params": {"query_vector": query_embedding}
            }
        }
    },
    "size": 10,
    "_source": ["content", "metadata"]
}

# 하이브리드 검색 (벡터 + 키워드)
search_body = {
    "query": {
        "bool": {
            "should": [
                {
                    "script_score": {
                        "query": {"match_all": {}},
                        "script": {
                            "source": "cosineSimilarity(params.query_vector, 'embedding')",
                            "params": {"query_vector": query_embedding}
                        }
                    }
                },
                {
                    "match": {
                        "content": {
                            "query": "search_text",
                            "boost": 0.3
                        }
                    }
                }
            ]
        }
    }
}
```

### 3. 에이전트 관리 패턴

#### 에이전트 구성 조회
```python
# 에이전트 상세 정보 (도구 포함)
async def get_agent_with_tools(agent_id: str) -> AgentWithTools:
    # 1. 에이전트 기본 정보 조회
    agent = await dynamodb.get_item(Key={'agent_id': agent_id})
    
    # 2. MCP 도구 정보 조회
    mcp_tools = []
    for mcp_ref in agent.mcp_tools:
        mcp_info = await dynamodb.get_item(Key={'mcp_id': mcp_ref.mcp_id})
        tools = await dynamodb.query(
            IndexName='GSI1',
            KeyConditionExpression='mcp_id = :mcp_id',
            ExpressionAttributeValues={':mcp_id': mcp_ref.mcp_id}
        )
        mcp_tools.append({'mcp': mcp_info, 'tools': tools})
    
    # 3. KB 도구 정보 조회
    kb_tools = []
    for kb_ref in agent.kb_tools:
        kb_info = await dynamodb.get_item(Key={'kb_id': kb_ref.kb_id})
        kb_tools.append({'kb': kb_info, 'config': kb_ref.search_config})
    
    return AgentWithTools(agent=agent, mcp_tools=mcp_tools, kb_tools=kb_tools)
```

### 4. 플레이그라운드 패턴

#### 세션 관리 패턴
```python
# 세션 생성 및 TTL 설정
await redis.setex(
    f"session:{session_id}",
    ttl_seconds,
    json.dumps(session_data)
)

# 메시지 추가 (리스트 구조)
await redis.lpush(f"messages:{session_id}", json.dumps(message))
await redis.ltrim(f"messages:{session_id}", 0, max_messages - 1)

# 세션 기록 아카이브 (배치 처리)
async def archive_expired_sessions():
    expired_sessions = await redis.scan_iter(match="session:*")
    for session_key in expired_sessions:
        session_data = await redis.get(session_key)
        if session_data:
            # DynamoDB에 아카이브
            await dynamodb.put_item(Item=archive_data)
            await redis.delete(session_key)
```

---

## 데이터 일관성 및 트랜잭션

### 1. 트랜잭션 패턴

#### MCP 생성 트랜잭션
```python
async def create_mcp_transaction(mcp_data: MCPCreateData) -> MCPModel:
    """MCP 생성 트랜잭션"""
    
    # DynamoDB 트랜잭션
    transaction_items = [
        {
            'Put': {
                'TableName': 'MCP',
                'Item': mcp_item,
                'ConditionExpression': 'attribute_not_exists(mcp_id)'
            }
        }
    ]
    
    # 도구가 있는 경우 함께 생성
    for tool in mcp_data.tools:
        transaction_items.append({
            'Put': {
                'TableName': 'MCPTool',
                'Item': tool_item
            }
        })
    
    await dynamodb.transact_write_items(TransactItems=transaction_items)
```

### 2. 이벤트 기반 일관성

#### 도메인 이벤트 패턴
```python
class DomainEvent:
    """도메인 이벤트 기본 클래스"""
    event_id: str
    event_type: str
    aggregate_id: str
    timestamp: datetime
    data: Dict[str, Any]

class MCPCreatedEvent(DomainEvent):
    """MCP 생성 이벤트"""
    event_type = "MCP_CREATED"

class KBProcessingCompletedEvent(DomainEvent):
    """KB 처리 완료 이벤트"""
    event_type = "KB_PROCESSING_COMPLETED"

# 이벤트 핸들러
async def handle_mcp_created(event: MCPCreatedEvent):
    """MCP 생성 이벤트 처리"""
    # 게이트웨이 생성
    # 알림 발송
    # 감사 로그 기록
    pass
```

---

## 성능 최적화 전략

### 1. 캐싱 전략
- **L1 캐시**: 애플리케이션 메모리 캐시
- **L2 캐시**: ElastiCache (Redis)
- **캐시 무효화**: 이벤트 기반 무효화

### 2. 인덱스 최적화
- **GSI 설계**: 쿼리 패턴에 맞는 GSI 구성
- **복합 키**: 범위 쿼리를 위한 복합 정렬 키
- **희소 인덱스**: 선택적 속성을 위한 희소 인덱스

### 3. 배치 처리
- **배치 읽기**: BatchGetItem 사용
- **배치 쓰기**: BatchWriteItem 사용
- **트랜잭션 배치**: TransactWriteItems 사용
