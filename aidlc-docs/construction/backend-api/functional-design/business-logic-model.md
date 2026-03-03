# Backend API Service 비즈니스 로직 모델

## 비즈니스 로직 설계 원칙

### 설계 결정 요약
- **MCP 등록**: 단순 등록 (기본 검증만)
- **KB 상태 관리**: 세분화된 상태 (업로드, 추출, 청킹, 임베딩, 인덱싱)
- **에이전트 검증**: 기본 검증 (필수 필드만 확인)
- **세션 관리**: 영구 저장 (모든 세션 데이터 저장)
- **오류 처리**: 구조화된 오류 (오류 코드 + 메시지)
- **데이터 일관성**: 보상 트랜잭션 (실패 시 롤백 로직)
- **외부 서비스**: 즉시 실패 (오류 즉시 반환)
- **API 응답**: 래핑 구조 (data + meta 구조)

---

## 1. MCP 관리 도메인 비즈니스 로직

### 1.1 외부 MCP 등록 로직
```python
async def register_external_mcp(mcp_data: ExternalMCPData) -> MCPRegistrationResult:
    """외부 MCP 등록 비즈니스 로직"""
    
    # 1. 기본 검증
    validation_result = validate_basic_mcp_data(mcp_data)
    if not validation_result.is_valid:
        raise ValidationError(validation_result.errors)
    
    # 2. 중복 확인
    existing_mcp = await check_mcp_exists(mcp_data.name)
    if existing_mcp:
        raise BusinessRuleError("MCP with same name already exists")
    
    # 3. 연결 테스트 (단순)
    connection_result = await test_mcp_connection(mcp_data.endpoint_url)
    if not connection_result.success:
        raise ConnectionError("Cannot connect to MCP endpoint")
    
    # 4. MCP 메타데이터 생성
    mcp_entity = create_mcp_entity(mcp_data, MCPType.EXTERNAL)
    
    # 5. 게이트웨이 생성 요청
    gateway_result = await request_gateway_creation(mcp_entity)
    mcp_entity.gateway_id = gateway_result.gateway_id
    
    # 6. 데이터베이스 저장
    saved_mcp = await save_mcp_entity(mcp_entity)
    
    return MCPRegistrationResult(
        mcp_id=saved_mcp.mcp_id,
        status=MCPStatus.ACTIVE,
        gateway_id=saved_mcp.gateway_id
    )
```

### 1.2 내부 MCP 등록 로직
```python
async def register_internal_mcp(mcp_data: InternalMCPData) -> MCPRegistrationResult:
    """내부 MCP 등록 비즈니스 로직"""
    
    # 1. 기본 검증
    validation_result = validate_basic_mcp_data(mcp_data)
    if not validation_result.is_valid:
        raise ValidationError(validation_result.errors)
    
    # 2. 컨테이너 파일 검증 (기본)
    if not mcp_data.container_file:
        raise ValidationError("Container file is required for internal MCP")
    
    # 3. MCP 메타데이터 생성
    mcp_entity = create_mcp_entity(mcp_data, MCPType.INTERNAL)
    mcp_entity.status = MCPStatus.UPLOADING
    
    # 4. 임시 저장
    saved_mcp = await save_mcp_entity(mcp_entity)
    
    # 5. 컨테이너 업로드 트리거 (Lambda)
    await trigger_container_upload(saved_mcp.mcp_id, mcp_data.container_file)
    
    return MCPRegistrationResult(
        mcp_id=saved_mcp.mcp_id,
        status=MCPStatus.UPLOADING,
        message="Container upload started"
    )
```

### 1.3 MCP 상태 관리 로직
```python
async def update_mcp_status(mcp_id: str, new_status: MCPStatus, 
                           metadata: Optional[Dict] = None) -> None:
    """MCP 상태 업데이트 로직"""
    
    # 1. MCP 존재 확인
    mcp = await get_mcp_by_id(mcp_id)
    if not mcp:
        raise EntityNotFoundError(f"MCP {mcp_id} not found")
    
    # 2. 상태 전환 유효성 검증
    if not is_valid_status_transition(mcp.status, new_status):
        raise BusinessRuleError(f"Invalid status transition: {mcp.status} -> {new_status}")
    
    # 3. 상태별 추가 로직
    if new_status == MCPStatus.ACTIVE:
        await activate_mcp(mcp)
    elif new_status == MCPStatus.FAILED:
        await handle_mcp_failure(mcp, metadata)
    
    # 4. 상태 업데이트
    await update_mcp_status_in_db(mcp_id, new_status, metadata)
```

