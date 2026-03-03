"""Deployment Service Tests"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.playground.application.service import DeploymentService
from app.playground.domain.entities.deployment import Deployment
from app.playground.domain.value_objects import DeploymentId, DeploymentStatus
from app.playground.exception.exceptions import (
    AgentNotFoundException,
    DeploymentNotFoundException,
    DeploymentAlreadyExistsException
)


@pytest.fixture
def mock_deployment_repository():
    return AsyncMock()


@pytest.fixture
def mock_conversation_repository():
    return AsyncMock()


@pytest.fixture
def mock_agent_repository():
    return AsyncMock()


@pytest.fixture
def mock_agentcore_client():
    return AsyncMock()


@pytest.fixture
def mock_code_generator():
    return MagicMock()


@pytest.fixture
def deployment_service(
    mock_deployment_repository,
    mock_conversation_repository,
    mock_agent_repository,
    mock_agentcore_client,
    mock_code_generator
):
    return DeploymentService(
        deployment_repository=mock_deployment_repository,
        conversation_repository=mock_conversation_repository,
        agent_repository=mock_agent_repository,
        agentcore_client=mock_agentcore_client,
        code_generator=mock_code_generator
    )


class TestDeployAgent:
    """deploy_agent 테스트"""

    @pytest.mark.asyncio
    async def test_deploy_agent_success(
        self,
        deployment_service,
        mock_agent_repository,
        mock_deployment_repository,
        mock_agentcore_client,
        mock_code_generator
    ):
        """Agent 배포 성공 테스트"""
        # Arrange
        user_id = "user-123"
        agent_id = "agent-456"
        version = "1.0.0"

        mock_agent = MagicMock()
        mock_agent.name = "Test Agent"
        mock_agent.llm_model.model_id = "anthropic.claude-3-sonnet"
        mock_agent.instruction.system_prompt = "You are helpful"
        mock_agent.instruction.temperature = 0.7
        mock_agent.instruction.max_tokens = 2000
        mock_agent.knowledge_bases = []

        mock_agent_repository.find_by_id.return_value = mock_agent
        mock_deployment_repository.find_by_user_agent_version.return_value = None
        mock_deployment_repository.save.return_value = MagicMock()

        mock_code_generator.generate_s3_prefix.return_value = "agents/user-123/agent-456/1.0.0/deploy-789"
        mock_code_generator.generate.return_value = {
            "agent.py": "# Agent code",
            "requirements.txt": "strands-agents"
        }

        mock_agentcore_client.upload_code.return_value = "s3://bucket/path"
        mock_agentcore_client.create_runtime.return_value = {"runtime_id": "runtime-001"}
        mock_agentcore_client.wait_for_ready.return_value = {
            "runtime_arn": "arn:aws:agentcore:runtime",
            "endpoint_url": "https://runtime.endpoint"
        }

        # Act
        result = await deployment_service.deploy_agent(user_id, agent_id, version)

        # Assert
        assert result is not None
        mock_agent_repository.find_by_id.assert_called_once_with(agent_id)
        mock_deployment_repository.save.assert_called()

    @pytest.mark.asyncio
    async def test_deploy_agent_not_found(
        self,
        deployment_service,
        mock_agent_repository
    ):
        """Agent가 존재하지 않는 경우 테스트"""
        # Arrange
        mock_agent_repository.find_by_id.return_value = None

        # Act & Assert
        with pytest.raises(AgentNotFoundException):
            await deployment_service.deploy_agent("user-123", "nonexistent", "1.0.0")

    @pytest.mark.asyncio
    async def test_deploy_agent_already_exists(
        self,
        deployment_service,
        mock_agent_repository,
        mock_deployment_repository
    ):
        """이미 활성 배포가 존재하는 경우 테스트"""
        # Arrange
        mock_agent_repository.find_by_id.return_value = MagicMock()

        existing_deployment = MagicMock()
        existing_deployment.is_active.return_value = True
        existing_deployment.id.value = "existing-deploy-123"
        mock_deployment_repository.find_by_user_agent_version.return_value = existing_deployment

        # Act & Assert
        with pytest.raises(DeploymentAlreadyExistsException):
            await deployment_service.deploy_agent("user-123", "agent-456", "1.0.0")


class TestGetDeploymentStatus:
    """get_deployment_status 테스트"""

    @pytest.mark.asyncio
    async def test_get_deployment_status_success(
        self,
        deployment_service,
        mock_deployment_repository
    ):
        """배포 상태 조회 성공 테스트"""
        # Arrange
        deployment_id = "deploy-123"
        mock_deployment = MagicMock()
        mock_deployment.id.value = deployment_id
        mock_deployment.status.value = "ready"
        mock_deployment.runtime_arn = "arn:aws:runtime"
        mock_deployment.endpoint_url = "https://endpoint"
        mock_deployment.created_at.isoformat.return_value = "2024-01-01T00:00:00"
        mock_deployment.idle_timeout = 300
        mock_deployment.max_lifetime = 1800
        mock_deployment.expires_at = None

        mock_deployment_repository.find_by_id.return_value = mock_deployment

        # Act
        result = await deployment_service.get_deployment_status(deployment_id)

        # Assert
        assert result.deployment_id == deployment_id
        assert result.status == "ready"

    @pytest.mark.asyncio
    async def test_get_deployment_status_not_found(
        self,
        deployment_service,
        mock_deployment_repository
    ):
        """배포가 존재하지 않는 경우 테스트"""
        # Arrange
        mock_deployment_repository.find_by_id.return_value = None

        # Act & Assert
        with pytest.raises(DeploymentNotFoundException):
            await deployment_service.get_deployment_status("nonexistent")


class TestDestroyDeployment:
    """destroy_deployment 테스트"""

    @pytest.mark.asyncio
    async def test_destroy_deployment_success(
        self,
        deployment_service,
        mock_deployment_repository,
        mock_agentcore_client
    ):
        """배포 종료 성공 테스트"""
        # Arrange
        deployment_id = "deploy-123"
        mock_deployment = MagicMock()
        mock_deployment.id.value = deployment_id
        mock_deployment.runtime_id = "runtime-001"
        mock_deployment.s3_code_prefix = "s3://prefix"

        mock_deployment_repository.find_by_id.return_value = mock_deployment

        # Act
        result = await deployment_service.destroy_deployment(deployment_id)

        # Assert
        assert result.status == "destroyed"
        mock_agentcore_client.delete_runtime.assert_called_once()

    @pytest.mark.asyncio
    async def test_destroy_deployment_not_found(
        self,
        deployment_service,
        mock_deployment_repository
    ):
        """배포가 존재하지 않는 경우 테스트"""
        # Arrange
        mock_deployment_repository.find_by_id.return_value = None

        # Act & Assert
        with pytest.raises(DeploymentNotFoundException):
            await deployment_service.destroy_deployment("nonexistent")
