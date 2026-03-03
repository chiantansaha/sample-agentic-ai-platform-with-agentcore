# Agent Management 테스트

## 테스트 구조

```
tests/
├── unit/                    # 단위 테스트
│   ├── test_agent_entity.py
│   └── test_value_objects.py
└── integration/             # 통합 테스트
    └── test_agent_service.py
```

## 테스트 실행

### 모든 테스트 실행
```bash
cd apps/backend
pytest app/agent/tests/
```

### 단위 테스트만 실행
```bash
pytest app/agent/tests/unit/
```

### 통합 테스트만 실행
```bash
pytest app/agent/tests/integration/
```

### 특정 테스트 파일 실행
```bash
pytest app/agent/tests/unit/test_agent_entity.py
```

### 커버리지 포함 실행
```bash
pytest app/agent/tests/ --cov=app/agent --cov-report=html
```

## 테스트 범위

### 단위 테스트
- ✅ Agent Entity 생성, 업데이트, 상태 변경
- ✅ Value Objects (AgentId, Version, LLMModel, Instruction)
- ✅ 버전 증가 로직

### 통합 테스트
- ✅ Agent 생성 Use Case
- ✅ Agent 조회 Use Case
- ✅ Agent 수정 Use Case
- ✅ Agent 상태 변경 Use Case
- ✅ 예외 처리 (AgentNotFoundException)

## 필요한 패키지

```bash
pip install pytest pytest-asyncio pytest-cov
```