---

## 2. 지식베이스 관리 도메인 비즈니스 로직

### 2.1 지식베이스 생성 로직
```python
async def create_knowledge_base(kb_data: KBCreateData) -> KBCreationResult:
    """지식베이스 생성 비즈니스 로직"""
    
    # 1. 기본 검증
    validation_result = validate_kb_data(kb_data)
    if not validation_result.is_valid:
        raise ValidationError(validation_result.errors)
    
    # 2. 중복 확인
    existing_kb = await check_kb_exists(kb_data.name)
    if existing_kb:
        raise BusinessRuleError("Knowledge base with same name already exists")
    
    # 3. KB 엔티티 생성
    kb_entity = create_kb_entity(kb_data)
    kb_entity.status = KBStatus.CREATING
    
    # 4. OpenSearch 인덱스 생성
    index_result = await create_opensearch_index(kb_entity)
    kb_entity.opensearch_index = index_result.index_name
    
    # 5. S3 폴더 생성
    s3_result = await create_s3_folder(kb_entity)
    kb_entity.s3_prefix = s3_result.prefix
    
    # 6. 데이터베이스 저장
    saved_kb = await save_kb_entity(kb_entity)
    
    # 7. 상태 업데이트
    await update_kb_status(saved_kb.kb_id, KBStatus.ACTIVE)
    
    return KBCreationResult(
        kb_id=saved_kb.kb_id,
        status=KBStatus.ACTIVE,
        opensearch_index=saved_kb.opensearch_index
    )
```

### 2.2 파일 업로드 처리 로직
```python
async def process_file_upload(kb_id: str, files: List[UploadFile]) -> FileUploadResult:
    """파일 업로드 처리 비즈니스 로직"""
    
    # 1. KB 존재 확인
    kb = await get_kb_by_id(kb_id)
    if not kb:
        raise EntityNotFoundError(f"Knowledge base {kb_id} not found")
    
    # 2. KB 상태 확인
    if kb.status != KBStatus.ACTIVE:
        raise BusinessRuleError("Knowledge base is not active")
    
    # 3. 파일 검증
    for file in files:
        validation_result = validate_file(file)
        if not validation_result.is_valid:
            raise ValidationError(f"Invalid file {file.filename}: {validation_result.errors}")
    
    # 4. 파일별 처리
    upload_results = []
    for file in files:
        # 파일 해시 생성
        file_hash = generate_file_hash(file.content)
        
        # 중복 확인
        existing_doc = await check_document_exists(kb_id, file_hash)
        if existing_doc:
            upload_results.append(FileProcessResult(
                filename=file.filename,
                status=ProcessingStatus.SKIPPED,
                message="File already exists"
            ))
            continue
        
        # 문서 메타데이터 생성
        document = create_document_entity(kb_id, file, file_hash)
        document.processing_status = ProcessingStatus.PENDING
        
        # 데이터베이스 저장
        saved_doc = await save_document_entity(document)
        
        # S3 업로드 및 Lambda 트리거
        await upload_file_to_s3(kb.s3_bucket, saved_doc.s3_key, file.content)
        
        upload_results.append(FileProcessResult(
            filename=file.filename,
            document_id=saved_doc.document_id,
            status=ProcessingStatus.PENDING
        ))
    
    return FileUploadResult(results=upload_results)
```

### 2.3 처리 상태 관리 로직 (세분화된 상태)
```python
class ProcessingStatus(Enum):
    PENDING = "PENDING"           # 대기중
    UPLOADING = "UPLOADING"       # 업로드중
    EXTRACTING = "EXTRACTING"     # 텍스트 추출중
    CHUNKING = "CHUNKING"         # 청킹 처리중
    EMBEDDING = "EMBEDDING"       # 임베딩 생성중
    INDEXING = "INDEXING"         # 인덱싱 처리중
    COMPLETED = "COMPLETED"       # 완료
    FAILED = "FAILED"            # 실패

async def update_document_processing_status(document_id: str, 
                                          new_status: ProcessingStatus,
                                          progress_info: Optional[Dict] = None) -> None:
    """문서 처리 상태 업데이트 로직"""
    
    # 1. 문서 존재 확인
    document = await get_document_by_id(document_id)
    if not document:
        raise EntityNotFoundError(f"Document {document_id} not found")
    
    # 2. 상태 전환 유효성 검증
    if not is_valid_processing_transition(document.processing_status, new_status):
        raise BusinessRuleError(f"Invalid processing transition: {document.processing_status} -> {new_status}")
    
    # 3. 진행률 계산
    progress_percentage = calculate_progress_percentage(new_status)
    
    # 4. 상태별 추가 로직
    if new_status == ProcessingStatus.COMPLETED:
        await finalize_document_processing(document)
    elif new_status == ProcessingStatus.FAILED:
        await handle_processing_failure(document, progress_info)
    
    # 5. 상태 업데이트
    await update_document_status_in_db(document_id, new_status, progress_percentage, progress_info)
```

