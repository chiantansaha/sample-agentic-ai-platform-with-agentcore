# 컴포넌트 메서드 정의

## 프론트엔드 컴포넌트 메서드

### 1. MCP 관리 컴포넌트 메서드

#### MCPService (Zustand Store)
```typescript
interface MCPService {
  // 상태
  mcps: MCP[]
  loading: boolean
  error: string | null
  
  // 메서드
  fetchMCPs(): Promise<void>
  searchMCPs(query: string, filters: MCPFilters): Promise<void>
  getMCPById(id: string): Promise<MCP>
  createExternalMCP(data: ExternalMCPData): Promise<MCP>
  createInternalMCP(data: InternalMCPData): Promise<MCP>
  uploadContainerImage(file: File, mcpId: string): Promise<void>
  toggleMCPStatus(id: string, enabled: boolean): Promise<void>
  updateMCPVersion(id: string, version: string): Promise<void>
  deleteMCP(id: string): Promise<void>
}
```

#### MCPList 컴포넌트
```typescript
interface MCPListProps {
  onMCPSelect: (mcp: MCP) => void
  filters?: MCPFilters
}

interface MCPListMethods {
  handleSearch(query: string): void
  handleFilterChange(filters: MCPFilters): void
  handleStatusToggle(id: string, enabled: boolean): void
  handleRefresh(): void
}
```

### 2. 지식베이스 관리 컴포넌트 메서드

#### KBService (Zustand Store)
```typescript
interface KBService {
  // 상태
  knowledgeBases: KnowledgeBase[]
  loading: boolean
  processingStatus: Record<string, ProcessingStatus>
  
  // 메서드
  fetchKnowledgeBases(): Promise<void>
  searchKnowledgeBases(query: string): Promise<void>
  getKBById(id: string): Promise<KnowledgeBase>
  createKnowledgeBase(data: KBCreateData): Promise<KnowledgeBase>
  uploadFiles(kbId: string, files: File[]): Promise<void>
  updateDataSource(kbId: string, changes: DataSourceChanges): Promise<void>
  toggleKBStatus(id: string, enabled: boolean): Promise<void>
  deleteKnowledgeBase(id: string): Promise<void>
  getProcessingStatus(kbId: string): Promise<ProcessingStatus>
}
```

#### FileUpload 컴포넌트
```typescript
interface FileUploadProps {
  onFilesSelected: (files: File[]) => void
  acceptedTypes: string[]
  maxFileSize: number
}

interface FileUploadMethods {
  handleFileSelect(event: ChangeEvent<HTMLInputElement>): void
  handleDragDrop(event: DragEvent): void
  validateFiles(files: File[]): ValidationResult
  uploadFiles(files: File[]): Promise<void>
}
```

### 3. 에이전트 관리 컴포넌트 메서드

#### AgentService (Zustand Store)
```typescript
interface AgentService {
  // 상태
  agents: Agent[]
  availableModels: BedrockModel[]
  availableTools: Tool[]
  deploymentStatus: Record<string, DeploymentStatus>
  
  // 메서드
  fetchAgents(): Promise<void>
  searchAgents(query: string): Promise<void>
  getAgentById(id: string): Promise<Agent>
  createAgent(data: AgentCreateData): Promise<Agent>
  updateAgent(id: string, data: AgentUpdateData): Promise<Agent>
  deployAgent(id: string): Promise<void>
  redeployAgent(id: string): Promise<void>
  toggleAgentStatus(id: string, enabled: boolean): Promise<void>
  getDeploymentStatus(id: string): Promise<DeploymentStatus>
  fetchAvailableModels(): Promise<BedrockModel[]>
  fetchAvailableTools(): Promise<Tool[]>
}
```

#### AgentForm 컴포넌트
```typescript
interface AgentFormProps {
  agent?: Agent
  onSubmit: (data: AgentFormData) => void
  onCancel: () => void
}

interface AgentFormMethods {
  handleModelSelect(modelId: string): void
  handleInstructionChange(instruction: string): void
  handleToolSelect(toolIds: string[]): void
  validateForm(data: AgentFormData): ValidationResult
  submitForm(): void
  resetForm(): void
}
```

### 4. 플레이그라운드 컴포넌트 메서드

