"""Deployment API Endpoints Tests"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.playground.dto.response import DeploymentResponse, DeploymentStatusResponse, DestroyResponse
from app.playground.presentation.controller import get_deployment_service


# Note: client, app_with_auth, mock_token_payload fixtures are provided by conftest.py


@pytest.fixture
def mock_deployment_response():
    """Mock deployment response"""
    return DeploymentResponse(
        id="deploy-123",
        agent_id="agent-456",
        version="1.0.0",
        status="ready",
        runtime_id="runtime-001",
        runtime_arn="arn:aws:agentcore:runtime",
        endpoint_url="https://runtime.endpoint",
        conversation_id=None,
        is_resumed=False,
        message_count=0,
        idle_timeout=300,
        max_lifetime=1800,
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
        expires_at="2024-01-01T00:30:00"
    )


class TestDeployEndpoint:
    """POST /playground/runtime/deploy 테스트"""

    def test_deploy_agent_success(
        self,
        app_with_auth,
        client,
        mock_deployment_response
    ):
        """배포 성공 테스트"""
        # Arrange
        mock_service = AsyncMock()
        mock_service.deploy_agent.return_value = mock_deployment_response
        app_with_auth.dependency_overrides[get_deployment_service] = lambda: mock_service

        # Act
        response = client.post(
            "/playground/runtime/deploy",
            json={"agent_id": "agent-456", "version": "1.0.0"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == 200
        assert data["data"]["id"] == "deploy-123"

    def test_deploy_agent_not_found(
        self,
        app_with_auth,
        client
    ):
        """Agent 미존재 테스트"""
        from app.playground.exception.exceptions import AgentNotFoundException

        # Arrange
        mock_service = AsyncMock()
        mock_service.deploy_agent.side_effect = AgentNotFoundException("agent-999")
        app_with_auth.dependency_overrides[get_deployment_service] = lambda: mock_service

        # Act
        response = client.post(
            "/playground/runtime/deploy",
            json={"agent_id": "agent-999", "version": "1.0.0"},
        )

        # Assert
        assert response.status_code == 404

    def test_deploy_already_exists(
        self,
        app_with_auth,
        client
    ):
        """중복 배포 테스트"""
        from app.playground.exception.exceptions import DeploymentAlreadyExistsException

        # Arrange
        mock_service = AsyncMock()
        mock_service.deploy_agent.side_effect = DeploymentAlreadyExistsException("deploy-existing")
        app_with_auth.dependency_overrides[get_deployment_service] = lambda: mock_service

        # Act
        response = client.post(
            "/playground/runtime/deploy",
            json={"agent_id": "agent-456", "version": "1.0.0"},
        )

        # Assert
        assert response.status_code == 409


class TestDeploymentStatusEndpoint:
    """GET /playground/runtime/deployments/{id}/status 테스트"""

    def test_get_status_success(
        self,
        app_with_auth,
        client
    ):
        """상태 조회 성공 테스트"""
        # Arrange
        mock_service = AsyncMock()
        mock_service.get_deployment_status.return_value = DeploymentStatusResponse(
            deployment_id="deploy-123",
            status="ready",
            runtime_arn="arn:aws:runtime",
            endpoint_url="https://endpoint",
            created_at="2024-01-01T00:00:00",
            idle_timeout=300,
            max_lifetime=1800
        )
        app_with_auth.dependency_overrides[get_deployment_service] = lambda: mock_service

        # Act
        response = client.get("/playground/runtime/deployments/deploy-123/status")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "ready"

    def test_get_status_not_found(
        self,
        app_with_auth,
        client
    ):
        """배포 미존재 테스트"""
        from app.playground.exception.exceptions import DeploymentNotFoundException

        # Arrange
        mock_service = AsyncMock()
        mock_service.get_deployment_status.side_effect = DeploymentNotFoundException("deploy-999")
        app_with_auth.dependency_overrides[get_deployment_service] = lambda: mock_service

        # Act
        response = client.get("/playground/runtime/deployments/deploy-999/status")

        # Assert
        assert response.status_code == 404


class TestDestroyDeploymentEndpoint:
    """DELETE /playground/runtime/deployments/{id} 테스트"""

    def test_destroy_success(
        self,
        app_with_auth,
        client
    ):
        """배포 종료 성공 테스트"""
        # Arrange
        mock_service = AsyncMock()
        mock_service.destroy_deployment.return_value = DestroyResponse(
            deployment_id="deploy-123",
            status="destroyed",
            message="Runtime이 성공적으로 종료되었습니다."
        )
        app_with_auth.dependency_overrides[get_deployment_service] = lambda: mock_service

        # Act
        response = client.delete("/playground/runtime/deployments/deploy-123")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "destroyed"

    def test_destroy_not_found(
        self,
        app_with_auth,
        client
    ):
        """배포 미존재 테스트"""
        from app.playground.exception.exceptions import DeploymentNotFoundException

        # Arrange
        mock_service = AsyncMock()
        mock_service.destroy_deployment.side_effect = DeploymentNotFoundException("deploy-999")
        app_with_auth.dependency_overrides[get_deployment_service] = lambda: mock_service

        # Act
        response = client.delete("/playground/runtime/deployments/deploy-999")

        # Assert
        assert response.status_code == 404


class TestRuntimeChatEndpoint:
    """POST /playground/runtime/deployments/{id}/chat/stream 테스트"""

    def test_stream_chat_returns_sse(
        self,
        app_with_auth,
        client
    ):
        """스트리밍 채팅 SSE 응답 테스트"""
        # Arrange
        async def mock_stream():
            yield {"type": "text", "content": "Hello"}
            yield {"type": "done"}

        mock_service = MagicMock()
        mock_service.stream_runtime_chat = MagicMock(return_value=mock_stream())
        app_with_auth.dependency_overrides[get_deployment_service] = lambda: mock_service

        # Act
        response = client.post(
            "/playground/runtime/deployments/deploy-123/chat/stream",
            json={"message": "Hello"},
        )

        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
