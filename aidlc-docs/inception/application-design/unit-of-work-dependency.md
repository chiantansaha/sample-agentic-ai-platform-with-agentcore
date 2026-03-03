# 단위 작업 의존성 매트릭스

## 의존성 관계 분석

### 단위 간 의존성 매트릭스

```
                        │ Frontend │ Backend │ KB Proc │ MCP Proc │ Infra │
────────────────────────┼──────────┼─────────┼─────────┼──────────┼───────┤
Frontend Application    │    -     │    ●    │    ○    │    ○     │   ○   │
Backend API Service     │    -     │    -    │    ●    │    ●     │   ●   │
KB Processing Functions │    -     │    ●    │    -    │    -     │   ●   │
MCP Processing Functions│    -     │    ●    │    -    │    -     │   ●   │
Infrastructure          │    -     │    -    │    -    │    -     │   -   │

범례:
● 강한 의존성 (직접적 호출/통신)
○ 약한 의존성 (간접적 관계)
- 의존성 없음
```

### 의존성 상세 분석

#### 1. Frontend Application 의존성
**강한 의존성**:
- **Backend API Service**: REST API 호출을 통한 모든 데이터 액세스

**약한 의존성**:
- **KB Processing Functions**: 파일 업로드 상태 모니터링 (Backend 경유)
- **MCP Processing Functions**: 컨테이너 배포 상태 모니터링 (Backend 경유)
- **Infrastructure**: AWS 리소스 상태 정보 (Backend 경유)

#### 2. Backend API Service 의존성
**강한 의존성**:
- **KB Processing Functions**: 파일 처리 상태 조회 및 제어
- **MCP Processing Functions**: 컨테이너 처리 상태 조회 및 제어
- **Infrastructure**: DynamoDB, S3, OpenSearch, AgentCore 직접 액세스

#### 3. KB Processing Functions 의존성
**강한 의존성**:
- **Backend API Service**: 처리 상태 업데이트 (DynamoDB 경유)
- **Infrastructure**: S3, Bedrock, OpenSearch 직접 액세스

#### 4. MCP Processing Functions 의존성
**강한 의존성**:
- **Backend API Service**: 처리 상태 업데이트 (DynamoDB 경유)
- **Infrastructure**: S3, ECR, AgentCore 직접 액세스

#### 5. Infrastructure 의존성
**의존성 없음**: 기반 인프라로서 다른 단위들이 의존

---

## 개발 순서 결정

### 의존성 기반 개발 순서

#### Phase 1: 기반 구축 (병렬 가능)
1. **Infrastructure** (우선순위: 1)
   - AWS 리소스 프로비저닝
   - DynamoDB 테이블 생성
   - S3 버킷 설정
   - OpenSearch 클러스터 구성
   - IAM 역할 및 정책 설정

#### Phase 2: 핵심 서비스 (Infrastructure 완료 후)
2. **Backend API Service** (우선순위: 2)
   - 핵심 API 엔드포인트 구현
   - 도메인 서비스 및 리포지토리
   - AWS 어댑터 구현
   - 기본 CRUD 작업

#### Phase 3: 처리 함수들 (Backend 핵심 완료 후, 병렬 가능)
3. **KB Processing Functions** (우선순위: 3a)
   - 파일 업로드 핸들러
   - 텍스트 추출 함수
   - 벡터 생성 함수
   - 인덱스 업데이트 함수

4. **MCP Processing Functions** (우선순위: 3b)
   - 컨테이너 업로드 핸들러
   - 런타임 배포 함수
   - 헬스체크 함수

#### Phase 4: 사용자 인터페이스 (모든 백엔드 완료 후)
5. **Frontend Application** (우선순위: 4)
   - React 컴포넌트 구현
   - 상태 관리 설정
   - API 통신 레이어
   - 사용자 인터페이스

### 개발 마일스톤

#### Milestone 1: 인프라 준비 완료
- [ ] AWS 리소스 프로비저닝 완료
- [ ] 네트워크 및 보안 설정 완료
- [ ] 개발 환경 구성 완료

#### Milestone 2: 백엔드 API 기본 기능
- [ ] MCP 관리 API 구현
- [ ] 지식베이스 관리 API 구현
- [ ] 에이전트 관리 API 구현
- [ ] 플레이그라운드 API 구현

#### Milestone 3: 파일 처리 기능
- [ ] KB 파일 처리 파이프라인 완료
- [ ] MCP 컨테이너 처리 파이프라인 완료
- [ ] 상태 모니터링 시스템 완료

#### Milestone 4: 완전한 사용자 경험
- [ ] 프론트엔드 모든 기능 구현
- [ ] 통합 테스트 완료
- [ ] 사용자 승인 테스트 완료

---

## 통합 지점 및 인터페이스

### 1. Frontend ↔ Backend 통합

#### REST API 인터페이스
```typescript
// API 클라이언트 인터페이스
interface APIEndpoints {
  // MCP 관리
  'GET /api/v1/mcps': MCPListResponse
  'POST /api/v1/mcps': MCPCreateRequest → MCPResponse
  'GET /api/v1/mcps/{id}': MCPDetailResponse
  'PUT /api/v1/mcps/{id}': MCPUpdateRequest → MCPResponse
  'DELETE /api/v1/mcps/{id}': void
  
  // 지식베이스 관리
  'GET /api/v1/knowledge-bases': KBListResponse
  'POST /api/v1/knowledge-bases': KBCreateRequest → KBResponse
  'POST /api/v1/knowledge-bases/{id}/files': FileUploadRequest → UploadResponse
  'GET /api/v1/knowledge-bases/{id}/status': KBStatusResponse
  
  // 에이전트 관리
  'GET /api/v1/agents': AgentListResponse
  'POST /api/v1/agents': AgentCreateRequest → AgentResponse
  'POST /api/v1/agents/{id}/deploy': DeploymentResponse
  'GET /api/v1/agents/{id}/config': AgentConfigResponse
  
  // 플레이그라운드
  'POST /api/v1/playground/sessions': SessionCreateRequest → SessionResponse
  'POST /api/v1/playground/sessions/{id}/messages': MessageRequest → MessageResponse
  'GET /api/v1/playground/sessions/{id}/history': ChatHistoryResponse
}
```

