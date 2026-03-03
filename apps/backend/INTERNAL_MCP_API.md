# Internal MCP 생성 API 스펙

## 개요
Internal MCP는 2가지 타입으로 생성할 수 있습니다:
1. **Internal-Deploy**: ECR 이미지 기반 MCP 배포
2. **Internal-Create**: API 선택 기반 MCP 생성

## API 엔드포인트

### 1. Internal Deploy MCP 생성

**POST** `/api/v1/mcps/`

```json
{
  "type": "internal-deploy",
  "name": "my-deploy-mcp",
  "description": "ECR 이미지 기반 MCP",
  "team_tags": ["backend-team", "devops-team"],
  "ecr_repository": "my-company/mcp-server",
  "image_tag": "v1.0.0",
  "resources": {
    "cpu": "256",
    "memory": "512",
    "replicas": 2
  },
  "environment": {
    "ENV": "production",
    "LOG_LEVEL": "info"
  }
}
```

**응답:**
```json
{
  "success": true,
  "data": {
    "id": "mcp-12345678",
    "name": "my-deploy-mcp",
    "type": "internal-deploy",
    "status": "enabled",
    "endpoint": "https://gw-00000001.gateway.bedrock-agentcore.ap-northeast-2.amazonaws.com/mcp"
  }
}
```

### 2. Internal Create MCP 생성

**POST** `/api/v1/mcps/`

```json
{
  "type": "internal-create",
  "name": "my-create-mcp",
  "description": "API 선택 기반 MCP",
  "team_tags": ["frontend-team", "api-team"],
  "selected_api_ids": ["flight-search", "hotel-booking"]
}
```

**응답:**
```json
{
  "success": true,
  "data": {
    "id": "mcp-87654321",
    "name": "my-create-mcp",
    "type": "internal-create",
    "status": "enabled",
    "endpoint": "https://gw-00000002.gateway.bedrock-agentcore.ap-northeast-2.amazonaws.com/mcp"
  }
}
```

### 3. 사용 가능한 API 목록 조회

**GET** `/api/v1/apis/available` (구현 필요)

```json
{
  "data": [
    {
      "id": "api-1",
      "name": "Flight Search API",
      "api_id": "flight-search",
      "endpoint": "https://api.example.aws/flight/search",
      "method": "POST",
      "auth_type": "oauth"
    },
    {
      "id": "api-2",
      "name": "Hotel Booking API", 
      "api_id": "hotel-booking",
      "endpoint": "https://api.example.aws/hotel/booking",
      "method": "POST",
      "auth_type": "api_key"
    }
  ]
}
```

## 필드 설명

### Internal Deploy MCP
- `ecr_repository`: ECR 리포지토리 경로
- `image_tag`: Docker 이미지 태그
- `resources`: 컨테이너 리소스 설정
- `environment`: 환경 변수

### Internal Create MCP
- `selected_api_ids`: 선택된 API ID 목록

## 에러 응답

```json
{
  "detail": "MCP with name 'my-mcp' already exists"
}
```

## 상태 코드
- `201`: 생성 성공
- `400`: 잘못된 요청
- `409`: 이름 중복
- `500`: 서버 오류

## 프론트엔드 구현 가이드

### 1. Internal Deploy MCP 생성 폼
- ECR Repository 입력 필드
- Image Tag 입력 필드  
- Resources 설정 (CPU, Memory, Replicas)
- Environment Variables 키-값 입력

### 2. Internal Create MCP 생성 폼
- Available APIs 목록 조회
- 다중 선택 체크박스
- 선택된 API 미리보기

### 3. 공통 필드
- Name (필수)
- Description (필수)
- Team Tags (다중 선택)

## 테스트 방법

```bash
# 1. 백엔드 서버 시작
cd apps/backend
SKIP_AUTH=true python -m uvicorn app.main:app --reload

# 2. 테스트 실행
python test_internal_mcp.py  # 도메인 로직 테스트
python test_http_mcp.py      # HTTP API 테스트
```
