# AWS Agentic AI Platform - Frontend

React 19 + TypeScript + Vite 기반의 프론트엔드 애플리케이션입니다.

## 기술 스택

- **React 19** - UI 라이브러리
- **TypeScript** - 타입 안전성
- **Vite** - 빌드 도구
- **Tailwind CSS v4** - 스타일링
- **React Router v7** - 라우팅
- **Zustand** - 상태 관리
- **TanStack Query** - 서버 상태 관리
- **Recharts** - 데이터 시각화
- **MSW** - API 모킹
- **Axios** - HTTP 클라이언트
- **Okta** - SSO 인증

## 개발 서버 실행

```bash
# 루트 디렉토리에서
pnpm dev:frontend

# 또는 이 디렉토리에서
pnpm dev
```

개발 서버는 http://localhost:5173 에서 실행됩니다.

## 빌드

```bash
# 루트 디렉토리에서
pnpm build:frontend

# 또는 이 디렉토리에서
pnpm build
```

빌드된 파일은 `dist/` 디렉토리에 생성됩니다.

## Docker 빌드

```bash
# 루트 디렉토리에서 실행
docker build -f apps/frontend/Dockerfile -t aws-agentic-ai-frontend .
docker run -p 80:80 aws-agentic-ai-frontend
```

## 프로젝트 구조

```
src/
├── components/        # React 컴포넌트
│   ├── agent/        # Agent 관련 컴포넌트 (AgentCard, DeployModal 등)
│   ├── auth/         # 인증 관련 컴포넌트 (AuthSync 등)
│   ├── common/       # 공통 컴포넌트 (Button, Card, Modal, Badge 등)
│   ├── kb/           # Knowledge Base 관련
│   ├── mcp/          # MCP 관련 컴포넌트 (MCPCard 등)
│   └── layout/       # 레이아웃 컴포넌트 (MainLayout, Sidebar 등)
├── pages/            # 페이지 컴포넌트
│   ├── agent/        # Agent 목록, 상세, 생성, 편집
│   ├── api-catalog/  # API Catalog 목록
│   ├── auth/         # 로그인, 콜백
│   ├── dashboard/    # 대시보드
│   ├── kb/           # Knowledge Base 목록, 상세, 생성, 편집
│   ├── mcp/          # MCP 목록, 상세, 생성, 편집
│   ├── playground/   # Agent 테스트 Playground
│   └── team-tags/    # 팀 태그 관리
├── contexts/         # React Context (ToastContext 등)
├── hooks/            # Custom hooks (useRecentActivity 등)
├── config/           # 설정 파일 (oktaConfig 등)
├── store/            # Zustand 스토어
├── api/              # API 클라이언트 함수
├── mocks/            # MSW 핸들러 (data.ts, handlers.ts)
├── types/            # TypeScript 타입 정의
└── utils/            # 유틸리티 함수
```

## 공유 패키지 사용

이 프론트엔드 앱은 다음 공유 패키지들을 사용합니다:

- `@agentic-ai/shared-types` - 공통 타입 정의
- `@agentic-ai/shared-constants` - 공통 상수
- `@agentic-ai/shared-utils` - 공통 유틸리티 함수
- `@agentic-ai/api-client` - Axios 기반 API 클라이언트

## 환경 변수

`.env` 파일에 다음 환경 변수를 설정하세요:

```env
# API
VITE_API_BASE_URL=http://localhost:8000

# Okta Configuration
VITE_OKTA_ISSUER=https://your-okta-domain.okta.com/oauth2/your-auth-server-id
VITE_OKTA_DOMAIN=https://your-okta-domain.okta.com
VITE_OKTA_CLIENT_ID=your-client-id
VITE_OKTA_REDIRECT_URI=http://localhost:5173/login/callback
VITE_OKTA_POST_LOGOUT_REDIRECT_URI=http://localhost:5173
VITE_OKTA_SCOPES=openid profile email
```

`.env.example` 파일을 참고하여 설정하세요.

## 주요 기능

### Dashboard
- **실시간 통계**: MCP, Agent, KB 전체 현황 카드
- **Quick Actions**: 빠른 생성 및 Playground 바로가기
- **Recent Activity**: localStorage 기반 최근 방문 페이지 추적 (최대 5개)

