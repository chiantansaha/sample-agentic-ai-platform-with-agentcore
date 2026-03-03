# Backend API Service 비즈니스 규칙 정의

## 비즈니스 규칙 개요

### 규칙 적용 원칙
- **단순성**: 복잡한 규칙보다는 명확하고 이해하기 쉬운 규칙
- **일관성**: 모든 도메인에 일관된 규칙 적용 패턴
- **확장성**: 향후 규칙 추가 및 변경이 용이한 구조
- **검증 가능성**: 모든 규칙은 자동화된 검증 가능

---

## 1. MCP 도메인 비즈니스 규칙

### 1.1 MCP 등록 규칙

#### BR-MCP-001: MCP 이름 고유성
```python
async def validate_mcp_name_uniqueness(name: str, exclude_id: str = None) -> ValidationResult:
    """MCP 이름 고유성 검증"""
    existing_mcp = await get_mcp_by_name(name)
    
    if existing_mcp and existing_mcp.mcp_id != exclude_id:
        return ValidationResult(
            is_valid=False,
            errors=["MCP name must be unique"]
        )
    
    return ValidationResult(is_valid=True)
```

#### BR-MCP-002: MCP 이름 형식 규칙
```python
def validate_mcp_name_format(name: str) -> ValidationResult:
    """MCP 이름 형식 검증"""
    errors = []
    
    # 길이 제한 (3-50자)
    if len(name) < 3 or len(name) > 50:
        errors.append("MCP name must be between 3 and 50 characters")
    
    # 허용된 문자만 사용 (영문, 숫자, 하이픈, 언더스코어)
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        errors.append("MCP name can only contain letters, numbers, hyphens, and underscores")
    
    # 영문자로 시작
    if not name[0].isalpha():
        errors.append("MCP name must start with a letter")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors
    )
```

#### BR-MCP-003: 외부 MCP 연결 검증
```python
async def validate_external_mcp_connection(endpoint_url: str) -> ValidationResult:
    """외부 MCP 연결 검증"""
    try:
        # 기본 연결 테스트 (30초 타임아웃)
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.get(f"{endpoint_url}/health") as response:
                if response.status == 200:
                    return ValidationResult(is_valid=True)
                else:
                    return ValidationResult(
                        is_valid=False,
                        errors=[f"MCP endpoint returned status {response.status}"]
                    )
    except Exception as e:
        return ValidationResult(
            is_valid=False,
            errors=[f"Cannot connect to MCP endpoint: {str(e)}"]
        )
```

### 1.2 MCP 상태 전환 규칙

#### BR-MCP-004: 유효한 상태 전환
```python
VALID_MCP_STATUS_TRANSITIONS = {
    MCPStatus.UPLOADING: [MCPStatus.ACTIVE, MCPStatus.FAILED],
    MCPStatus.DEPLOYING: [MCPStatus.ACTIVE, MCPStatus.FAILED],
    MCPStatus.ACTIVE: [MCPStatus.INACTIVE, MCPStatus.FAILED],
    MCPStatus.INACTIVE: [MCPStatus.ACTIVE, MCPStatus.DEPLOYING],
    MCPStatus.FAILED: [MCPStatus.DEPLOYING, MCPStatus.INACTIVE]
}

def validate_mcp_status_transition(current_status: MCPStatus, new_status: MCPStatus) -> ValidationResult:
    """MCP 상태 전환 유효성 검증"""
    if current_status == new_status:
        return ValidationResult(is_valid=True)  # 동일 상태는 허용
    
    valid_transitions = VALID_MCP_STATUS_TRANSITIONS.get(current_status, [])
    
    if new_status not in valid_transitions:
        return ValidationResult(
            is_valid=False,
            errors=[f"Invalid status transition from {current_status} to {new_status}"]
        )
    
    return ValidationResult(is_valid=True)
```

### 1.3 MCP 삭제 규칙

#### BR-MCP-005: MCP 삭제 가능 조건
```python
async def validate_mcp_deletion(mcp_id: str) -> ValidationResult:
    """MCP 삭제 가능성 검증"""
    mcp = await get_mcp_by_id(mcp_id)
    if not mcp:
        return ValidationResult(
            is_valid=False,
            errors=["MCP not found"]
        )
    
    errors = []
    
    # 활성 상태인 MCP는 삭제 불가
    if mcp.status == MCPStatus.ACTIVE:
        errors.append("Cannot delete active MCP. Deactivate first.")
    
    # 에이전트에서 사용 중인 MCP는 삭제 불가
    using_agents = await get_agents_using_mcp(mcp_id)
    if using_agents:
        agent_names = [agent.name for agent in using_agents]
        errors.append(f"MCP is being used by agents: {', '.join(agent_names)}")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors
    )
```

