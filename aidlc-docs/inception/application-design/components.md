# 컴포넌트 정의

## 프론트엔드 컴포넌트 (React/TypeScript)

### 1. 공통 컴포넌트 (Shared)
**위치**: `src/shared/components/`

#### 1.1 Layout 컴포넌트
- **AppLayout**: 전체 애플리케이션 레이아웃
- **Sidebar**: 네비게이션 사이드바
- **Header**: 상단 헤더
- **Footer**: 하단 푸터

#### 1.2 UI 컴포넌트
- **Button**: 재사용 가능한 버튼 컴포넌트
- **Input**: 폼 입력 컴포넌트
- **Modal**: 모달 다이얼로그
- **Table**: 데이터 테이블
- **LoadingSpinner**: 로딩 표시기
- **ErrorBoundary**: 오류 경계 컴포넌트

### 2. MCP 관리 컴포넌트
**위치**: `src/features/mcp/`

#### 2.1 페이지 컴포넌트
- **MCPListPage**: MCP 목록 페이지
- **MCPDetailPage**: MCP 상세 페이지
- **MCPCreatePage**: MCP 생성 페이지

#### 2.2 기능 컴포넌트
- **MCPList**: MCP 목록 표시
- **MCPCard**: MCP 카드 컴포넌트
- **MCPForm**: MCP 생성/수정 폼
- **MCPStatusToggle**: 활성화/비활성화 토글
- **MCPUpload**: 컨테이너 이미지 업로드

### 3. 지식베이스 관리 컴포넌트
**위치**: `src/features/knowledge-base/`

#### 3.1 페이지 컴포넌트
- **KBListPage**: 지식베이스 목록 페이지
- **KBDetailPage**: 지식베이스 상세 페이지
- **KBCreatePage**: 지식베이스 생성 페이지

#### 3.2 기능 컴포넌트
- **KBList**: 지식베이스 목록 표시
- **KBCard**: 지식베이스 카드 컴포넌트
- **KBForm**: 지식베이스 생성/수정 폼
- **FileUpload**: 마크다운 파일 업로드
- **ProcessingStatus**: 벡터 처리 상태 표시

### 4. 에이전트 관리 컴포넌트
**위치**: `src/features/agent/`

#### 4.1 페이지 컴포넌트
- **AgentListPage**: 에이전트 목록 페이지
- **AgentDetailPage**: 에이전트 상세 페이지
- **AgentCreatePage**: 에이전트 생성 페이지

#### 4.2 기능 컴포넌트
- **AgentList**: 에이전트 목록 표시
- **AgentCard**: 에이전트 카드 컴포넌트
- **AgentForm**: 에이전트 생성/수정 폼
- **ModelSelector**: LLM 모델 선택기
- **ToolSelector**: 도구 선택기 (MCP, KB)
- **InstructionEditor**: 인스트럭션 편집기
- **DeploymentStatus**: 배포 상태 표시

### 5. 플레이그라운드 컴포넌트
**위치**: `src/features/playground/`

#### 5.1 페이지 컴포넌트
- **PlaygroundPage**: 플레이그라운드 메인 페이지

#### 5.2 기능 컴포넌트
- **AgentSelector**: 에이전트 선택기
- **ChatInterface**: 채팅 인터페이스
- **MessageList**: 메시지 목록
- **MessageInput**: 메시지 입력
- **ChatSession**: 채팅 세션 관리

---

## 백엔드 컴포넌트 (Python/FastAPI)

### 1. MCP 도메인
**위치**: `src/domains/mcp/`

#### 1.1 핵심 컴포넌트
- **MCPRouter**: MCP API 라우터
- **MCPService**: MCP 비즈니스 로직
- **MCPRepository**: MCP 데이터 액세스
- **MCPModel**: MCP 데이터 모델
- **MCPSchema**: MCP API 스키마

#### 1.2 특화 컴포넌트
- **ExternalMCPAdapter**: 외부 MCP 통합
- **InternalMCPAdapter**: 내부 MCP 관리
- **ContainerUploadHandler**: 컨테이너 이미지 업로드
- **GatewayManager**: 게이트웨이 생성/관리

