# 단위 작업 스토리 매핑

## 사용자 스토리 단위별 할당

### 할당 전략
- **주 담당 단위**: 스토리의 핵심 기능을 구현하는 단위
- **지원 단위**: 스토리 완성을 위해 필요한 보조 기능을 제공하는 단위
- **통합 스토리**: 여러 단위가 협력해야 하는 스토리

---

## MCP 관리 스토리 (7개)

### MCP-001: 외부 MCP 등록
**주 담당**: Backend API Service
**지원 단위**: Frontend Application
**구현 범위**:
- Backend: 외부 MCP 등록 API, 연결 테스트, 게이트웨이 생성
- Frontend: MCP 등록 폼, 연결 상태 표시

### MCP-002: 내부 MCP 업로드
**주 담당**: MCP Processing Functions
**지원 단위**: Backend API Service, Frontend Application
**구현 범위**:
- MCP Processing: 컨테이너 업로드, 검증, ECR 등록, 런타임 배포
- Backend: 업로드 API, 상태 관리
- Frontend: 파일 업로드 인터페이스, 진행 상태 표시

### MCP-003: MCP 목록 조회
**주 담당**: Backend API Service
**지원 단위**: Frontend Application
**구현 범위**:
- Backend: MCP 목록 API, 필터링, 페이지네이션
- Frontend: MCP 목록 컴포넌트, 검색/필터 UI

### MCP-004: MCP 상세 정보 조회
**주 담당**: Backend API Service
**지원 단위**: Frontend Application
**구현 범위**:
- Backend: MCP 상세 API, 도구 목록 API
- Frontend: MCP 상세 페이지, 도구 목록 표시

### MCP-005: MCP 상태 관리
**주 담당**: Backend API Service
**지원 단위**: MCP Processing Functions, Frontend Application
**구현 범위**:
- Backend: 상태 업데이트 API, 상태 변경 로직
- MCP Processing: 상태 모니터링, 헬스체크
- Frontend: 상태 표시, 상태 변경 UI

### MCP-006: MCP 도구 목록 조회
**주 담당**: Backend API Service
**지원 단위**: Frontend Application
**구현 범위**:
- Backend: 도구 목록 API, 도구 스키마 조회
- Frontend: 도구 목록 컴포넌트, 스키마 표시

### MCP-007: MCP 삭제
**주 담당**: Backend API Service
**지원 단위**: MCP Processing Functions, Frontend Application
**구현 범위**:
- Backend: MCP 삭제 API, 관련 데이터 정리
- MCP Processing: 런타임에서 제거, 리소스 정리
- Frontend: 삭제 확인 UI, 삭제 진행 상태

---

## 지식베이스 관리 스토리 (4개)

### KB-001: 지식베이스 생성
**주 담당**: Backend API Service
**지원 단위**: Frontend Application
**구현 범위**:
- Backend: KB 생성 API, OpenSearch 인덱스 생성, S3 폴더 생성
- Frontend: KB 생성 폼, 구성 옵션 UI

### KB-002: 파일 업로드
**주 담당**: KB Processing Functions
**지원 단위**: Backend API Service, Frontend Application
**구현 범위**:
- KB Processing: 파일 처리 파이프라인, 텍스트 추출, 벡터 생성, 인덱싱
- Backend: 파일 업로드 API, 상태 관리
- Frontend: 파일 업로드 UI, 드래그 앤 드롭, 진행 상태

### KB-003: 처리 상태 모니터링
**주 담당**: Backend API Service
**지원 단위**: KB Processing Functions, Frontend Application
**구현 범위**:
- Backend: 상태 조회 API, 진행률 계산
- KB Processing: 상태 업데이트, 진행률 보고
- Frontend: 상태 모니터링 UI, 실시간 업데이트

### KB-004: 지식베이스 목록 조회
**주 담당**: Backend API Service
**지원 단위**: Frontend Application
**구현 범위**:
- Backend: KB 목록 API, 통계 정보 제공
- Frontend: KB 목록 컴포넌트, 통계 표시

