# 서비스 정의 및 오케스트레이션

## 서비스 아키텍처 개요

### 아키텍처 패턴
- **도메인 주도 설계 (DDD)**: 각 도메인이 완전한 서비스 모듈
- **리포지토리 패턴**: 데이터 액세스 레이어 분리
- **어댑터 패턴**: AWS 서비스별 어댑터 클래스
- **도메인별 오류 처리**: 각 도메인의 특화된 예외 처리

---

## 1. MCP 관리 서비스

### 1.1 MCPService (핵심 비즈니스 로직)
```python
class MCPService:
    """MCP 관리 핵심 비즈니스 로직"""
    
    def __init__(self, 
                 repository: MCPRepository,
                 gateway_manager: GatewayManager,
                 container_handler: ContainerUploadHandler,
                 external_adapter: ExternalMCPAdapter):
        self.repository = repository
        self.gateway_manager = gateway_manager
        self.container_handler = container_handler
        self.external_adapter = external_adapter
    
    # 비즈니스 규칙
    async def validate_mcp_creation(self, data: MCPCreateData) -> ValidationResult:
        """MCP 생성 전 비즈니스 규칙 검증"""
        pass
    
    async def orchestrate_external_mcp_registration(self, data: ExternalMCPData) -> MCP:
        """외부 MCP 등록 오케스트레이션"""
        # 1. 데이터 검증
        # 2. 외부 MCP 연결 테스트
        # 3. 게이트웨이에 Target 추가
        # 4. 데이터베이스에 저장
        pass
    
    async def orchestrate_internal_mcp_deployment(self, data: InternalMCPData) -> MCP:
        """내부 MCP 배포 오케스트레이션"""
        # 1. 컨테이너 이미지 업로드
        # 2. 런타임에 배포
        # 3. 상태 확인
        # 4. 데이터베이스 업데이트
        pass
```

### 1.2 MCPRepository (데이터 액세스)
```python
class MCPRepository:
    """MCP 데이터 액세스 레이어"""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
    
    # CRUD 작업
    async def create_mcp(self, mcp_data: MCPModel) -> MCPModel:
        """MCP 생성"""
        pass
    
    async def find_by_filters(self, filters: MCPFilters) -> List[MCPModel]:
        """필터링된 MCP 조회"""
        pass
    
    async def update_status(self, mcp_id: str, status: MCPStatus) -> MCPModel:
        """MCP 상태 업데이트"""
        pass
```

### 1.3 GatewayManager (게이트웨이 관리)
```python
class GatewayManager:
    """AWS AgentCore Gateway 관리"""
    
    def __init__(self, agentcore_adapter: AgentCoreAdapter):
        self.agentcore = agentcore_adapter
    
    async def create_gateway_for_api(self, api_spec: APISpec) -> GatewayResult:
        """API 명세로부터 게이트웨이 생성"""
        pass
    
    async def add_external_target(self, gateway_id: str, endpoint: str) -> None:
        """외부 엔드포인트를 게이트웨이에 추가"""
        pass
    
    async def update_gateway_version(self, gateway_id: str, version: str) -> None:
        """게이트웨이 버전 업데이트"""
        pass
```

---

## 2. 지식베이스 관리 서비스

### 2.1 KnowledgeBaseService (핵심 비즈니스 로직)
```python
class KnowledgeBaseService:
    """지식베이스 관리 핵심 비즈니스 로직"""
    
    def __init__(self,
                 repository: KBRepository,
                 s3_adapter: S3Adapter,
                 opensearch_adapter: OpenSearchAdapter):
        self.repository = repository
        self.s3_adapter = s3_adapter
        self.opensearch_adapter = opensearch_adapter
    
    async def orchestrate_kb_creation(self, data: KBCreateData) -> KnowledgeBase:
        """지식베이스 생성 오케스트레이션"""
        # 1. 지식베이스 메타데이터 생성
        # 2. OpenSearch 인덱스 생성
        # 3. S3 버킷 폴더 생성
        # 4. 초기 상태 설정
        pass
    
    async def orchestrate_file_upload(self, kb_id: str, files: List[UploadFile]) -> None:
        """파일 업로드 오케스트레이션"""
        # 1. 파일 검증
        # 2. S3 업로드 (Lambda 트리거)
        # 3. 처리 상태 추적
        pass
    
    async def monitor_processing_status(self, kb_id: str) -> ProcessingStatus:
        """벡터 처리 상태 모니터링"""
        pass
```