---

## 2. 지식베이스 도메인 비즈니스 규칙

### 2.1 지식베이스 생성 규칙

#### BR-KB-001: KB 이름 고유성 및 형식
```python
async def validate_kb_name(name: str, exclude_id: str = None) -> ValidationResult:
    """KB 이름 검증 (고유성 + 형식)"""
    errors = []
    
    # 형식 검증
    if len(name) < 3 or len(name) > 50:
        errors.append("KB name must be between 3 and 50 characters")
    
    if not re.match(r'^[a-zA-Z0-9_-\s]+$', name):
        errors.append("KB name can only contain letters, numbers, spaces, hyphens, and underscores")
    
    # 고유성 검증
    existing_kb = await get_kb_by_name(name)
    if existing_kb and existing_kb.kb_id != exclude_id:
        errors.append("KB name must be unique")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors
    )
```

### 2.2 파일 업로드 규칙

#### BR-KB-002: 지원 파일 형식
```python
SUPPORTED_FILE_TYPES = {
    '.pdf': 'application/pdf',
    '.txt': 'text/plain',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.md': 'text/markdown'
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def validate_file_upload(file: UploadFile) -> ValidationResult:
    """파일 업로드 검증"""
    errors = []
    
    # 파일 크기 검증
    if file.size > MAX_FILE_SIZE:
        errors.append(f"File size must be less than {MAX_FILE_SIZE // (1024*1024)}MB")
    
    # 파일 형식 검증
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in SUPPORTED_FILE_TYPES:
        supported_formats = ', '.join(SUPPORTED_FILE_TYPES.keys())
        errors.append(f"Unsupported file format. Supported formats: {supported_formats}")
    
    # 파일명 검증
    if not file.filename or len(file.filename) > 255:
        errors.append("Invalid filename")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors
    )
```

#### BR-KB-003: 중복 파일 처리
```python
async def validate_file_duplication(kb_id: str, file_hash: str) -> ValidationResult:
    """파일 중복 검증"""
    existing_doc = await get_document_by_hash(kb_id, file_hash)
    
    if existing_doc:
        return ValidationResult(
            is_valid=False,
            errors=["File already exists in knowledge base"],
            metadata={"existing_document_id": existing_doc.document_id}
        )
    
    return ValidationResult(is_valid=True)
```

### 2.3 처리 상태 전환 규칙

#### BR-KB-004: 문서 처리 상태 전환
```python
VALID_PROCESSING_TRANSITIONS = {
    ProcessingStatus.PENDING: [ProcessingStatus.UPLOADING, ProcessingStatus.FAILED],
    ProcessingStatus.UPLOADING: [ProcessingStatus.EXTRACTING, ProcessingStatus.FAILED],
    ProcessingStatus.EXTRACTING: [ProcessingStatus.CHUNKING, ProcessingStatus.FAILED],
    ProcessingStatus.CHUNKING: [ProcessingStatus.EMBEDDING, ProcessingStatus.FAILED],
    ProcessingStatus.EMBEDDING: [ProcessingStatus.INDEXING, ProcessingStatus.FAILED],
    ProcessingStatus.INDEXING: [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED],
    ProcessingStatus.FAILED: [ProcessingStatus.PENDING]  # 재처리 가능
}

def validate_processing_status_transition(current: ProcessingStatus, new: ProcessingStatus) -> ValidationResult:
    """문서 처리 상태 전환 검증"""
    if current == new:
        return ValidationResult(is_valid=True)
    
    valid_transitions = VALID_PROCESSING_TRANSITIONS.get(current, [])
    
    if new not in valid_transitions:
        return ValidationResult(
            is_valid=False,
            errors=[f"Invalid processing transition from {current} to {new}"]
        )
    
    return ValidationResult(is_valid=True)
```

---

## 3. 에이전트 도메인 비즈니스 규칙

### 3.1 에이전트 생성 규칙

#### BR-AGENT-001: 에이전트 이름 및 기본 검증
```python
async def validate_agent_basic_info(agent_data: AgentCreateData) -> ValidationResult:
    """에이전트 기본 정보 검증"""
    errors = []
    
    # 이름 검증
    if not agent_data.name or len(agent_data.name) < 3 or len(agent_data.name) > 50:
        errors.append("Agent name must be between 3 and 50 characters")
    
    # 이름 고유성
    existing_agent = await get_agent_by_name(agent_data.name)
    if existing_agent:
        errors.append("Agent name must be unique")
    
    # 설명 검증
    if not agent_data.description or len(agent_data.description) > 500:
        errors.append("Agent description is required and must be less than 500 characters")
    
    # LLM 모델 검증
    if not agent_data.llm_config.model:
        errors.append("LLM model is required")
    
    # 시스템 지시사항 검증
    if not agent_data.llm_config.system_instructions:
        errors.append("System instructions are required")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors
    )
```