---

## 3. 에이전트 관리 도메인 비즈니스 로직

### 3.1 에이전트 생성 로직
```python
async def create_agent(agent_data: AgentCreateData) -> AgentCreationResult:
    """에이전트 생성 비즈니스 로직"""
    
    # 1. 기본 검증 (필수 필드만)
    validation_result = validate_basic_agent_data(agent_data)
    if not validation_result.is_valid:
        raise ValidationError(validation_result.errors)
    
    # 2. 중복 확인
    existing_agent = await check_agent_exists(agent_data.name)
    if existing_agent:
        raise BusinessRuleError("Agent with same name already exists")
    
    # 3. 에이전트 엔티티 생성
    agent_entity = create_agent_entity(agent_data)
    agent_entity.status = AgentStatus.DRAFT
    
    # 4. 데이터베이스 저장
    saved_agent = await save_agent_entity(agent_entity)
    
    return AgentCreationResult(
        agent_id=saved_agent.agent_id,
        status=AgentStatus.DRAFT
    )
```

### 3.2 에이전트 구성 검증 로직
```python
async def validate_agent_configuration(agent_id: str, config: AgentConfig) -> ValidationResult:
    """에이전트 구성 검증 로직 (기본 검증만)"""
    
    errors = []
    
    # 1. 필수 필드 검증
    if not config.llm_model:
        errors.append("LLM model is required")
    
    if not config.system_instructions:
        errors.append("System instructions are required")
    
    # 2. MCP 도구 기본 검증
    for mcp_tool in config.mcp_tools:
        if not mcp_tool.mcp_id:
            errors.append("MCP ID is required for MCP tools")
    
    # 3. KB 도구 기본 검증
    for kb_tool in config.kb_tools:
        if not kb_tool.kb_id:
            errors.append("KB ID is required for KB tools")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors
    )
```

### 3.3 에이전트 배포 로직
```python
async def deploy_agent(agent_id: str) -> DeploymentResult:
    """에이전트 배포 비즈니스 로직"""
    
    # 1. 에이전트 존재 확인
    agent = await get_agent_by_id(agent_id)
    if not agent:
        raise EntityNotFoundError(f"Agent {agent_id} not found")
    
    # 2. 배포 가능 상태 확인
    if agent.status not in [AgentStatus.DRAFT, AgentStatus.INACTIVE]:
        raise BusinessRuleError("Agent is not in deployable state")
    
    # 3. 구성 검증
    validation_result = await validate_agent_configuration(agent_id, agent.configuration)
    if not validation_result.is_valid:
        raise ValidationError(validation_result.errors)
    
    # 4. 상태 업데이트 (배포 시작)
    await update_agent_status(agent_id, AgentStatus.DEPLOYING)
    
    # 5. AgentCore 배포 요청
    try:
        deployment_result = await deploy_to_agentcore(agent)
        
        # 6. 배포 성공 시 상태 업데이트
        await update_agent_deployment_info(agent_id, deployment_result)
        await update_agent_status(agent_id, AgentStatus.ACTIVE)
        
        return DeploymentResult(
            agent_id=agent_id,
            agentcore_agent_id=deployment_result.agentcore_agent_id,
            status=AgentStatus.ACTIVE
        )
        
    except Exception as e:
        # 7. 배포 실패 시 상태 복구
        await update_agent_status(agent_id, AgentStatus.INACTIVE)
        raise DeploymentError(f"Agent deployment failed: {str(e)}")
```

---

## 4. 플레이그라운드 도메인 비즈니스 로직

