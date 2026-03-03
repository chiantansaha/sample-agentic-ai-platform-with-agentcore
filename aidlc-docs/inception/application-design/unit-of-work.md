# 단위 작업 정의 및 책임

## 시스템 분해 전략

### 분해 결정 요약
- **배포 모델**: 모듈러 모놀리스 (단일 애플리케이션, 도메인별 모듈)
- **프론트엔드**: 단일 SPA (모든 기능이 하나의 애플리케이션)
- **백엔드**: 단일 API 서비스 (모든 도메인이 하나의 FastAPI 앱)
- **파일 처리**: 도메인별 Lambda 함수 (KB 전용, MCP 전용 등)
- **데이터 소유권**: 도메인별 데이터 소유권 (각 도메인이 자체 데이터 관리)
- **개발 순서**: 의존성 기반 순서 (의존성이 적은 것부터)
- **통합 전략**: 직접 통합 (라이브러리/모듈 import)
- **코드 구조**: 워크스페이스 기반 (패키지 매니저 워크스페이스)

---

## 개발 단위 정의

### Unit 1: Frontend Application
**단위 유형**: React SPA
**배포 단위**: 독립 배포 가능
**개발 우선순위**: 2 (Backend API 이후)

#### 책임
- 사용자 인터페이스 제공
- 사용자 상호작용 처리
- 상태 관리 (Zustand)
- API 통신 관리
- 라우팅 및 네비게이션

#### 기술 스택
- **프레임워크**: React 18+ with TypeScript
- **상태 관리**: Zustand
- **라우팅**: React Router
- **UI 라이브러리**: Material-UI 또는 Ant Design
- **HTTP 클라이언트**: Axios
- **빌드 도구**: Vite
- **테스팅**: Jest + React Testing Library

#### 주요 컴포넌트
- MCP 관리 컴포넌트 (등록, 목록, 상세)
- 지식베이스 관리 컴포넌트 (생성, 파일 업로드, 상태 모니터링)
- 에이전트 관리 컴포넌트 (생성, 구성, 배포)
- 플레이그라운드 컴포넌트 (채팅 인터페이스, 세션 관리)
- 공통 컴포넌트 (레이아웃, 폼, 테이블, 모달)

#### 디렉토리 구조
```
frontend/
├── src/
│   ├── components/
│   │   ├── mcp/
│   │   ├── knowledge-base/
│   │   ├── agent/
│   │   ├── playground/
│   │   └── shared/
│   ├── pages/
│   ├── services/
│   ├── stores/
│   ├── types/
│   └── utils/
├── public/
├── tests/
└── package.json
```

---

### Unit 2: Backend API Service
**단위 유형**: FastAPI 모놀리스
**배포 단위**: 독립 배포 가능
**개발 우선순위**: 1 (최우선 - 다른 단위들의 의존성)

#### 책임
- RESTful API 제공
- 비즈니스 로직 처리
- 데이터 액세스 관리
- 외부 서비스 통합 (AWS)
- 인증 및 권한 관리 (향후)
- 오류 처리 및 로깅

#### 기술 스택
- **프레임워크**: FastAPI with Python 3.11+
- **ORM**: SQLAlchemy (DynamoDB 어댑터)
- **검증**: Pydantic
- **비동기**: asyncio, aiohttp
- **테스팅**: pytest, pytest-asyncio
- **문서화**: FastAPI 자동 문서화
- **배포**: Docker + AWS ECS/Lambda

#### 도메인 모듈 구조
```python
# 도메인별 모듈 구성
backend/
├── app/
│   ├── domains/
│   │   ├── mcp/
│   │   │   ├── models.py
│   │   │   ├── services.py
│   │   │   ├── repositories.py
│   │   │   └── routers.py
│   │   ├── knowledge_base/
│   │   ├── agent/
│   │   └── playground/
│   ├── shared/
│   │   ├── adapters/
│   │   ├── exceptions/
│   │   └── utils/
│   └── main.py
├── tests/
└── requirements.txt
```

#### API 엔드포인트 구조
- `/api/v1/mcps/` - MCP 관리 API
- `/api/v1/knowledge-bases/` - 지식베이스 관리 API
- `/api/v1/agents/` - 에이전트 관리 API
- `/api/v1/playground/` - 플레이그라운드 API
- `/api/v1/health/` - 헬스체크 API

---

### Unit 3: Knowledge Base Processing
**단위 유형**: AWS Lambda 함수 집합
**배포 단위**: 독립 배포 가능 (각 함수별)
**개발 우선순위**: 3 (Backend API 이후)

#### 책임
- 파일 업로드 처리
- 텍스트 추출 및 청킹
- 벡터 임베딩 생성
- OpenSearch 인덱싱
- 처리 상태 업데이트

#### Lambda 함수 구성
1. **File Upload Handler**
   - S3 업로드 이벤트 처리
   - 파일 메타데이터 추출
   - 처리 큐에 작업 추가

2. **Text Extraction Function**
   - 다양한 파일 형식 지원 (PDF, DOCX, TXT)
   - 텍스트 추출 및 정제
   - 청킹 처리

3. **Vector Generation Function**
   - Bedrock 임베딩 API 호출
   - 벡터 생성 및 검증
   - 배치 처리 최적화

4. **Index Update Function**
   - OpenSearch 인덱스 업데이트
   - 메타데이터 저장
   - 상태 업데이트

#### 기술 스택
- **런타임**: Python 3.11
- **AWS SDK**: boto3
- **텍스트 처리**: PyPDF2, python-docx
- **벡터 처리**: numpy, scikit-learn
- **배포**: AWS SAM 또는 CDK

