# Backend API Service 도메인 엔티티 설계

## 도메인 엔티티 개요

### 엔티티 설계 원칙
- **단순성**: 복잡한 관계보다는 명확한 책임 분리
- **독립성**: 각 도메인 엔티티는 독립적으로 관리
- **확장성**: 향후 기능 추가를 고려한 유연한 구조
- **일관성**: 모든 엔티티에 공통 메타데이터 적용

---

## 1. MCP 도메인 엔티티

### 1.1 MCP 엔티티 (집합체 루트)
```python
@dataclass
class MCP:
    """MCP 집합체 루트"""
    
    # 식별자
    mcp_id: str
    
    # 기본 정보
    name: str
    description: str
    type: MCPType  # EXTERNAL, INTERNAL
    status: MCPStatus  # ACTIVE, INACTIVE, UPLOADING, DEPLOYING, FAILED
    version: str
    
    # 타입별 구성
    external_config: Optional[ExternalMCPConfig] = None
    internal_config: Optional[InternalMCPConfig] = None
    
    # 게이트웨이 정보
    gateway_id: Optional[str] = None
    gateway_targets: List[GatewayTarget] = field(default_factory=list)
    
    # 공통 메타데이터
    created_at: datetime
    updated_at: datetime
    owner: str
    tags: Dict[str, str] = field(default_factory=dict)
    
    def is_active(self) -> bool:
        return self.status == MCPStatus.ACTIVE
    
    def can_be_deleted(self) -> bool:
        return self.status in [MCPStatus.INACTIVE, MCPStatus.FAILED]
```

### 1.2 MCP 값 객체
```python
@dataclass(frozen=True)
class ExternalMCPConfig:
    """외부 MCP 구성 값 객체"""
    endpoint_url: str
    authentication: AuthConfig
    connection_timeout: int = 30
    health_check_interval: int = 300

@dataclass(frozen=True)
class InternalMCPConfig:
    """내부 MCP 구성 값 객체"""
    container_image_uri: str
    runtime_config: Dict[str, Any]
    resource_requirements: ResourceRequirements
    deployment_status: DeploymentStatus

@dataclass(frozen=True)
class GatewayTarget:
    """게이트웨이 타겟 값 객체"""
    target_id: str
    target_type: str  # LAMBDA, OPENAPI, SMITHY
    endpoint: str
    version: str
```

### 1.3 MCP 도구 엔티티
```python
@dataclass
class MCPTool:
    """MCP 도구 엔티티"""
    
    # 식별자
    tool_id: str
    mcp_id: str  # MCP 참조
    
    # 도구 정보
    name: str
    description: str
    schema: Dict[str, Any]  # JSON Schema
    
    # 메타데이터
    created_at: datetime
    updated_at: datetime
```

---

## 2. 지식베이스 도메인 엔티티

### 2.1 지식베이스 엔티티 (집합체 루트)
```python
@dataclass
class KnowledgeBase:
    """지식베이스 집합체 루트"""
    
    # 식별자
    kb_id: str
    
    # 기본 정보
    name: str
    description: str
    status: KBStatus  # ACTIVE, INACTIVE, CREATING, PROCESSING, FAILED
    
    # 저장소 구성
    s3_bucket: str
    s3_prefix: str
    opensearch_index: str
    
    # 처리 구성
    embedding_config: EmbeddingConfig
    
    # 통계
    total_documents: int = 0
    total_chunks: int = 0
    last_processed_at: Optional[datetime] = None
    
    # 공통 메타데이터
    created_at: datetime
    updated_at: datetime
    owner: str
    tags: Dict[str, str] = field(default_factory=dict)
    
    def is_ready_for_upload(self) -> bool:
        return self.status == KBStatus.ACTIVE
    
    def add_document_stats(self, chunks_count: int) -> None:
        self.total_documents += 1
        self.total_chunks += chunks_count
        self.last_processed_at = datetime.utcnow()
```