---

## 에이전트 관리 스토리 (7개)

### AGENT-001: 에이전트 생성
**주 담당**: Backend API Service
**지원 단위**: Frontend Application
**구현 범위**:
- Backend: 에이전트 생성 API, 구성 검증
- Frontend: 에이전트 생성 폼, 구성 마법사

### AGENT-002: 도구 선택 및 구성
**주 담당**: Backend API Service
**지원 단위**: Frontend Application
**구현 범위**:
- Backend: 도구 구성 API, MCP/KB 도구 조회, 구성 빌더
- Frontend: 도구 선택 UI, 구성 옵션 설정

### AGENT-003: 에이전트 배포
**주 담당**: Backend API Service
**지원 단위**: Frontend Application
**구현 범위**:
- Backend: 배포 API, AgentCore 통합, 배포 상태 관리
- Frontend: 배포 트리거 UI, 배포 상태 모니터링

### AGENT-004: 에이전트 목록 조회
**주 담당**: Backend API Service
**지원 단위**: Frontend Application
**구현 범위**:
- Backend: 에이전트 목록 API, 상태 정보 포함
- Frontend: 에이전트 목록 컴포넌트, 상태 표시

### AGENT-005: 에이전트 상세 조회
**주 담당**: Backend API Service
**지원 단위**: Frontend Application
**구현 범위**:
- Backend: 에이전트 상세 API, 구성 정보, 도구 정보
- Frontend: 에이전트 상세 페이지, 구성 표시

### AGENT-006: 에이전트 수정
**주 담당**: Backend API Service
**지원 단위**: Frontend Application
**구현 범위**:
- Backend: 에이전트 수정 API, 버전 관리, 재배포
- Frontend: 에이전트 수정 폼, 변경사항 표시

### AGENT-007: 에이전트 삭제
**주 담당**: Backend API Service
**지원 단위**: Frontend Application
**구현 범위**:
- Backend: 에이전트 삭제 API, AgentCore에서 제거
- Frontend: 삭제 확인 UI, 관련 세션 정리 안내

---

## 플레이그라운드 스토리 (5개)

### PLAY-001: 에이전트 선택
**주 담당**: Frontend Application
**지원 단위**: Backend API Service
**구현 범위**:
- Frontend: 에이전트 선택 UI, 상태 확인
- Backend: 에이전트 목록 API, 상태 조회 API

### PLAY-002: 채팅 상호작용
**주 담당**: Backend API Service
**지원 단위**: Frontend Application
**구현 범위**:
- Backend: 채팅 API, WebSocket 서버, AgentCore 통신, 세션 관리
- Frontend: 채팅 인터페이스, WebSocket 클라이언트, 메시지 표시

### PLAY-003: 채팅 기록 조회
**주 담당**: Backend API Service
**지원 단위**: Frontend Application
**구현 범위**:
- Backend: 채팅 기록 API, 세션 기록 관리
- Frontend: 채팅 기록 UI, 검색 및 필터링

### PLAY-004: 세션 관리
**주 담당**: Backend API Service
**지원 단위**: Frontend Application
**구현 범위**:
- Backend: 세션 생성/삭제 API, 세션 상태 관리, 아카이브
- Frontend: 세션 관리 UI, 새 세션 생성, 세션 초기화

### PLAY-005: 실시간 응답
**주 담당**: Backend API Service
**지원 단위**: Frontend Application
**구현 범위**:
- Backend: WebSocket 실시간 통신, 스트리밍 응답 처리
- Frontend: 실시간 메시지 수신, 타이핑 인디케이터, 응답 스트리밍

---

## 크로스 단위 스토리 분석

### 높은 통합 복잡도 스토리
1. **MCP-002 (내부 MCP 업로드)**: 3개 단위 협력
2. **KB-002 (파일 업로드)**: 3개 단위 협력
3. **PLAY-002 (채팅 상호작용)**: 2개 단위 긴밀한 협력