---

### Unit 4: MCP Container Processing
**단위 유형**: AWS Lambda 함수 집합
**배포 단위**: 독립 배포 가능 (각 함수별)
**개발 우선순위**: 4 (Backend API 이후)

#### 책임
- 컨테이너 이미지 업로드 처리
- 이미지 검증 및 스캔
- ECR 등록 관리
- AgentCore 런타임 배포
- 배포 상태 모니터링

#### Lambda 함수 구성
1. **Container Upload Handler**
   - S3 컨테이너 업로드 이벤트 처리
   - 이미지 검증 및 보안 스캔
   - ECR 푸시 작업

2. **Runtime Deployment Function**
   - AgentCore 런타임 배포
   - 배포 상태 모니터링
   - 롤백 처리

3. **Health Check Function**
   - 배포된 MCP 상태 확인
   - 헬스체크 수행
   - 상태 업데이트

#### 기술 스택
- **런타임**: Python 3.11
- **컨테이너**: Docker SDK
- **AWS SDK**: boto3
- **보안 스캔**: AWS Inspector 통합

---

## 워크스페이스 구조

### 전체 프로젝트 구조
```
agentic-ai-platform/                    # 프로젝트 루트
├── package.json                        # 워크스페이스 설정
├── pnpm-workspace.yaml                 # pnpm 워크스페이스 구성
├── docker-compose.yml                  # 로컬 개발 환경
├── .github/                            # CI/CD 워크플로우
├── docs/                               # 프로젝트 문서
├── aidlc-docs/                         # AI-DLC 문서 (기존)
│
├── packages/                           # 워크스페이스 패키지
│   ├── frontend/                       # Unit 1: Frontend Application
│   │   ├── package.json
│   │   ├── src/
│   │   ├── public/
│   │   └── tests/
│   │
│   ├── backend/                        # Unit 2: Backend API Service
│   │   ├── pyproject.toml
│   │   ├── app/
│   │   ├── tests/
│   │   └── Dockerfile
│   │
│   ├── kb-processing/                  # Unit 3: KB Processing Functions
│   │   ├── template.yaml               # SAM 템플릿
│   │   ├── functions/
│   │   │   ├── file-upload/
│   │   │   ├── text-extraction/
│   │   │   ├── vector-generation/
│   │   │   └── index-update/
│   │   └── tests/
│   │
│   └── mcp-processing/                 # Unit 4: MCP Processing Functions
│       ├── template.yaml
│       ├── functions/
│       │   ├── container-upload/
│       │   ├── runtime-deployment/
│       │   └── health-check/
│       └── tests/
│
├── infrastructure/                     # AWS 인프라 코드
│   ├── cdk/                           # CDK 스택
│   └── terraform/                     # Terraform 구성 (선택사항)
│
└── scripts/                           # 빌드 및 배포 스크립트
    ├── build.sh
    ├── deploy.sh
    └── test.sh
```

### 워크스페이스 설정

#### package.json (루트)
```json
{
  "name": "agentic-ai-platform",
  "private": true,
  "workspaces": [
    "packages/*"
  ],
  "scripts": {
    "build": "pnpm -r build",
    "test": "pnpm -r test",
    "dev": "pnpm -r dev",
    "deploy": "./scripts/deploy.sh"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "typescript": "^5.0.0",
    "prettier": "^3.0.0",
    "eslint": "^8.0.0"
  }
}
```

#### pnpm-workspace.yaml
```yaml
packages:
  - 'packages/*'
  - 'infrastructure/*'
```

---

## 빌드 및 배포 전략

### 개발 환경
- **로컬 개발**: Docker Compose로 통합 환경
- **핫 리로드**: Frontend (Vite), Backend (uvicorn --reload)
- **테스트**: 단위별 독립 테스트 + 통합 테스트

### CI/CD 파이프라인
1. **코드 품질 검사**: ESLint, Prettier, pytest
2. **단위 테스트**: 각 패키지별 테스트 실행
3. **통합 테스트**: 전체 시스템 테스트
4. **빌드**: 각 단위별 빌드 아티팩트 생성
5. **배포**: 단위별 순차 배포 (의존성 순서)

### 배포 순서 (의존성 기반)
1. **Infrastructure** (AWS 리소스)
2. **Backend API Service** (핵심 API)
3. **KB Processing Functions** (파일 처리)
4. **MCP Processing Functions** (컨테이너 처리)
5. **Frontend Application** (사용자 인터페이스)

---

## 단위 간 통신

### 직접 통합 패턴
- **Frontend ↔ Backend**: HTTP REST API 호출
- **Backend ↔ AWS Services**: AWS SDK 직접 호출
- **Lambda Functions ↔ Backend**: DynamoDB 상태 업데이트
- **Lambda Functions ↔ AWS Services**: AWS SDK 직접 호출

### 데이터 흐름
1. **사용자 요청** → Frontend → Backend API
2. **파일 업로드** → Backend → S3 → Lambda (KB Processing)
3. **컨테이너 업로드** → Backend → S3 → Lambda (MCP Processing)
4. **상태 업데이트** → Lambda → DynamoDB → Backend → Frontend

### 오류 처리
- **Frontend**: 사용자 친화적 오류 메시지
- **Backend**: 구조화된 오류 응답
- **Lambda**: CloudWatch 로깅 + DynamoDB 상태 업데이트
- **통합**: 재시도 로직 및 회로 차단기 패턴