### 2.2 VectorProcessingService (Lambda)
```python
class VectorProcessingService:
    """벡터 처리 서비스 (Lambda 함수)"""
    
    def __init__(self,
                 bedrock_adapter: BedrockAdapter,
                 opensearch_adapter: OpenSearchAdapter,
                 kb_repository: KBRepository):
        self.bedrock = bedrock_adapter
        self.opensearch = opensearch_adapter
        self.kb_repository = kb_repository
    
    async def process_uploaded_file(self, s3_event: S3Event) -> None:
        """S3 이벤트 기반 파일 처리"""
        # 1. S3에서 파일 다운로드
        # 2. 텍스트 추출
        # 3. 청킹
        # 4. 임베딩 생성 (Bedrock)
        # 5. OpenSearch 인덱싱
        # 6. 상태 업데이트
        pass
```

---

## 3. 에이전트 관리 서비스

### 3.1 AgentService (핵심 비즈니스 로직)
```python
class AgentService:
    """에이전트 관리 핵심 비즈니스 로직"""
    
    def __init__(self,
                 repository: AgentRepository,
                 agentcore_adapter: AgentCoreAdapter,
                 bedrock_adapter: BedrockAdapter,
                 config_builder: ConfigurationBuilder):
        self.repository = repository
        self.agentcore = agentcore_adapter
        self.bedrock = bedrock_adapter
        self.config_builder = config_builder
    
    async def orchestrate_agent_creation(self, data: AgentCreateData) -> Agent:
        """에이전트 생성 오케스트레이션"""
        # 1. 에이전트 구성 검증
        # 2. 도구 가용성 확인
        # 3. 에이전트 명세 생성
        # 4. 데이터베이스 저장
        pass
    
    async def orchestrate_agent_deployment(self, agent_id: str) -> DeploymentResult:
        """에이전트 배포 오케스트레이션"""
        # 1. 에이전트 구성 빌드
        # 2. AgentCore에 배포
        # 3. 배포 상태 모니터링
        # 4. 상태 업데이트
        pass
    
    async def validate_agent_configuration(self, config: AgentConfig) -> ValidationResult:
        """에이전트 구성 검증"""
        pass
```

### 3.2 ConfigurationBuilder (구성 빌더)
```python
class ConfigurationBuilder:
    """에이전트 구성 빌더"""
    
    def __init__(self,
                 mcp_service: MCPService,
                 kb_service: KnowledgeBaseService):
        self.mcp_service = mcp_service
        self.kb_service = kb_service
    
    async def build_agent_config(self, agent_data: AgentData) -> AgentConfig:
        """에이전트 구성 빌드"""
        # 1. LLM 모델 구성
        # 2. 인스트럭션 설정
        # 3. 도구 구성 (MCP, KB)
        # 4. 런타임 설정
        pass
    
    async def resolve_tool_dependencies(self, tool_ids: List[str]) -> List[ToolConfig]:
        """도구 의존성 해결"""
        pass
```

---

## 4. 플레이그라운드 서비스

### 4.1 PlaygroundService (핵심 비즈니스 로직)
```python
class PlaygroundService:
    """플레이그라운드 핵심 비즈니스 로직"""
    
    def __init__(self,
                 agent_communicator: AgentCommunicator,
                 session_manager: SessionManager,
                 agent_service: AgentService):
        self.agent_communicator = agent_communicator
        self.session_manager = session_manager
        self.agent_service = agent_service
    
    async def orchestrate_agent_preparation(self, agent_id: str) -> AgentStatus:
        """에이전트 준비 오케스트레이션"""
        # 1. 에이전트 상태 확인
        # 2. 런타임 준비
        # 3. 연결 테스트
        # 4. 준비 완료 상태 반환
        pass
    
    async def orchestrate_chat_interaction(self, 
                                         agent_id: str, 
                                         message: str, 
                                         session_id: str) -> ChatResponse:
        """채팅 상호작용 오케스트레이션"""
        # 1. 세션 검증
        # 2. 메시지 전처리
        # 3. 에이전트 호출
        # 4. 응답 후처리
        # 5. 세션 업데이트
        pass
```

### 4.2 SessionManager (세션 관리)
```python
class SessionManager:
    """채팅 세션 관리"""
    
    def __init__(self, cache_adapter: CacheAdapter):
        self.cache = cache_adapter
    
    async def create_session(self, agent_id: str, user_id: str) -> str:
        """새 채팅 세션 생성"""
        pass
    
    async def get_session_context(self, session_id: str) -> SessionContext:
        """세션 컨텍스트 조회"""
        pass
    
    async def update_session_history(self, session_id: str, message: ChatMessage) -> None:
        """세션 기록 업데이트"""
        pass
    
    async def clear_session(self, session_id: str) -> None:
        """세션 초기화"""
        pass
```

---

## 5. 공통 서비스