#### BR-AGENT-002: 도구 참조 검증 (기본)
```python
async def validate_agent_tool_references(agent_data: AgentCreateData) -> ValidationResult:
    """에이전트 도구 참조 기본 검증"""
    errors = []
    
    # MCP 도구 검증
    for mcp_tool in agent_data.mcp_tools:
        if not mcp_tool.mcp_id:
            errors.append("MCP ID is required for MCP tools")
            continue
        
        # MCP 존재 확인 (기본 검증)
        mcp = await get_mcp_by_id(mcp_tool.mcp_id)
        if not mcp:
            errors.append(f"MCP {mcp_tool.mcp_id} not found")
    
    # KB 도구 검증
    for kb_tool in agent_data.kb_tools:
        if not kb_tool.kb_id:
            errors.append("KB ID is required for KB tools")
            continue
        
        # KB 존재 확인 (기본 검증)
        kb = await get_kb_by_id(kb_tool.kb_id)
        if not kb:
            errors.append(f"Knowledge base {kb_tool.kb_id} not found")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors
    )
```

### 3.2 에이전트 배포 규칙

#### BR-AGENT-003: 배포 가능 조건
```python
async def validate_agent_deployment_readiness(agent_id: str) -> ValidationResult:
    """에이전트 배포 준비 상태 검증"""
    agent = await get_agent_by_id(agent_id)
    if not agent:
        return ValidationResult(
            is_valid=False,
            errors=["Agent not found"]
        )
    
    errors = []
    
    # 상태 확인
    if agent.status not in [AgentStatus.DRAFT, AgentStatus.INACTIVE]:
        errors.append("Agent must be in DRAFT or INACTIVE status to deploy")
    
    # 필수 구성 확인
    if not agent.llm_config.model:
        errors.append("LLM model configuration is required")
    
    if not agent.llm_config.system_instructions:
        errors.append("System instructions are required")
    
    # 참조된 리소스 활성 상태 확인 (기본 검증)
    for mcp_tool in agent.mcp_tools:
        mcp = await get_mcp_by_id(mcp_tool.mcp_id)
        if not mcp or mcp.status != MCPStatus.ACTIVE:
            errors.append(f"Referenced MCP {mcp_tool.mcp_id} is not active")
    
    for kb_tool in agent.kb_tools:
        kb = await get_kb_by_id(kb_tool.kb_id)
        if not kb or kb.status != KBStatus.ACTIVE:
            errors.append(f"Referenced KB {kb_tool.kb_id} is not active")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors
    )
```

---

## 4. 플레이그라운드 도메인 비즈니스 규칙

### 4.1 세션 생성 규칙

#### BR-PLAY-001: 세션 생성 조건
```python
async def validate_session_creation(agent_id: str, user_id: str) -> ValidationResult:
    """세션 생성 조건 검증"""
    errors = []
    
    # 에이전트 존재 및 활성 상태 확인
    agent = await get_agent_by_id(agent_id)
    if not agent:
        errors.append("Agent not found")
    elif agent.status != AgentStatus.ACTIVE:
        errors.append("Agent is not active")
    
    # 사용자 ID 검증
    if not user_id or len(user_id) < 1:
        errors.append("User ID is required")
    
    # 동일 사용자의 활성 세션 수 제한 (최대 5개)
    active_sessions = await get_active_sessions_by_user(user_id)
    if len(active_sessions) >= 5:
        errors.append("Maximum number of active sessions reached (5)")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors
    )
```

### 4.2 메시지 처리 규칙

#### BR-PLAY-002: 메시지 검증
```python
def validate_chat_message(message: str) -> ValidationResult:
    """채팅 메시지 검증"""
    errors = []
    
    # 메시지 길이 제한
    if not message or len(message.strip()) == 0:
        errors.append("Message cannot be empty")
    
    if len(message) > 4000:
        errors.append("Message must be less than 4000 characters")
    
    # 금지된 내용 검사 (기본적인 필터링)
    prohibited_patterns = [
        r'<script.*?>.*?</script>',  # 스크립트 태그
        r'javascript:',              # 자바스크립트 프로토콜
    ]
    
    for pattern in prohibited_patterns:
        if re.search(pattern, message, re.IGNORECASE):
            errors.append("Message contains prohibited content")
            break
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors
    )
```

#### BR-PLAY-003: 세션 메시지 제한
```python
async def validate_session_message_limit(session_id: str) -> ValidationResult:
    """세션 메시지 수 제한 검증"""
    session = await get_session_by_id(session_id)
    if not session:
        return ValidationResult(
            is_valid=False,
            errors=["Session not found"]
        )
    
    if session.message_count >= session.max_messages:
        return ValidationResult(
            is_valid=False,
            errors=[f"Session has reached maximum message limit ({session.max_messages})"]
        )
    
    return ValidationResult(is_valid=True)
```