### 2. 지식베이스 도메인
**위치**: `src/domains/knowledge_base/`

#### 2.1 핵심 컴포넌트
- **KBRouter**: 지식베이스 API 라우터
- **KBService**: 지식베이스 비즈니스 로직
- **KBRepository**: 지식베이스 데이터 액세스
- **KBModel**: 지식베이스 데이터 모델
- **KBSchema**: 지식베이스 API 스키마

#### 2.2 특화 컴포넌트
- **FileUploadHandler**: 파일 업로드 처리
- **VectorProcessor**: 벡터 임베딩 처리 (Lambda 트리거)
- **OpenSearchAdapter**: OpenSearch 통합
- **S3Adapter**: S3 파일 저장

### 3. 에이전트 도메인
**위치**: `src/domains/agent/`

#### 3.1 핵심 컴포넌트
- **AgentRouter**: 에이전트 API 라우터
- **AgentService**: 에이전트 비즈니스 로직
- **AgentRepository**: 에이전트 데이터 액세스
- **AgentModel**: 에이전트 데이터 모델
- **AgentSchema**: 에이전트 API 스키마

#### 3.2 특화 컴포넌트
- **BedrockAdapter**: AWS Bedrock 통합
- **AgentCoreAdapter**: AWS AgentCore 통합
- **DeploymentManager**: 에이전트 배포 관리
- **ConfigurationBuilder**: 에이전트 구성 빌더

### 4. 플레이그라운드 도메인
**위치**: `src/domains/playground/`

#### 4.1 핵심 컴포넌트
- **PlaygroundRouter**: 플레이그라운드 API 라우터
- **PlaygroundService**: 플레이그라운드 비즈니스 로직
- **ChatHandler**: 채팅 처리
- **SessionManager**: 세션 관리

#### 4.2 특화 컴포넌트
- **AgentCommunicator**: 에이전트 통신
- **MessageProcessor**: 메시지 처리
- **ResponseFormatter**: 응답 포맷팅

### 5. 공통 컴포넌트
**위치**: `src/shared/`

#### 5.1 인프라 컴포넌트
- **DatabaseConnection**: DynamoDB 연결
- **AWSClientFactory**: AWS 클라이언트 팩토리
- **ConfigManager**: 설정 관리
- **LoggingManager**: 로깅 관리

#### 5.2 유틸리티 컴포넌트
- **ErrorHandler**: 오류 처리
- **ValidationUtils**: 검증 유틸리티
- **DateTimeUtils**: 날짜/시간 유틸리티
- **FileUtils**: 파일 처리 유틸리티

---

## AWS Lambda 컴포넌트

### 1. 파일 처리 Lambda
**위치**: `lambda/file-processor/`

#### 1.1 핵심 컴포넌트
- **FileProcessorHandler**: Lambda 핸들러
- **EmbeddingGenerator**: 임베딩 생성
- **OpenSearchIndexer**: OpenSearch 인덱싱
- **S3EventProcessor**: S3 이벤트 처리

---

## 컴포넌트 책임 요약

### 프론트엔드 책임
- **사용자 인터페이스 렌더링**: React 컴포넌트를 통한 UI 표시
- **사용자 상호작용 처리**: 폼 입력, 버튼 클릭, 파일 업로드 등
- **상태 관리**: Zustand를 통한 클라이언트 상태 관리
- **API 통신**: 백엔드 API와의 HTTP 통신
- **라우팅**: 페이지 간 네비게이션

### 백엔드 책임
- **API 엔드포인트 제공**: RESTful API 서비스
- **비즈니스 로직 처리**: 도메인별 비즈니스 규칙 실행
- **데이터 액세스**: DynamoDB를 통한 데이터 CRUD
- **외부 서비스 통합**: AWS 서비스와의 연동
- **오류 처리**: 도메인별 예외 처리

### Lambda 책임
- **비동기 파일 처리**: S3 이벤트 기반 파일 처리
- **벡터 임베딩 생성**: 업로드된 문서의 벡터 변환
- **검색 인덱스 업데이트**: OpenSearch 인덱스 관리
