# 애플리케이션 설계 계획

## 실행 체크리스트

### 1단계: 컴포넌트 식별 및 정의
- [x] 프론트엔드 컴포넌트 식별 (React 컴포넌트 구조)
- [x] 백엔드 API 컴포넌트 식별 (FastAPI 모듈 구조)
- [x] 파일 처리 컴포넌트 식별 (벡터 임베딩 처리)
- [x] 외부 서비스 통합 컴포넌트 식별 (AWS 서비스 연동)

### 2단계: 컴포넌트 메서드 정의
- [x] 각 컴포넌트의 주요 메서드 시그니처 정의
- [x] 메서드 입력/출력 타입 정의
- [x] 메서드 간 호출 관계 정의

### 3단계: 서비스 레이어 설계
- [x] MCP 관리 서비스 설계
- [x] 지식베이스 관리 서비스 설계
- [x] 에이전트 관리 서비스 설계
- [x] 플레이그라운드 서비스 설계
- [x] 공통 서비스 (인증, 로깅, 오류 처리) 설계

### 4단계: 컴포넌트 의존성 분석
- [x] 컴포넌트 간 의존성 매트릭스 생성
- [x] 데이터 플로우 다이어그램 생성
- [x] 통신 패턴 정의

### 5단계: 설계 검증 및 정제
- [x] 설계 완전성 검증
- [x] 설계 일관성 검증
- [x] 사용자 스토리와 설계 매핑 확인

## 설계 결정 질문

다음 질문들에 답하여 애플리케이션 설계 방향을 결정해주세요:

### 질문 1: 프론트엔드 컴포넌트 구조
React 애플리케이션의 컴포넌트 구조를 어떻게 조직하시겠습니까?

A) 기능별 구조 (MCP, KB, Agent, Playground 폴더로 분리)
B) 계층별 구조 (components, pages, services, utils 폴더로 분리)
C) 도메인별 구조 (각 도메인이 자체 components, services, types 포함)
D) 하이브리드 구조 (기능별 + 계층별 조합)
E) 기타 (아래 [Answer]: 태그 뒤에 설명해주세요)

[Answer]: D

### 질문 2: 백엔드 API 구조
FastAPI 백엔드의 모듈 구조를 어떻게 조직하시겠습니까?

A) 기능별 라우터 (mcp, knowledge_base, agent, playground 라우터)
B) 계층별 구조 (routers, services, models, utils 분리)
C) 도메인 주도 설계 (각 도메인이 완전한 모듈)
D) 마이크로서비스 스타일 (독립적인 서비스 모듈)
E) 기타 (아래 [Answer]: 태그 뒤에 설명해주세요)

[Answer]: C

### 질문 3: 데이터 액세스 패턴
DynamoDB와의 데이터 액세스를 어떻게 구조화하시겠습니까?

A) 직접 액세스 (각 서비스에서 직접 DynamoDB 호출)
B) 리포지토리 패턴 (데이터 액세스 레이어 분리)
C) ORM/ODM 사용 (PynamoDB 등 사용)
D) 데이터 서비스 레이어 (중앙화된 데이터 서비스)
E) 기타 (아래 [Answer]: 태그 뒤에 설명해주세요)

[Answer]: B

### 질문 4: 파일 처리 아키텍처
파일 업로드 및 벡터 처리를 어떻게 구조화하시겠습니까?

A) 동기 처리 (API 요청 내에서 모든 처리 완료)
B) 비동기 작업 큐 (Celery, RQ 등 사용)
C) AWS Lambda 함수 (S3 이벤트 트리거)
D) 백그라운드 스레드 (FastAPI BackgroundTasks)
E) 기타 (아래 [Answer]: 태그 뒤에 설명해주세요)

[Answer]: C

### 질문 5: 외부 서비스 통합
AWS 서비스 (Bedrock, AgentCore, OpenSearch) 통합을 어떻게 구조화하시겠습니까?

A) 직접 통합 (각 서비스에서 직접 AWS SDK 호출)
B) 어댑터 패턴 (AWS 서비스별 어댑터 클래스)
C) 팩토리 패턴 (서비스 팩토리를 통한 인스턴스 생성)
D) 의존성 주입 (DI 컨테이너 사용)
E) 기타 (아래 [Answer]: 태그 뒤에 설명해주세요)

[Answer]: B

### 질문 6: 오류 처리 전략
애플리케이션 전반의 오류 처리를 어떻게 구조화하시겠습니까?

A) 중앙화된 오류 핸들러 (글로벌 예외 처리)
B) 계층별 오류 처리 (각 계층에서 적절한 처리)
C) 도메인별 오류 처리 (각 도메인의 특화된 처리)
D) 혼합 접근법 (중앙화 + 도메인별)
E) 기타 (아래 [Answer]: 태그 뒤에 설명해주세요)

[Answer]: C

### 질문 7: 상태 관리 (프론트엔드)
React 애플리케이션의 상태 관리를 어떻게 구조화하시겠습니까?

A) React 내장 상태 (useState, useContext)
B) Redux Toolkit (중앙화된 상태 관리)
C) Zustand (경량 상태 관리)
D) React Query + 로컬 상태 (서버 상태와 클라이언트 상태 분리)
E) 기타 (아래 [Answer]: 태그 뒤에 설명해주세요)

[Answer]: C

## 생성될 아티팩트
- `aidlc-docs/inception/application-design/components.md` - 컴포넌트 정의 및 책임
- `aidlc-docs/inception/application-design/component-methods.md` - 메서드 시그니처 및 목적
- `aidlc-docs/inception/application-design/services.md` - 서비스 정의 및 오케스트레이션
- `aidlc-docs/inception/application-design/component-dependency.md` - 의존성 관계 및 통신 패턴