---

## 5. 공통 비즈니스 규칙

### 5.1 데이터 일관성 규칙

#### BR-COMMON-001: 보상 트랜잭션 규칙
```python
class BusinessTransaction:
    """비즈니스 트랜잭션 관리"""
    
    def __init__(self):
        self.operations = []
        self.compensations = []
    
    def add_operation(self, operation: Callable, compensation: Callable, *args, **kwargs):
        """작업과 보상 액션 추가"""
        self.operations.append((operation, args, kwargs))
        self.compensations.append((compensation, args, kwargs))
    
    async def execute(self):
        """트랜잭션 실행"""
        completed_operations = []
        
        try:
            for i, (operation, args, kwargs) in enumerate(self.operations):
                result = await operation(*args, **kwargs)
                completed_operations.append(i)
                
            return True
            
        except Exception as e:
            # 실패 시 완료된 작업들에 대해 보상 실행
            for i in reversed(completed_operations):
                compensation, args, kwargs = self.compensations[i]
                try:
                    await compensation(*args, **kwargs)
                except Exception as comp_error:
                    logger.error(f"Compensation failed: {comp_error}")
            
            raise e
```

### 5.2 오류 처리 규칙

#### BR-COMMON-002: 구조화된 오류 응답
```python
class BusinessRuleViolation(Exception):
    """비즈니스 규칙 위반 예외"""
    
    def __init__(self, rule_code: str, message: str, details: Dict = None):
        self.rule_code = rule_code
        self.message = message
        self.details = details or {}
        super().__init__(message)
    
    def to_api_error(self) -> APIError:
        return APIError(
            code=self.rule_code,
            message=self.message,
            details=self.details
        )

# 비즈니스 규칙 코드 정의
class BusinessRuleCodes:
    # MCP 관련
    MCP_NAME_NOT_UNIQUE = "BR_MCP_001"
    MCP_INVALID_NAME_FORMAT = "BR_MCP_002"
    MCP_CONNECTION_FAILED = "BR_MCP_003"
    MCP_INVALID_STATUS_TRANSITION = "BR_MCP_004"
    MCP_CANNOT_DELETE = "BR_MCP_005"
    
    # KB 관련
    KB_NAME_NOT_UNIQUE = "BR_KB_001"
    KB_UNSUPPORTED_FILE_TYPE = "BR_KB_002"
    KB_FILE_ALREADY_EXISTS = "BR_KB_003"
    KB_INVALID_PROCESSING_TRANSITION = "BR_KB_004"
    
    # Agent 관련
    AGENT_INVALID_BASIC_INFO = "BR_AGENT_001"
    AGENT_INVALID_TOOL_REFERENCE = "BR_AGENT_002"
    AGENT_NOT_DEPLOYABLE = "BR_AGENT_003"
    
    # Playground 관련
    PLAY_INVALID_SESSION_CREATION = "BR_PLAY_001"
    PLAY_INVALID_MESSAGE = "BR_PLAY_002"
    PLAY_SESSION_MESSAGE_LIMIT = "BR_PLAY_003"
```

### 5.3 검증 결과 표준화

#### BR-COMMON-003: 검증 결과 구조
```python
@dataclass
class ValidationResult:
    """표준 검증 결과"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, error: str) -> None:
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str) -> None:
        self.warnings.append(warning)
    
    def merge(self, other: 'ValidationResult') -> 'ValidationResult':
        """다른 검증 결과와 병합"""
        return ValidationResult(
            is_valid=self.is_valid and other.is_valid,
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings,
            metadata={**self.metadata, **other.metadata}
        )
```

---

## 비즈니스 규칙 적용 패턴

### 1. 규칙 실행 순서
1. **형식 검증**: 데이터 형식 및 타입 검증
2. **비즈니스 규칙**: 도메인별 비즈니스 규칙 적용
3. **참조 무결성**: 외부 참조 유효성 검증
4. **상태 일관성**: 상태 전환 및 일관성 검증

### 2. 규칙 위반 처리
1. **즉시 실패**: 중요한 규칙 위반 시 즉시 처리 중단
2. **경고 수집**: 경미한 위반은 경고로 수집
3. **보상 실행**: 부분 실패 시 보상 트랜잭션 실행
4. **구조화된 응답**: 일관된 오류 응답 형식 제공

### 3. 규칙 확장성
- 새로운 규칙 추가 시 기존 규칙과의 충돌 방지
- 규칙 버전 관리 및 하위 호환성 보장
- 규칙별 활성화/비활성화 기능 제공