#### PlaygroundService (Zustand Store)
```typescript
interface PlaygroundService {
  // 상태
  selectedAgent: Agent | null
  chatSessions: Record<string, ChatSession>
  currentSessionId: string | null
  agentStatus: AgentStatus
  
  // 메서드
  selectAgent(agentId: string): Promise<void>
  prepareAgent(agentId: string): Promise<void>
  createChatSession(): string
  sendMessage(sessionId: string, message: string): Promise<void>
  getChatHistory(sessionId: string): ChatMessage[]
  clearChatSession(sessionId: string): void
  getAgentStatus(agentId: string): Promise<AgentStatus>
}
```

#### ChatInterface 컴포넌트
```typescript
interface ChatInterfaceProps {
  sessionId: string
  onMessageSend: (message: string) => void
}

interface ChatInterfaceMethods {
  handleMessageSubmit(message: string): void
  handleNewSession(): void
  scrollToBottom(): void
  formatMessage(message: ChatMessage): JSX.Element
}
```

---

## 백엔드 컴포넌트 메서드

### 1. MCP 도메인 메서드

#### MCPService
```python
class MCPService:
    def __init__(self, repository: MCPRepository, gateway_manager: GatewayManager):
        pass
    
    async def list_mcps(self, filters: MCPFilters) -> List[MCP]:
        """MCP 목록 조회"""
        pass
    
    async def get_mcp_by_id(self, mcp_id: str) -> MCP:
        """MCP 상세 조회"""
        pass
    
    async def create_external_mcp(self, data: ExternalMCPCreate) -> MCP:
        """외부 MCP 등록"""
        pass
    
    async def create_internal_mcp(self, data: InternalMCPCreate) -> MCP:
        """내부 MCP 생성"""
        pass
    
    async def upload_container_image(self, mcp_id: str, image_data: bytes) -> None:
        """컨테이너 이미지 업로드"""
        pass
    
    async def toggle_mcp_status(self, mcp_id: str, enabled: bool) -> MCP:
        """MCP 활성화/비활성화"""
        pass
    
    async def update_mcp_version(self, mcp_id: str, version_data: VersionUpdate) -> MCP:
        """MCP 버전 업데이트"""
        pass
```

#### MCPRepository
```python
class MCPRepository:
    def __init__(self, db_connection: DatabaseConnection):
        pass
    
    async def find_all(self, filters: MCPFilters) -> List[MCP]:
        """모든 MCP 조회"""
        pass
    
    async def find_by_id(self, mcp_id: str) -> Optional[MCP]:
        """ID로 MCP 조회"""
        pass
    
    async def create(self, mcp_data: MCPCreate) -> MCP:
        """MCP 생성"""
        pass
    
    async def update(self, mcp_id: str, updates: MCPUpdate) -> MCP:
        """MCP 업데이트"""
        pass
    
    async def delete(self, mcp_id: str) -> bool:
        """MCP 삭제"""
        pass
```

### 2. 지식베이스 도메인 메서드

#### KBService
```python
class KBService:
    def __init__(self, repository: KBRepository, s3_adapter: S3Adapter):
        pass
    
    async def list_knowledge_bases(self, filters: KBFilters) -> List[KnowledgeBase]:
        """지식베이스 목록 조회"""
        pass
    
    async def get_kb_by_id(self, kb_id: str) -> KnowledgeBase:
        """지식베이스 상세 조회"""
        pass
    
    async def create_knowledge_base(self, data: KBCreate) -> KnowledgeBase:
        """지식베이스 생성"""
        pass
    
    async def upload_files(self, kb_id: str, files: List[UploadFile]) -> None:
        """파일 업로드 (Lambda 트리거)"""
        pass
    
    async def update_data_source(self, kb_id: str, changes: DataSourceUpdate) -> None:
        """데이터소스 업데이트"""
        pass
    
    async def get_processing_status(self, kb_id: str) -> ProcessingStatus:
        """처리 상태 조회"""
        pass
```

#### VectorProcessor (Lambda)
```python
class VectorProcessor:
    def __init__(self, opensearch_adapter: OpenSearchAdapter):
        pass
    
    def lambda_handler(self, event: S3Event, context: LambdaContext) -> Dict:
        """Lambda 핸들러"""
        pass
    
    async def process_file(self, bucket: str, key: str) -> None:
        """파일 처리"""
        pass
    
    async def generate_embeddings(self, text: str) -> List[float]:
        """임베딩 생성"""
        pass
    
    async def index_to_opensearch(self, kb_id: str, embeddings: List[float]) -> None:
        """OpenSearch 인덱싱"""
        pass
```