### 2.2 문서 엔티티
```python
@dataclass
class Document:
    """문서 엔티티"""
    
    # 식별자
    document_id: str
    kb_id: str  # KB 참조
    
    # 파일 정보
    filename: str
    file_size: int
    file_type: str
    file_hash: str
    s3_key: str
    
    # 처리 상태
    processing_status: ProcessingStatus
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    # 청킹 정보
    total_chunks: int = 0
    chunk_ids: List[str] = field(default_factory=list)
    
    # 메타데이터
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    
    def is_processing_complete(self) -> bool:
        return self.processing_status == ProcessingStatus.COMPLETED
    
    def mark_processing_failed(self, error: str) -> None:
        self.processing_status = ProcessingStatus.FAILED
        self.error_message = error
        self.processing_completed_at = datetime.utcnow()
```

### 2.3 KB 값 객체
```python
@dataclass(frozen=True)
class EmbeddingConfig:
    """임베딩 구성 값 객체"""
    model: str = "amazon.titan-embed-text-v1"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_chunks_per_document: int = 1000
```

---

## 3. 에이전트 도메인 엔티티

### 3.1 에이전트 엔티티 (집합체 루트)
```python
@dataclass
class Agent:
    """에이전트 집합체 루트"""
    
    # 식별자
    agent_id: str
    
    # 기본 정보
    name: str
    description: str
    status: AgentStatus  # DRAFT, ACTIVE, INACTIVE, DEPLOYING, FAILED
    
    # LLM 구성
    llm_config: LLMConfig
    
    # 도구 구성
    mcp_tools: List[MCPToolReference] = field(default_factory=list)
    kb_tools: List[KBToolReference] = field(default_factory=list)
    
    # 배포 정보
    deployment_info: Optional[DeploymentInfo] = None
    
    # 버전 관리
    current_version: str = "1.0.0"
    
    # 공통 메타데이터
    created_at: datetime
    updated_at: datetime
    deployed_at: Optional[datetime] = None
    owner: str
    tags: Dict[str, str] = field(default_factory=dict)
    
    def is_deployable(self) -> bool:
        return self.status in [AgentStatus.DRAFT, AgentStatus.INACTIVE]
    
    def is_active(self) -> bool:
        return self.status == AgentStatus.ACTIVE
    
    def add_mcp_tool(self, mcp_id: str, tool_names: List[str] = None) -> None:
        tool_ref = MCPToolReference(mcp_id=mcp_id, tool_names=tool_names or [])
        self.mcp_tools.append(tool_ref)
    
    def add_kb_tool(self, kb_id: str, search_config: SearchConfig) -> None:
        tool_ref = KBToolReference(kb_id=kb_id, search_config=search_config)
        self.kb_tools.append(tool_ref)
```

### 3.2 에이전트 값 객체
```python
@dataclass(frozen=True)
class LLMConfig:
    """LLM 구성 값 객체"""
    model: str
    system_instructions: str
    temperature: float = 0.7
    max_tokens: int = 4000
    top_p: float = 0.9

@dataclass(frozen=True)
class MCPToolReference:
    """MCP 도구 참조 값 객체"""
    mcp_id: str
    tool_names: List[str] = field(default_factory=list)  # 빈 리스트면 모든 도구
    configuration: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class KBToolReference:
    """KB 도구 참조 값 객체"""
    kb_id: str
    search_config: SearchConfig

@dataclass(frozen=True)
class SearchConfig:
    """검색 구성 값 객체"""
    max_results: int = 10
    similarity_threshold: float = 0.7
    search_type: str = "HYBRID"  # VECTOR, HYBRID, KEYWORD

@dataclass(frozen=True)
class DeploymentInfo:
    """배포 정보 값 객체"""
    agentcore_agent_id: str
    deployment_config: Dict[str, Any]
    deployed_version: str
```

### 3.3 에이전트 버전 엔티티
```python
@dataclass
class AgentVersion:
    """에이전트 버전 엔티티"""
    
    # 식별자
    version_id: str
    agent_id: str  # Agent 참조
    
    # 버전 정보
    version: str
    is_active: bool = False
    
    # 구성 스냅샷
    llm_config: LLMConfig
    mcp_tools: List[MCPToolReference]
    kb_tools: List[KBToolReference]
    
    # 메타데이터
    created_at: datetime
    created_by: str
```

---

## 4. 플레이그라운드 도메인 엔티티

