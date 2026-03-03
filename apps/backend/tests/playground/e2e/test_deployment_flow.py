"""E2E Tests - Deployment Flow (배포 → 채팅 → 종료)"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.playground.dto.response import (
    DeploymentResponse,
    DeploymentStatusResponse,
    DestroyResponse
)
from app.playground.domain.value_objects import DeploymentStatus
from app.playground.presentation.controller import get_deployment_service


# Note: client, app_with_auth, mock_token_payload fixtures are provided by conftest.py


class TestDeploymentToDestroyFlow:
    """배포 → 채팅 → 종료 E2E 플로우 테스트"""

    def test_full_deployment_lifecycle(
        self,
        app_with_auth,
        client,
        mock_token_payload
    ):
        """전체 배포 라이프사이클 테스트: 배포 → 상태확인 → 채팅 → 종료"""
        mock_service = AsyncMock()
        app_with_auth.dependency_overrides[get_deployment_service] = lambda: mock_service

        # Step 1: 배포 요청
        mock_service.deploy_agent.return_value = DeploymentResponse(
            id="deploy-e2e-123",
            agent_id="agent-456",
            version="1.0.0",
            status="pending",
            runtime_id=None,
            runtime_arn=None,
            endpoint_url=None,
            conversation_id=None,
            is_resumed=False,
            message_count=0,
            idle_timeout=300,
            max_lifetime=1800,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            expires_at="2024-01-01T00:30:00"
        )

        deploy_response = client.post(
            "/playground/runtime/deploy",
            json={"agent_id": "agent-456", "version": "1.0.0"},
        )

        assert deploy_response.status_code == 200
        deploy_data = deploy_response.json()
        assert deploy_data["data"]["id"] == "deploy-e2e-123"
        assert deploy_data["data"]["status"] == "pending"

        deployment_id = deploy_data["data"]["id"]

        # Step 2: 상태 확인 - pending
        mock_service.get_deployment_status.return_value = DeploymentStatusResponse(
            deployment_id=deployment_id,
            status="creating",
            runtime_arn=None,
            endpoint_url=None,
            created_at="2024-01-01T00:00:00",
            idle_timeout=300,
            max_lifetime=1800
        )

        status_response = client.get(
            f"/playground/runtime/deployments/{deployment_id}/status",
        )

        assert status_response.status_code == 200
        assert status_response.json()["data"]["status"] == "creating"

        # Step 3: 상태 확인 - ready
        mock_service.get_deployment_status.return_value = DeploymentStatusResponse(
            deployment_id=deployment_id,
            status="ready",
            runtime_arn="arn:aws:runtime:123",
            endpoint_url="https://runtime.endpoint.com",
            created_at="2024-01-01T00:00:00",
            idle_timeout=300,
            max_lifetime=1800
        )

        status_response = client.get(
            f"/playground/runtime/deployments/{deployment_id}/status",
        )

        assert status_response.status_code == 200
        assert status_response.json()["data"]["status"] == "ready"
        assert status_response.json()["data"]["endpoint_url"] == "https://runtime.endpoint.com"

        # Step 4: 채팅 (스트리밍)
        async def mock_stream():
            yield {"type": "text", "content": "안녕하세요! "}
            yield {"type": "text", "content": "도움이 필요하시면 말씀해주세요."}
            yield {"type": "done"}

        mock_service.stream_runtime_chat = MagicMock(return_value=mock_stream())

        chat_response = client.post(
            f"/playground/runtime/deployments/{deployment_id}/chat/stream",
            json={"message": "안녕하세요"},
        )

        assert chat_response.status_code == 200
        assert "text/event-stream" in chat_response.headers["content-type"]

        # Step 5: 종료
        mock_service.destroy_deployment.return_value = DestroyResponse(
            deployment_id=deployment_id,
            status="destroyed",
            message="Runtime이 성공적으로 종료되었습니다."
        )

        destroy_response = client.delete(
            f"/playground/runtime/deployments/{deployment_id}",
        )

        assert destroy_response.status_code == 200
        assert destroy_response.json()["data"]["status"] == "destroyed"

    def test_deployment_failure_handling(
        self,
        app_with_auth,
        client,
        mock_token_payload
    ):
        """배포 실패 처리 테스트"""
        mock_service = AsyncMock()
        app_with_auth.dependency_overrides[get_deployment_service] = lambda: mock_service

        # Step 1: 배포 요청
        mock_service.deploy_agent.return_value = DeploymentResponse(
            id="deploy-fail-123",
            agent_id="agent-456",
            version="1.0.0",
            status="pending",
            runtime_id=None,
            runtime_arn=None,
            endpoint_url=None,
            conversation_id=None,
            is_resumed=False,
            message_count=0,
            idle_timeout=300,
            max_lifetime=1800,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            expires_at=None
        )

        deploy_response = client.post(
            "/playground/runtime/deploy",
            json={"agent_id": "agent-456", "version": "1.0.0"},
        )

        assert deploy_response.status_code == 200
        deployment_id = deploy_response.json()["data"]["id"]

        # Step 2: 상태 확인 - failed
        mock_service.get_deployment_status.return_value = DeploymentStatusResponse(
            deployment_id=deployment_id,
            status="failed",
            runtime_arn=None,
            endpoint_url=None,
            created_at="2024-01-01T00:00:00",
            idle_timeout=300,
            max_lifetime=1800,
            error_message="Runtime 생성 중 오류 발생"
        )

        status_response = client.get(
            f"/playground/runtime/deployments/{deployment_id}/status",
        )

        assert status_response.status_code == 200
        status_data = status_response.json()["data"]
        assert status_data["status"] == "failed"
        assert status_data["error_message"] == "Runtime 생성 중 오류 발생"

    def test_multiple_chat_messages(
        self,
        app_with_auth,
        client,
        mock_token_payload
    ):
        """여러 채팅 메시지 연속 전송 테스트"""
        mock_service = AsyncMock()
        app_with_auth.dependency_overrides[get_deployment_service] = lambda: mock_service

        deployment_id = "deploy-chat-123"

        # 첫 번째 메시지
        async def mock_stream_1():
            yield {"type": "text", "content": "첫 번째 응답입니다."}
            yield {"type": "done"}

        mock_service.stream_runtime_chat = MagicMock(return_value=mock_stream_1())

        response_1 = client.post(
            f"/playground/runtime/deployments/{deployment_id}/chat/stream",
            json={"message": "첫 번째 메시지"},
        )

        assert response_1.status_code == 200

        # 두 번째 메시지
        async def mock_stream_2():
            yield {"type": "text", "content": "두 번째 응답입니다."}
            yield {"type": "done"}

        mock_service.stream_runtime_chat = MagicMock(return_value=mock_stream_2())

        response_2 = client.post(
            f"/playground/runtime/deployments/{deployment_id}/chat/stream",
            json={"message": "두 번째 메시지"},
        )

        assert response_2.status_code == 200

        # 세 번째 메시지
        async def mock_stream_3():
            yield {"type": "text", "content": "세 번째 응답입니다."}
            yield {"type": "done"}

        mock_service.stream_runtime_chat = MagicMock(return_value=mock_stream_3())

        response_3 = client.post(
            f"/playground/runtime/deployments/{deployment_id}/chat/stream",
            json={"message": "세 번째 메시지"},
        )

        assert response_3.status_code == 200
