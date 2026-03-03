# Agent Management API 테스트 가이드

## 1. 백엔드 서버 실행

### 인증 우회 모드로 실행 (개발용)
```bash
cd apps/backend
SKIP_AUTH=true python3 -m uvicorn app.main:app --reload
```

서버가 실행되면:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 2. 자동 테스트 스크립트 실행

```bash
cd apps/backend
python3 scripts/test_agent_api.py
```

## 3. 수동 테스트 (Swagger UI)

1. 브라우저에서 http://localhost:8000/docs 접속
2. 각 API 엔드포인트 테스트

### 3.1 Agent 생성
```
POST /api/v1/agents
```

Request Body:
```json
{
  "name": "Customer Support Agent",
  "description": "고객 지원 AI 에이전트",
  "llm_model_id": "anthropic.claude-3-sonnet",
  "llm_model_name": "Claude 3 Sonnet",
  "llm_provider": "Anthropic",
  "system_prompt": "You are a helpful customer support agent.",
  "temperature": 0.7,
  "max_tokens": 2000,
  "knowledge_bases": [],
  "mcps": [],
  "team_tags": []
}
```

### 3.2 Agent 조회
```
GET /api/v1/agents/{agent_id}
```

### 3.3 Agent 목록 조회
```
GET /api/v1/agents?page=1&page_size=20
```

### 3.4 Agent 수정
```
PUT /api/v1/agents/{agent_id}
```

### 3.5 Agent 상태 변경
```
PATCH /api/v1/agents/{agent_id}
```

Request Body:
```json
{
  "enabled": false
}
```

### 3.6 버전 히스토리 조회
```
GET /api/v1/agents/{agent_id}/versions
```

## 4. DynamoDB 데이터 확인

### AWS CLI로 확인
```bash
# Agent 목록 조회
aws dynamodb scan --table-name AgentManagement --filter-expression "EntityType = :type" --expression-attribute-values '{":type":{"S":"Agent"}}'

# 특정 Agent 조회
aws dynamodb get-item --table-name AgentManagement --key '{"PK":{"S":"AGENT#<agent-id>"},"SK":{"S":"METADATA"}}'

# Agent 버전 조회
aws dynamodb query --table-name AgentManagement --key-condition-expression "PK = :pk AND begins_with(SK, :sk)" --expression-attribute-values '{":pk":{"S":"AGENT#<agent-id>"},":sk":{"S":"VERSION#"}}'
```

## 5. 예상 결과

### Agent 생성 성공
- Status: 201
- Response에 agent_id 포함
- current_version: "v1.0.0"
- DynamoDB에 2개 항목 생성:
  - AGENT#{id} / METADATA
  - AGENT#{id} / VERSION#v1.0.0

### Agent 수정 성공
- Status: 200
- current_version: "v1.1.0" (자동 증가)
- DynamoDB에 새 버전 항목 추가:
  - AGENT#{id} / VERSION#v1.1.0

### 버전 히스토리 조회
- 최신순으로 정렬된 버전 목록
- 각 버전의 change_log 포함

## 6. 문제 해결

### 서버 실행 오류
```bash
# Python 패키지 재설치
pip install -r requirements.txt

# DynamoDB 테이블 재생성
python3 scripts/create_dynamodb_tables.py
```

### AWS 자격증명 오류
```bash
# AWS 자격증명 확인
aws sts get-caller-identity

# 프로필 설정
export AWS_PROFILE=default
```
