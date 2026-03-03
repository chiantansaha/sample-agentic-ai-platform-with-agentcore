"""AgentCore Runtime 통합 테스트

실제 AgentCore Runtime에 배포하고 호출하는 전체 플로우 테스트
"""
import asyncio
import os
import time
import uuid
import pytest

# 환경 변수 설정
os.environ.setdefault('AWS_REGION', 'us-east-1')
os.environ.setdefault('AGENTCORE_CODE_BUCKET', 'bedrock-agentcore-runtime-982534381466-us-east-1-ulijapa6wh')
os.environ.setdefault('AGENTCORE_ROLE_ARN', 'arn:aws:iam::982534381466:role/AgentCoreRuntimeRole')


class TestAgentCoreIntegration:
    """AgentCore Runtime 통합 테스트"""

    @pytest.fixture
    def client(self):
        """AgentCoreClient 인스턴스"""
        from app.playground.infrastructure.clients.agentcore_client import AgentCoreClient
        return AgentCoreClient(
            region='us-east-1',
            s3_bucket=os.environ['AGENTCORE_CODE_BUCKET'],
            role_arn=os.environ['AGENTCORE_ROLE_ARN']
        )

    @pytest.fixture
    def code_generator(self):
        """AgentCodeGenerator 인스턴스"""
        from app.playground.infrastructure.code_generator import AgentCodeGenerator
        return AgentCodeGenerator()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_flow_deploy_and_invoke(self, client, code_generator):
        """전체 플로우 테스트: 코드 생성 → 업로드 → Runtime 생성 → 호출 → 정리"""

        runtime_id = None
        s3_prefix = None

        try:
            # 1. 코드 생성
            print("\n[1/6] 코드 생성...")
            agent_config = {
                "agent_id": f"test-{uuid.uuid4().hex[:8]}",
                "agent_name": "Integration Test Agent",
                "version": "1.0.0",
                "model_id": "anthropic.claude-3-haiku-20240307-v1:0",
                "system_prompt": "You are a helpful assistant. Always respond in Korean.",
                "temperature": 0.7,
                "max_tokens": 1000,
                "knowledge_bases": []
            }

            files = code_generator.generate(agent_config)
            assert "agent.py" in files
            assert "requirements.txt" in files
            print(f"  ✅ {len(files)}개 파일 생성됨")

            # 2. S3 업로드 (의존성 번들링 포함)
            print("\n[2/6] S3 업로드 (의존성 번들링)...")
            deployment_id = uuid.uuid4().hex[:8]
            s3_prefix = f"integration-test/{agent_config['agent_id']}/{deployment_id}"

            s3_uri = await client.upload_code(
                files=files,
                s3_prefix=s3_prefix,
                bundle_dependencies=True,
                include_strands=True  # 템플릿이 Strands를 사용하므로 포함
            )
            assert s3_uri.startswith("s3://")
            print(f"  ✅ 업로드 완료: {s3_uri}")

            # 3. Runtime 생성
            print("\n[3/6] Runtime 생성...")
            # Runtime 이름은 [a-zA-Z][a-zA-Z0-9_]{0,47} 패턴만 허용
            runtime_name = f"integ_test_{deployment_id}"

            result = await client.create_runtime(
                name=runtime_name,
                s3_uri=s3_uri,
                description="Integration test runtime"
            )

            runtime_id = result["runtime_id"]
            assert runtime_id is not None
            print(f"  ✅ Runtime 생성됨: {runtime_id}")

            # 4. Ready 대기
            print("\n[4/6] Ready 상태 대기...")
            runtime = await client.wait_for_ready(
                runtime_id=runtime_id,
                max_wait=300,
                poll_interval=10
            )

            assert runtime["status"] == "READY"
            runtime_arn = runtime["runtime_arn"]
            print(f"  ✅ Runtime READY: {runtime_arn}")

            # 5. 호출 테스트
            print("\n[5/6] 호출 테스트...")
            # runtimeSessionId는 최소 33자 필요
            session_id = str(uuid.uuid4())  # 36자 (하이픈 포함)
            payload = {
                "prompt": "안녕하세요! 간단히 자기소개 해주세요.",
                "session_id": session_id
            }

            response_text = ""
            async for event in client.invoke(
                runtime_arn=runtime_arn,
                payload=payload,
                session_id=payload["session_id"]
            ):
                event_type = event.get("type")
                if event_type == "text":
                    response_text += event.get("content", "")
                elif event_type == "error":
                    pytest.fail(f"Runtime error: {event.get('content')}")
                elif event_type == "done":
                    break

            print(f"  📥 응답: {response_text[:100]}...")
            assert len(response_text) > 0, "응답이 비어있음"
            print("  ✅ 호출 성공!")

        finally:
            # 6. 정리
            print("\n[6/6] 리소스 정리...")

            if runtime_id:
                try:
                    await client.delete_runtime(runtime_id)
                    print(f"  🗑️ Runtime 삭제됨: {runtime_id}")
                except Exception as e:
                    print(f"  ⚠️ Runtime 삭제 실패: {e}")

            if s3_prefix:
                try:
                    await client.cleanup_code(s3_prefix)
                    print(f"  🗑️ S3 정리됨: {s3_prefix}")
                except Exception as e:
                    print(f"  ⚠️ S3 정리 실패: {e}")


# 직접 실행용
if __name__ == "__main__":
    async def main():
        from app.playground.infrastructure.clients.agentcore_client import AgentCoreClient
        from app.playground.infrastructure.code_generator import AgentCodeGenerator

        client = AgentCoreClient(
            region='us-east-1',
            s3_bucket=os.environ['AGENTCORE_CODE_BUCKET'],
            role_arn=os.environ['AGENTCORE_ROLE_ARN']
        )
        code_generator = AgentCodeGenerator()

        test = TestAgentCoreIntegration()
        await test.test_full_flow_deploy_and_invoke(client, code_generator)

    asyncio.run(main())