### MCP 관리
- **3가지 타입 지원**:
  - External: 외부 MCP 등록
  - Internal (API): API 기반 내부 MCP
  - Internal (Container): 컨테이너 기반 내부 MCP
- **버전 관리**: 히스토리 및 엔드포인트 추적
- **Enable/Disable 토글**: 확인 모달과 함께 상태 변경

### Agent 관리
- **배포 관리**: Runtime, Spec Export, ECR Image 배포
- **Playground 테스트**: 실시간 대화 테스트
- **버전 관리**: Production 배포 히스토리
- **Enable/Disable 토글**: 안전한 상태 변경

### Knowledge Base 관리
- **데이터 소스**: S3, 파일 업로드 지원
- **문서 통계**: 문서 수, 용량 추적
- **Enable/Disable 토글**: 신규 연동 경고와 함께 상태 변경

### API Catalog
- **KEIS 동기화**: 외부 API 목록 자동 동기화
- **검색 및 필터**: API명, 설명, 팀 태그로 검색

### Team Tags
- **리소스 관리**: 태그별 리소스 그룹핑
- **사용 현황 팝업**: 클릭 시 연결된 MCP, Agent, KB, API 조회
- **직접 이동**: 팝업에서 각 리소스로 바로 이동

### Toast 알림 시스템
- **4가지 타입**: success, error, warning, info
- **블루 톤 디자인**: 플랫폼 일관성 유지
- **자동 닫힘**: 3초 후 자동 사라짐
- **다중 알림**: 여러 알림 동시 표시 가능

## API 모킹 (MSW)

개발 중에는 MSW(Mock Service Worker)를 사용하여 API를 모킹합니다.

**핸들러 파일:**
- `src/mocks/handlers.ts` - API 엔드포인트 정의
- `src/mocks/data.ts` - Mock 데이터

**주요 엔드포인트:**
- `/api/v1/mcps` - MCP CRUD
- `/api/v1/agents` - Agent CRUD
- `/api/v1/knowledge-bases` - KB CRUD
- `/api/v1/api-catalog` - API Catalog 조회 및 동기화
- `/api/v1/team-tags` - Team Tag 관리
- `/api/v1/dashboard/stats` - Dashboard 통계

## Okta SSO 인증

이 애플리케이션은 Okta를 사용한 SSO(Single Sign-On) 인증을 지원합니다.

### 설정 방법

1. **Okta 계정 및 애플리케이션 생성**
   - Okta 개발자 콘솔에서 새 애플리케이션 생성
   - Application type: Single-Page Application (SPA)
   - Grant type: Authorization Code + PKCE

2. **환경 변수 설정**
   - `.env.example`을 복사하여 `.env` 파일 생성
   - Okta 관련 환경 변수 설정:
     - `VITE_OKTA_ISSUER`: Okta Authorization Server URL
     - `VITE_OKTA_CLIENT_ID`: 애플리케이션 Client ID
     - `VITE_OKTA_REDIRECT_URI`: 콜백 URL (기본값: `http://localhost:5173/login/callback`)

3. **Okta 애플리케이션 설정**
   - Sign-in redirect URIs: `http://localhost:5173/login/callback`
   - Sign-out redirect URIs: `http://localhost:5173`
   - Trusted Origins에 `http://localhost:5173` 추가

### 인증 플로우

1. 사용자가 로그인 페이지에서 "Okta로 로그인" 버튼 클릭
2. Okta 로그인 페이지로 리다이렉트
3. 로그인 성공 후 `/login/callback`으로 리다이렉트
4. 애플리케이션이 토큰을 처리하고 사용자 정보를 저장
5. 홈페이지로 자동 이동

### 세션 관리
- **비활성 타임아웃**: 30분 (사용자 활동 없을 시 자동 로그아웃)
- **절대 타임아웃**: 8시간 (최초 로그인 후 무조건 로그아웃)
- **실시간 동기화**: 다른 탭에서 로그아웃 시 모든 탭 즉시 반영

### 주요 파일
- `src/config/oktaConfig.ts` - Okta 설정
- `src/pages/auth/Login.tsx` - 로그인 페이지
- `src/pages/auth/LoginCallback.tsx` - OAuth 콜백 처리
- `src/components/auth/AuthSync.tsx` - 세션 동기화 및 타임아웃
- `src/store/authStore.ts` - 인증 상태 관리

## 린트

```bash
pnpm lint
```
