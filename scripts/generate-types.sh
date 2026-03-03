#!/bin/bash

# OpenAPI 스펙에서 TypeScript 타입 자동 생성 스크립트

echo "🚀 Starting type generation..."

# 1. Backend 서버 시작 (인증 스킵, 개발 모드)
echo "📦 Starting backend server..."
cd apps/backend
SKIP_AUTH=true ENV_MODE=development uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ../..

# 2. 서버가 준비될 때까지 대기
echo "⏳ Waiting for backend to be ready..."
sleep 5

# 3. OpenAPI 스펙 다운로드
echo "📥 Downloading OpenAPI specification..."
curl -s http://localhost:8000/openapi.json -o openapi.json

# 4. Backend 서버 종료
echo "🛑 Stopping backend server..."
kill $BACKEND_PID

# 5. TypeScript 타입 생성 (openapi-typescript 사용)
echo "✨ Generating TypeScript types..."
npx openapi-typescript openapi.json -o packages/shared-types/src/generated.types.ts

# 6. OpenAPI 스펙 파일 삭제
rm openapi.json

echo "✅ Type generation completed successfully!"
echo "📝 Generated file: packages/shared-types/src/generated.types.ts"