### 4.1 채팅 세션 엔티티 (집합체 루트)
```python
@dataclass
class ChatSession:
    """채팅 세션 집합체 루트"""
    
    # 식별자
    session_id: str
    agent_id: str  # Agent 참조
    user_id: str
    
    # 세션 상태
    status: SessionStatus  # ACTIVE, INACTIVE, EXPIRED
    
    # 세션 설정
    max_messages: int = 100
    
    # 통계
    message_count: int = 0
    total_tokens: int = 0
    
    # 메타데이터
    created_at: datetime
    last_activity_at: datetime
    expires_at: Optional[datetime] = None
    
    def is_active(self) -> bool:
        return self.status == SessionStatus.ACTIVE
    
    def can_accept_messages(self) -> bool:
        return self.is_active() and self.message_count < self.max_messages
    
    def add_message_stats(self, token_count: int) -> None:
        self.message_count += 1
        self.total_tokens += token_count
        self.last_activity_at = datetime.utcnow()
```

### 4.2 채팅 메시지 엔티티
```python
@dataclass
class ChatMessage:
    """채팅 메시지 엔티티"""
    
    # 식별자
    message_id: str
    session_id: str  # Session 참조
    
    # 메시지 정보
    role: MessageRole  # USER, ASSISTANT, SYSTEM
    content: str
    
    # 메타데이터
    timestamp: datetime
    token_count: Optional[int] = None
    processing_time: Optional[float] = None
    
    # 도구 호출 정보
    tool_calls: List[ToolCall] = field(default_factory=list)
    
    def is_user_message(self) -> bool:
        return self.role == MessageRole.USER
    
    def is_assistant_message(self) -> bool:
        return self.role == MessageRole.ASSISTANT
```

### 4.3 플레이그라운드 값 객체
```python
@dataclass(frozen=True)
class ToolCall:
    """도구 호출 정보 값 객체"""
    tool_name: str
    tool_type: str  # MCP, KB
    parameters: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    execution_time: float = 0.0
```

---

## 5. 공통 엔티티 및 값 객체

### 5.1 공통 열거형
```python
class MCPType(Enum):
    EXTERNAL = "EXTERNAL"
    INTERNAL = "INTERNAL"

class MCPStatus(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    UPLOADING = "UPLOADING"
    DEPLOYING = "DEPLOYING"
    FAILED = "FAILED"

class KBStatus(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    CREATING = "CREATING"
    PROCESSING = "PROCESSING"
    FAILED = "FAILED"

class ProcessingStatus(Enum):
    PENDING = "PENDING"
    UPLOADING = "UPLOADING"
    EXTRACTING = "EXTRACTING"
    CHUNKING = "CHUNKING"
    EMBEDDING = "EMBEDDING"
    INDEXING = "INDEXING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class AgentStatus(Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DEPLOYING = "DEPLOYING"
    FAILED = "FAILED"

class SessionStatus(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    EXPIRED = "EXPIRED"

class MessageRole(Enum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"
    SYSTEM = "SYSTEM"
```

### 5.2 공통 값 객체
```python
@dataclass(frozen=True)
class AuthConfig:
    """인증 구성 값 객체"""
    auth_type: str  # NONE, API_KEY, OAUTH
    credentials: Dict[str, str] = field(default_factory=dict)

@dataclass(frozen=True)
class ResourceRequirements:
    """리소스 요구사항 값 객체"""
    cpu: str = "256"
    memory: str = "512"
    storage: str = "1024"

@dataclass(frozen=True)
class DeploymentStatus:
    """배포 상태 값 객체"""
    status: str
    message: str
    last_updated: datetime
```

---

## 엔티티 관계 다이어그램

```
MCP (1) -----> (*) MCPTool
    ^
    |
    | (참조)
    |
Agent (1) -----> (*) AgentVersion
    |
    | (1:*)
    v
ChatSession (1) -----> (*) ChatMessage

KnowledgeBase (1) -----> (*) Document
    ^
    |
    | (참조)
    |
Agent
```

## 엔티티 제약사항

### 1. 비즈니스 규칙 제약사항
- MCP 이름은 고유해야 함
- KB 이름은 고유해야 함
- Agent 이름은 고유해야 함
- 활성 상태의 리소스만 참조 가능

### 2. 데이터 무결성 제약사항
- 외래 키 참조 무결성 보장
- 상태 전환 규칙 준수
- 필수 필드 존재 확인

### 3. 성능 제약사항
- 세션당 최대 메시지 수 제한
- 문서당 최대 청크 수 제한
- 에이전트당 최대 도구 수 제한
