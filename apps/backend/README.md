# AWS Agentic AI Platform - Backend

Python FastAPI 기반 백엔드 API 서버입니다.

## 기술 스택

- **Python 3.11+**
- **FastAPI** - 웹 프레임워크
- **Uvicorn** - ASGI 서버
- **Pydantic** - 데이터 검증
- **SQLAlchemy** - ORM (향후 사용)
- **Boto3** - AWS SDK
- **Pytest** - 테스팅

## 시작하기

### 1. 가상환경 생성 및 활성화

```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
# or
venv\Scripts\activate  # Windows
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt

# 개발 의존성도 설치
pip install -r requirements-dev.txt
```

### 3. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 편집하여 실제 값 설정
```

### 4. 개발 서버 실행

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

서버가 http://localhost:8000 에서 실행됩니다.

## API 문서

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 프로젝트 구조

```
app/
├── __init__.py
├── main.py              # FastAPI 앱 진입점
├── config.py            # 설정 관리
├── api/
│   └── v1/              # API v1 엔드포인트
│       ├── agents.py
│       ├── mcp.py
│       ├── kb.py
│       ├── gateway.py
│       ├── blueprint.py
│       ├── playground.py
│       └── settings.py
├── models/              # SQLAlchemy 모델
├── schemas/             # Pydantic 스키마
├── services/            # 비즈니스 로직
├── db/                  # 데이터베이스 설정
├── utils/               # 유틸리티 함수
└── tests/               # 테스트
```

## 개발 가이드

### 코드 포맷팅

```bash
# Black 포맷터
black app/

# Ruff 린터
ruff check app/
```

### 타입 체크

```bash
mypy app/
```

### 테스트 실행

```bash
pytest
pytest --cov=app  # 커버리지 포함
```

## Docker

### 이미지 빌드

```bash
docker build -t aws-agentic-ai-backend .
```

### 컨테이너 실행

```bash
docker run -p 8000:8000 --env-file .env aws-agentic-ai-backend
```

## API 엔드포인트

### MCP Management
- `GET /api/v1/mcps` - MCP 목록 조회
- `GET /api/v1/mcps/{id}` - MCP 상세 조회
- `POST /api/v1/mcps` - MCP 생성
- `PATCH /api/v1/mcps/{id}` - MCP 수정 (상태 변경 포함)
- `DELETE /api/v1/mcps/{id}` - MCP 삭제

### Agent Management
- `GET /api/v1/agents` - Agent 목록 조회
- `GET /api/v1/agents/{id}` - Agent 상세 조회
- `POST /api/v1/agents` - Agent 생성
- `PATCH /api/v1/agents/{id}` - Agent 수정 (상태 변경 포함)
- `DELETE /api/v1/agents/{id}` - Agent 삭제
- `POST /api/v1/agents/{id}/deploy` - Agent 배포

### Knowledge Base Management
- `GET /api/v1/knowledge-bases` - KB 목록 조회
- `GET /api/v1/knowledge-bases/{id}` - KB 상세 조회
- `POST /api/v1/knowledge-bases` - KB 생성
- `PATCH /api/v1/knowledge-bases/{id}` - KB 수정 (상태 변경 포함)
- `DELETE /api/v1/knowledge-bases/{id}` - KB 삭제

### API Catalog
- `GET /api/v1/api-catalog` - API 목록 조회 (검색/필터 지원)
- `POST /api/v1/api-catalog/sync` - KEIS API 동기화

### Team Tags
- `GET /api/v1/team-tags` - 팀 태그 목록 조회
- `GET /api/v1/team-tags/{id}/resources` - 팀 태그별 리소스 조회
- `POST /api/v1/team-tags` - 팀 태그 생성
- `DELETE /api/v1/team-tags/{id}` - 팀 태그 삭제

### Dashboard
- `GET /api/v1/dashboard/stats` - 대시보드 통계 (MCP/Agent/KB 현황)

## 개발 상태

### 현재 구현 상태
현재 프론트엔드는 **MSW(Mock Service Worker)**를 사용하여 API를 모킹하고 있습니다. 백엔드는 향후 구현 예정이며, 아래는 로드맵입니다.

### TODO

- [ ] 데이터베이스 연결 구현 (PostgreSQL/RDS)
- [ ] AWS Bedrock AgentCore 통합
  - [ ] Runtime 배포
  - [ ] MCP Gateway 생성 및 관리
  - [ ] Agent 배포 및 관리
- [ ] 인증/인가 구현 (Okta 토큰 검증)
- [ ] 각 엔드포인트 실제 비즈니스 로직 구현
- [ ] S3 통합 (Knowledge Base 파일 업로드)
- [ ] KEIS API 연동 (API Catalog 동기화)
- [ ] 테스트 코드 작성 (Pytest)
- [ ] CI/CD 파이프라인 구축
- [ ] Docker/ECS 배포 설정
- [ ] 모니터링 및 로깅 (CloudWatch)
