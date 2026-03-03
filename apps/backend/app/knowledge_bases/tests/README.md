# KB Management 테스트

## 테스트 구조

```
tests/
├── unit/                    # 단위 테스트
│   └── test_kb_entity.py
└── integration/             # 통합 테스트
    └── test_kb_service.py
```

## 테스트 실행

### 모든 테스트 실행
```bash
cd apps/backend
pytest app/kb/tests/
```

### 단위 테스트만 실행
```bash
pytest app/kb/tests/unit/
```

### 통합 테스트만 실행
```bash
pytest app/kb/tests/integration/
```

## 테스트 범위

### 단위 테스트
- ✅ KB Entity 생성, 활성화/비활성화, 통계 업데이트

### 통합 테스트
- ✅ KB 생성 Use Case
- ✅ KB 조회 Use Case
- ✅ KB 목록 조회 Use Case
- ✅ KB 상태 변경 Use Case
- ✅ 예외 처리 (KBNotFoundException)