### 4.1 채팅 세션 생성 로직 (영구 저장)
```python
async def create_chat_session(agent_id: str, user_id: str) -> SessionCreationResult:
    """채팅 세션 생성 비즈니스 로직"""
    
    # 1. 에이전트 존재 및 상태 확인
    agent = await get_agent_by_id(agent_id)
    if not agent:
        raise EntityNotFoundError(f"Agent {agent_id} not found")
    
    if agent.status != AgentStatus.ACTIVE:
        raise BusinessRuleError("Agent is not active")
    
    # 2. 세션 엔티티 생성
    session = create_session_entity(agent_id, user_id)
    session.status = SessionStatus.ACTIVE
    
    # 3. 데이터베이스에 영구 저장
    saved_session = await save_session_entity(session)
    
    # 4. 초기 컨텍스트 설정
    await initialize_session_context(saved_session.session_id, agent.configuration)
    
    return SessionCreationResult(
        session_id=saved_session.session_id,
        agent_id=agent_id,
        status=SessionStatus.ACTIVE
    )
```

### 4.2 채팅 메시지 처리 로직
```python
async def process_chat_message(session_id: str, message: str) -> ChatResponse:
    """채팅 메시지 처리 비즈니스 로직"""
    
    # 1. 세션 존재 및 상태 확인
    session = await get_session_by_id(session_id)
    if not session:
        raise EntityNotFoundError(f"Session {session_id} not found")
    
    if session.status != SessionStatus.ACTIVE:
        raise BusinessRuleError("Session is not active")
    
    # 2. 사용자 메시지 저장
    user_message = create_message_entity(session_id, MessageRole.USER, message)
    await save_message_entity(user_message)
    
    # 3. 에이전트 호출
    try:
        agent_response = await invoke_agent(session.agent_id, message, session.context)
        
        # 4. 에이전트 응답 저장
        assistant_message = create_message_entity(
            session_id, 
            MessageRole.ASSISTANT, 
            agent_response.content
        )
        assistant_message.metadata = agent_response.metadata
        await save_message_entity(assistant_message)
        
        # 5. 세션 컨텍스트 업데이트
        await update_session_context(session_id, user_message, assistant_message)
        
        # 6. 세션 활동 시간 업데이트
        await update_session_activity(session_id)
        
        return ChatResponse(
            message_id=assistant_message.message_id,
            content=agent_response.content,
            metadata=agent_response.metadata
        )
        
    except Exception as e:
        # 7. 오류 메시지 저장
        error_message = create_message_entity(
            session_id, 
            MessageRole.SYSTEM, 
            f"Error: {str(e)}"
        )
        await save_message_entity(error_message)
        raise ChatProcessingError(str(e))
```

---

## 5. 도메인 간 상호작용 로직

### 5.1 에이전트-MCP 통합 로직
```python
async def get_agent_mcp_tools(agent_id: str) -> List[MCPToolInfo]:
    """에이전트의 MCP 도구 정보 조회"""
    
    # 1. 에이전트 구성 조회
    agent = await get_agent_by_id(agent_id)
    if not agent:
        raise EntityNotFoundError(f"Agent {agent_id} not found")
    
    # 2. MCP 도구 정보 수집
    mcp_tools = []
    for mcp_ref in agent.mcp_tools:
        mcp = await get_mcp_by_id(mcp_ref.mcp_id)
        if mcp and mcp.status == MCPStatus.ACTIVE:
            tools = await get_mcp_tools(mcp.mcp_id)
            mcp_tools.extend(tools)
    
    return mcp_tools
```

### 5.2 에이전트-KB 통합 로직
```python
async def get_agent_kb_tools(agent_id: str) -> List[KBToolInfo]:
    """에이전트의 지식베이스 도구 정보 조회"""
    
    # 1. 에이전트 구성 조회
    agent = await get_agent_by_id(agent_id)
    if not agent:
        raise EntityNotFoundError(f"Agent {agent_id} not found")
    
    # 2. KB 도구 정보 수집
    kb_tools = []
    for kb_ref in agent.kb_tools:
        kb = await get_kb_by_id(kb_ref.kb_id)
        if kb and kb.status == KBStatus.ACTIVE:
            kb_tool = create_kb_tool_info(kb, kb_ref.search_config)
            kb_tools.append(kb_tool)
    
    return kb_tools
```

---

## 6. 공통 비즈니스 로직