#### WebSocket 인터페이스 (플레이그라운드)
```typescript
interface WebSocketEvents {
  // 클라이언트 → 서버
  'chat:message': { sessionId: string, message: string }
  'session:create': { agentId: string }
  
  // 서버 → 클라이언트
  'chat:response': { sessionId: string, message: string, metadata: object }
  'chat:error': { sessionId: string, error: string }
  'agent:status': { agentId: string, status: string }
}
```

### 2. Backend ↔ Processing Functions 통합

#### 상태 업데이트 인터페이스
```python
# DynamoDB를 통한 상태 동기화
class ProcessingStatus:
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

# Lambda → Backend 상태 업데이트
async def update_processing_status(
    entity_id: str,
    entity_type: str,  # "kb" | "mcp"
    status: ProcessingStatus,
    progress: Optional[int] = None,
    error_message: Optional[str] = None
):
    # DynamoDB 상태 업데이트
    pass

# Backend → Lambda 작업 트리거
async def trigger_processing(
    entity_id: str,
    processing_type: str,  # "file_upload" | "container_deploy"
    payload: Dict[str, Any]
):
    # S3 이벤트 또는 직접 Lambda 호출
    pass
```

### 3. Processing Functions ↔ AWS Services 통합

#### AWS 서비스 어댑터 인터페이스
```python
# Bedrock 어댑터
class BedrockAdapter:
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]
    async def invoke_model(self, model_id: str, payload: dict) -> dict

# S3 어댑터
class S3Adapter:
    async def upload_file(self, bucket: str, key: str, data: bytes) -> str
    async def download_file(self, bucket: str, key: str) -> bytes
    async def list_objects(self, bucket: str, prefix: str) -> List[str]

# OpenSearch 어댑터
class OpenSearchAdapter:
    async def create_index(self, index_name: str, mapping: dict) -> bool
    async def index_document(self, index: str, doc_id: str, document: dict) -> bool
    async def search(self, index: str, query: dict) -> dict

# AgentCore 어댑터
class AgentCoreAdapter:
    async def deploy_agent(self, config: AgentConfig) -> DeploymentResult
    async def invoke_agent(self, agent_id: str, message: str) -> AgentResponse
    async def get_agent_status(self, agent_id: str) -> AgentStatus
```

---

## 순환 의존성 검증

### 검증 결과: ✅ 순환 의존성 없음

#### 의존성 그래프 분석
```
Infrastructure (Level 0)
    ↑
Backend API Service (Level 1)
    ↑                    ↑
KB Processing (Level 2)  MCP Processing (Level 2)
                    ↑
            Frontend Application (Level 3)
```

#### 검증 규칙
1. **단방향 의존성**: 모든 의존성이 단방향으로 흐름
2. **계층적 구조**: 명확한 레이어 구조로 순환 방지
3. **공유 의존성**: Infrastructure는 공유 기반으로 순환 없음
4. **통신 패턴**: 직접 통합으로 중간 레이어 없음

---

## 위험 요소 및 완화 전략

### 1. 단위 간 결합도 위험
**위험**: Backend API Service가 단일 장애점이 될 수 있음
**완화 전략**:
- 헬스체크 엔드포인트 구현
- 회로 차단기 패턴 적용
- 재시도 로직 구현
- 모니터링 및 알림 설정

### 2. 처리 함수 의존성 위험
**위험**: Lambda 함수 실패 시 상태 불일치 가능
**완화 전략**:
- 멱등성 보장
- 상태 복구 메커니즘
- Dead Letter Queue 설정
- 수동 재처리 기능

### 3. 프론트엔드 단일점 위험
**위험**: 단일 SPA로 인한 전체 기능 영향
**완화 전략**:
- 코드 분할 (Route-based)
- 오류 경계 (Error Boundaries)
- 점진적 로딩
- 오프라인 지원 (향후)

### 4. 데이터 일관성 위험
**위험**: 도메인별 데이터 소유권으로 인한 일관성 문제
**완화 전략**:
- 트랜잭션 패턴 적용
- 이벤트 기반 동기화
- 데이터 검증 로직
- 정기적 일관성 검사

---

## 성능 고려사항

### 1. 단위별 성능 목표
- **Frontend**: 초기 로딩 < 3초, 페이지 전환 < 1초
- **Backend API**: 응답 시간 < 500ms (95th percentile)
- **KB Processing**: 파일 처리 < 5분 (10MB 파일 기준)
- **MCP Processing**: 컨테이너 배포 < 10분

### 2. 확장성 전략
- **Frontend**: CDN 배포, 코드 분할
- **Backend**: 수평 확장 (ECS/Lambda)
- **Processing**: Lambda 동시 실행 제한 관리
- **Infrastructure**: Auto Scaling 설정

### 3. 모니터링 지점
- **API 응답 시간**: CloudWatch 메트릭
- **Lambda 실행 시간**: CloudWatch Logs
- **데이터베이스 성능**: DynamoDB 메트릭
- **사용자 경험**: 프론트엔드 성능 모니터링