### 5.1 ErrorHandlingService (오류 처리)
```python
class ErrorHandlingService:
    """도메인별 오류 처리"""
    
    @staticmethod
    def handle_mcp_errors(error: Exception) -> MCPError:
        """MCP 도메인 오류 처리"""
        pass
    
    @staticmethod
    def handle_kb_errors(error: Exception) -> KBError:
        """지식베이스 도메인 오류 처리"""
        pass
    
    @staticmethod
    def handle_agent_errors(error: Exception) -> AgentError:
        """에이전트 도메인 오류 처리"""
        pass
    
    @staticmethod
    def handle_playground_errors(error: Exception) -> PlaygroundError:
        """플레이그라운드 도메인 오류 처리"""
        pass
```

### 5.2 ValidationService (검증 서비스)
```python
class ValidationService:
    """공통 검증 서비스"""
    
    @staticmethod
    def validate_file_upload(file: UploadFile) -> ValidationResult:
        """파일 업로드 검증"""
        pass
    
    @staticmethod
    def validate_api_endpoint(endpoint: str) -> ValidationResult:
        """API 엔드포인트 검증"""
        pass
    
    @staticmethod
    def validate_container_image(image_data: bytes) -> ValidationResult:
        """컨테이너 이미지 검증"""
        pass
```

---

## 서비스 오케스트레이션 패턴

### 1. 생성 오케스트레이션 패턴
```python
async def orchestrate_creation(self, data: CreateData) -> Result:
    """생성 오케스트레이션 공통 패턴"""
    try:
        # 1. 입력 검증
        validation_result = await self.validate_input(data)
        if not validation_result.is_valid:
            raise ValidationError(validation_result.errors)
        
        # 2. 비즈니스 규칙 적용
        processed_data = await self.apply_business_rules(data)
        
        # 3. 외부 서비스 호출
        external_result = await self.call_external_services(processed_data)
        
        # 4. 데이터 저장
        saved_entity = await self.repository.create(processed_data)
        
        # 5. 후처리 작업
        await self.post_creation_tasks(saved_entity)
        
        return saved_entity
        
    except Exception as e:
        # 도메인별 오류 처리
        raise self.error_handler.handle_domain_error(e)
```

### 2. 업데이트 오케스트레이션 패턴
```python
async def orchestrate_update(self, entity_id: str, updates: UpdateData) -> Result:
    """업데이트 오케스트레이션 공통 패턴"""
    try:
        # 1. 기존 엔티티 조회
        existing_entity = await self.repository.find_by_id(entity_id)
        if not existing_entity:
            raise EntityNotFoundError(entity_id)
        
        # 2. 업데이트 권한 확인
        await self.check_update_permissions(existing_entity, updates)
        
        # 3. 변경사항 검증
        validation_result = await self.validate_updates(existing_entity, updates)
        if not validation_result.is_valid:
            raise ValidationError(validation_result.errors)
        
        # 4. 외부 서비스 업데이트
        await self.update_external_services(entity_id, updates)
        
        # 5. 데이터베이스 업데이트
        updated_entity = await self.repository.update(entity_id, updates)
        
        return updated_entity
        
    except Exception as e:
        raise self.error_handler.handle_domain_error(e)
```

### 3. 비동기 처리 오케스트레이션 패턴
```python
async def orchestrate_async_processing(self, entity_id: str, task_data: TaskData) -> TaskResult:
    """비동기 처리 오케스트레이션 패턴"""
    try:
        # 1. 작업 상태 초기화
        await self.repository.update_status(entity_id, ProcessingStatus.STARTED)
        
        # 2. 비동기 작업 시작 (Lambda, Background Task 등)
        task_id = await self.start_async_task(task_data)
        
        # 3. 작업 ID 저장
        await self.repository.update_task_id(entity_id, task_id)
        
        # 4. 상태 모니터링 설정
        await self.setup_status_monitoring(entity_id, task_id)
        
        return TaskResult(task_id=task_id, status=ProcessingStatus.IN_PROGRESS)
        
    except Exception as e:
        await self.repository.update_status(entity_id, ProcessingStatus.FAILED)
        raise self.error_handler.handle_domain_error(e)
```

---

## 서비스 간 통신 패턴

### 1. 도메인 간 통신
- **이벤트 기반**: 도메인 이벤트를 통한 느슨한 결합
- **서비스 참조**: 직접 서비스 호출 (신중하게 사용)
- **공유 데이터**: 읽기 전용 데이터 공유

### 2. 외부 서비스 통신
- **어댑터 패턴**: AWS 서비스별 전용 어댑터
- **재시도 로직**: 일시적 오류에 대한 자동 재시도
- **회로 차단기**: 외부 서비스 장애 시 보호

### 3. 프론트엔드-백엔드 통신
- **RESTful API**: 표준 HTTP 메서드 사용
- **상태 코드**: 적절한 HTTP 상태 코드 반환
- **오류 응답**: 일관된 오류 응답 형식