### 6.1 보상 트랜잭션 패턴
```python
class CompensationTransaction:
    """보상 트랜잭션 관리"""
    
    def __init__(self):
        self.compensation_actions = []
    
    def add_compensation(self, action: Callable, *args, **kwargs):
        """보상 액션 추가"""
        self.compensation_actions.append((action, args, kwargs))
    
    async def execute_compensations(self):
        """모든 보상 액션 실행 (역순)"""
        for action, args, kwargs in reversed(self.compensation_actions):
            try:
                await action(*args, **kwargs)
            except Exception as e:
                # 보상 실패는 로깅만 하고 계속 진행
                logger.error(f"Compensation failed: {e}")

async def create_agent_with_compensation(agent_data: AgentCreateData) -> AgentCreationResult:
    """보상 트랜잭션을 사용한 에이전트 생성"""
    
    compensation = CompensationTransaction()
    
    try:
        # 1. 에이전트 생성
        agent = await create_agent_entity(agent_data)
        compensation.add_compensation(delete_agent_entity, agent.agent_id)
        
        # 2. 구성 저장
        config = await save_agent_configuration(agent.agent_id, agent_data.configuration)
        compensation.add_compensation(delete_agent_configuration, agent.agent_id)
        
        # 3. 버전 생성
        version = await create_agent_version(agent.agent_id, config)
        compensation.add_compensation(delete_agent_version, version.version_id)
        
        return AgentCreationResult(agent_id=agent.agent_id)
        
    except Exception as e:
        # 실패 시 보상 실행
        await compensation.execute_compensations()
        raise e
```

### 6.2 구조화된 오류 처리
```python
class APIError:
    """구조화된 API 오류"""
    
    def __init__(self, code: str, message: str, details: Optional[Dict] = None):
        self.code = code
        self.message = message
        self.details = details or {}
    
    def to_dict(self) -> Dict:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details
            }
        }

# 도메인별 오류 코드
class ErrorCodes:
    # MCP 관련
    MCP_NOT_FOUND = "MCP_NOT_FOUND"
    MCP_CONNECTION_FAILED = "MCP_CONNECTION_FAILED"
    MCP_ALREADY_EXISTS = "MCP_ALREADY_EXISTS"
    
    # KB 관련
    KB_NOT_FOUND = "KB_NOT_FOUND"
    KB_INVALID_FILE = "KB_INVALID_FILE"
    KB_PROCESSING_FAILED = "KB_PROCESSING_FAILED"
    
    # Agent 관련
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
    AGENT_INVALID_CONFIG = "AGENT_INVALID_CONFIG"
    AGENT_DEPLOYMENT_FAILED = "AGENT_DEPLOYMENT_FAILED"
    
    # Session 관련
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    SESSION_INACTIVE = "SESSION_INACTIVE"
    CHAT_PROCESSING_FAILED = "CHAT_PROCESSING_FAILED"
```

### 6.3 래핑 구조 API 응답
```python
class APIResponse:
    """표준 API 응답 구조"""
    
    @staticmethod
    def success(data: Any, meta: Optional[Dict] = None) -> Dict:
        """성공 응답"""
        response = {"data": data}
        if meta:
            response["meta"] = meta
        return response
    
    @staticmethod
    def error(error: APIError) -> Dict:
        """오류 응답"""
        return error.to_dict()
    
    @staticmethod
    def paginated(data: List[Any], pagination: PaginationInfo) -> Dict:
        """페이지네이션 응답"""
        return {
            "data": data,
            "meta": {
                "pagination": {
                    "total": pagination.total,
                    "page": pagination.page,
                    "per_page": pagination.per_page,
                    "total_pages": pagination.total_pages,
                    "has_next": pagination.has_next,
                    "has_prev": pagination.has_prev
                }
            }
        }
```

---

## 비즈니스 로직 검증 규칙

### 1. 입력 검증 규칙
- 모든 필수 필드 존재 확인
- 데이터 타입 및 형식 검증
- 비즈니스 규칙 제약사항 확인

### 2. 상태 전환 규칙
- 유효한 상태 전환만 허용
- 상태별 전제조건 확인
- 상태 변경 시 부수 효과 처리

### 3. 데이터 일관성 규칙
- 참조 무결성 보장
- 중복 데이터 방지
- 보상 트랜잭션으로 일관성 유지

### 4. 비즈니스 정책 규칙
- 도메인별 비즈니스 정책 적용
- 사용자 권한 및 접근 제어
- 리소스 제한 및 할당량 관리