### 통합 테스트 우선순위
1. **파일 처리 플로우**: KB-002, MCP-002
2. **실시간 통신**: PLAY-002, PLAY-005
3. **상태 동기화**: 모든 상태 관리 스토리

---

## 단위별 스토리 우선순위

### Unit 1: Frontend Application
**총 스토리**: 23개 (모든 스토리의 UI 부분)
**우선순위 순서**:
1. MCP-003, KB-004, AGENT-004 (목록 조회 - 기본 UI)
2. MCP-001, KB-001, AGENT-001 (생성 기능)
3. PLAY-001, PLAY-002 (플레이그라운드 기본 기능)
4. 나머지 상세/관리 기능

### Unit 2: Backend API Service
**총 스토리**: 23개 (모든 스토리의 API 부분)
**우선순위 순서**:
1. 기본 CRUD API (목록, 생성, 조회)
2. 상태 관리 API
3. 플레이그라운드 API
4. 고급 기능 API

### Unit 3: KB Processing Functions
**총 스토리**: 2개 (KB-002, KB-003)
**우선순위 순서**:
1. KB-002 (파일 업로드 처리)
2. KB-003 (상태 모니터링 지원)

### Unit 4: MCP Processing Functions
**총 스토리**: 3개 (MCP-002, MCP-005, MCP-007)
**우선순위 순서**:
1. MCP-002 (컨테이너 업로드 처리)
2. MCP-005 (상태 모니터링 지원)
3. MCP-007 (리소스 정리 지원)

---

## 통합 스토리 정의

### 통합 스토리 1: 완전한 MCP 등록 플로우
**참여 단위**: Frontend, Backend, MCP Processing
**통합 시나리오**:
1. 사용자가 컨테이너 파일 업로드 (Frontend)
2. 파일이 S3에 저장되고 처리 시작 (Backend)
3. 컨테이너 검증 및 ECR 등록 (MCP Processing)
4. 런타임 배포 및 상태 업데이트 (MCP Processing)
5. 사용자에게 완료 알림 (Frontend)

### 통합 스토리 2: 완전한 KB 생성 플로우
**참여 단위**: Frontend, Backend, KB Processing
**통합 시나리오**:
1. 사용자가 KB 생성 및 파일 업로드 (Frontend)
2. KB 메타데이터 생성 및 파일 저장 (Backend)
3. 파일 처리 및 벡터 생성 (KB Processing)
4. OpenSearch 인덱싱 완료 (KB Processing)
5. 사용자에게 완료 알림 (Frontend)

### 통합 스토리 3: 완전한 에이전트 채팅 플로우
**참여 단위**: Frontend, Backend
**통합 시나리오**:
1. 사용자가 에이전트 선택 및 채팅 시작 (Frontend)
2. 세션 생성 및 WebSocket 연결 (Backend)
3. 메시지 전송 및 에이전트 호출 (Backend)
4. 실시간 응답 스트리밍 (Backend → Frontend)
5. 채팅 기록 저장 및 표시 (Backend, Frontend)

---

## 개발 및 테스트 전략

### 단위별 개발 전략
1. **독립 개발**: 각 단위는 모의 객체를 사용하여 독립적으로 개발
2. **점진적 통합**: 단위별 완성 후 순차적으로 통합
3. **스토리 기반 검증**: 각 스토리 완성 시 승인 기준 확인

### 통합 테스트 전략
1. **단위 간 인터페이스 테스트**: API 계약 테스트
2. **엔드투엔드 테스트**: 완전한 사용자 플로우 테스트
3. **성능 테스트**: 통합 환경에서 성능 요구사항 검증

### 사용자 승인 테스트
1. **스토리별 데모**: 각 스토리의 승인 기준 시연
2. **통합 시나리오 테스트**: 실제 사용 시나리오 검증
3. **사용성 테스트**: 사용자 경험 및 인터페이스 검증