### 3. 에이전트 도메인 메서드

#### AgentService
```python
class AgentService:
    def __init__(self, repository: AgentRepository, agentcore_adapter: AgentCoreAdapter):
        pass
    
    async def list_agents(self, filters: AgentFilters) -> List[Agent]:
        """에이전트 목록 조회"""
        pass
    
    async def get_agent_by_id(self, agent_id: str) -> Agent:
        """에이전트 상세 조회"""
        pass
    
    async def create_agent(self, data: AgentCreate) -> Agent:
        """에이전트 생성"""
        pass
    
    async def update_agent(self, agent_id: str, data: AgentUpdate) -> Agent:
        """에이전트 업데이트"""
        pass
    
    async def deploy_agent(self, agent_id: str) -> DeploymentResult:
        """에이전트 배포"""
        pass
    
    async def get_deployment_status(self, agent_id: str) -> DeploymentStatus:
        """배포 상태 조회"""
        pass
    
    async def get_available_models(self) -> List[BedrockModel]:
        """사용 가능한 모델 조회"""
        pass
    
    async def get_available_tools(self) -> List[Tool]:
        """사용 가능한 도구 조회"""
        pass
```

### 4. 플레이그라운드 도메인 메서드

#### PlaygroundService
```python
class PlaygroundService:
    def __init__(self, agent_communicator: AgentCommunicator):
        pass
    
    async def prepare_agent(self, agent_id: str) -> AgentStatus:
        """에이전트 준비"""
        pass
    
    async def send_message(self, agent_id: str, message: str, session_id: str) -> ChatResponse:
        """메시지 전송"""
        pass
    
    async def get_chat_history(self, session_id: str) -> List[ChatMessage]:
        """채팅 기록 조회"""
        pass
    
    async def create_chat_session(self, agent_id: str) -> str:
        """채팅 세션 생성"""
        pass
    
    async def clear_chat_session(self, session_id: str) -> None:
        """채팅 세션 초기화"""
        pass
```

---

## AWS 어댑터 메서드

### BedrockAdapter
```python
class BedrockAdapter:
    def __init__(self, client: BedrockClient):
        pass
    
    async def list_foundation_models(self) -> List[BedrockModel]:
        """기반 모델 목록 조회"""
        pass
    
    async def invoke_model(self, model_id: str, prompt: str) -> ModelResponse:
        """모델 호출"""
        pass
```

### AgentCoreAdapter
```python
class AgentCoreAdapter:
    def __init__(self, client: AgentCoreClient):
        pass
    
    async def create_agent(self, config: AgentConfig) -> str:
        """에이전트 생성"""
        pass
    
    async def deploy_agent(self, agent_id: str) -> DeploymentResult:
        """에이전트 배포"""
        pass
    
    async def invoke_agent(self, agent_id: str, message: str) -> AgentResponse:
        """에이전트 호출"""
        pass
```

### OpenSearchAdapter
```python
class OpenSearchAdapter:
    def __init__(self, client: OpenSearchClient):
        pass
    
    async def create_index(self, index_name: str, mapping: Dict) -> None:
        """인덱스 생성"""
        pass
    
    async def index_document(self, index_name: str, doc_id: str, document: Dict) -> None:
        """문서 인덱싱"""
        pass
    
    async def search(self, index_name: str, query: Dict) -> SearchResult:
        """검색 실행"""
        pass
```

---

## 메서드 호출 관계

### 프론트엔드 → 백엔드 호출 패턴
1. **컴포넌트** → **Zustand Store** → **API Client** → **백엔드 API**
2. **이벤트 핸들러** → **서비스 메서드** → **HTTP 요청** → **응답 처리**

### 백엔드 내부 호출 패턴
1. **Router** → **Service** → **Repository** → **Database**
2. **Service** → **Adapter** → **외부 서비스** (AWS)
3. **Lambda** → **Adapter** → **AWS 서비스** (S3, OpenSearch)

### 비동기 처리 패턴
1. **파일 업로드**: API → S3 → Lambda → OpenSearch
2. **에이전트 배포**: API → AgentCore → 상태 폴링
3. **채팅**: 프론트엔드 → API → AgentCore → 응답
