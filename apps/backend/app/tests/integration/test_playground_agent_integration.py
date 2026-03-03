"""Playground-Agent 통합 테스트"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.playground.infrastructure.clients.strands_agent_client import (
    StrandsAgentClient,
    AgentSpec,
)


@pytest.fixture
def agent_spec():
    """Agent 스펙 Fixture"""
    return AgentSpec(
        model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        model_name="Claude 3 Sonnet",
        provider="bedrock",
        system_prompt="You are a helpful assistant.",
        temperature=0.7,
        max_tokens=2000,
        mcps=['{"command": "uvx", "args": ["mcp-server-fetch"]}'],
        knowledge_bases=["bedrock-kb-123"],
    )


@pytest.fixture
def mock_bedrock_model():
    """Bedrock Model Mock"""
    mock = MagicMock()
    mock.model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
    return mock


@pytest.fixture
def mock_mcp_client():
    """MCP Client Mock"""
    mock = AsyncMock()
    mock.call_tool = AsyncMock(return_value={"result": "Mock tool result"})
    return mock


@pytest.mark.asyncio
async def test_create_agent_from_spec(agent_spec, mock_bedrock_model):
    """Agent 스펙 기반 Strands Agent 생성"""
    # Given
    client = StrandsAgentClient()
    agent_id = "agent-test-id"
    version = "1.0.0"

    # When
    with patch("app.playground.infrastructure.clients.strands_agent_client.BedrockModel", return_value=mock_bedrock_model):
        with patch("app.playground.infrastructure.clients.strands_agent_client.Agent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent_class.return_value = mock_agent

            agent = client.get_or_create_agent(agent_id, version, agent_spec)

            # Then
            assert agent is not None
            assert agent == mock_agent
            mock_agent_class.assert_called_once()


@pytest.mark.asyncio
async def test_agent_with_mcps(agent_spec):
    """MCP 연동 Agent 생성"""
    # Given
    client = StrandsAgentClient()
    agent_id = "agent-with-mcp"
    version = "1.0.0"

    # When
    with patch("app.playground.infrastructure.clients.strands_agent_client.BedrockModel"):
        with patch("app.playground.infrastructure.clients.strands_agent_client.Agent") as mock_agent_class:
            with patch("app.playground.infrastructure.clients.strands_agent_client.stdio_client") as mock_stdio:
                mock_stdio.return_value.__aenter__ = AsyncMock()
                mock_stdio.return_value.__aexit__ = AsyncMock()

                agent = client.get_or_create_agent(agent_id, version, agent_spec)

                # Then
                assert agent is not None
                assert len(agent_spec.mcps) == 1


@pytest.mark.asyncio
async def test_agent_with_kbs(agent_spec):
    """KB 연동 Agent 생성"""
    # Given
    client = StrandsAgentClient()
    agent_id = "agent-with-kb"
    version = "1.0.0"

    # When
    with patch("app.playground.infrastructure.clients.strands_agent_client.BedrockModel"):
        with patch("app.playground.infrastructure.clients.strands_agent_client.Agent") as mock_agent_class:
            with patch("app.playground.infrastructure.clients.strands_agent_client.retrieve") as mock_retrieve:
                mock_retrieve.return_value = MagicMock()

                agent = client.get_or_create_agent(agent_id, version, agent_spec)

                # Then
                assert agent is not None
                assert len(agent_spec.knowledge_bases) == 1


@pytest.mark.asyncio
async def test_agent_caching():
    """Agent 인스턴스 캐싱 테스트"""
    # Given
    client = StrandsAgentClient()
    agent_id = "agent-cached"
    version = "1.0.0"
    spec = AgentSpec(
        model_id="test-model",
        model_name="Test Model",
        provider="bedrock",
        system_prompt="Test prompt",
    )

    # When
    with patch("app.playground.infrastructure.clients.strands_agent_client.BedrockModel"):
        with patch("app.playground.infrastructure.clients.strands_agent_client.Agent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent_class.return_value = mock_agent

            agent1 = client.get_or_create_agent(agent_id, version, spec)
            agent2 = client.get_or_create_agent(agent_id, version, spec)

            # Then
            assert agent1 == agent2
            mock_agent_class.assert_called_once()  # 한 번만 생성


@pytest.mark.asyncio
async def test_invoke_agent(agent_spec):
    """Agent 호출 테스트 (비스트리밍)"""
    # Given
    client = StrandsAgentClient()
    agent_id = "agent-invoke"
    version = "1.0.0"
    message = "Hello, Agent!"

    # When
    with patch("app.playground.infrastructure.clients.strands_agent_client.BedrockModel"):
        with patch("app.playground.infrastructure.clients.strands_agent_client.Agent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.invoke = AsyncMock(return_value={"content": "Hello, User!"})
            mock_agent_class.return_value = mock_agent

            result = await client.invoke_agent(agent_id, version, agent_spec, message)

            # Then
            assert result is not None
            assert result["content"] == "Hello, User!"
            mock_agent.invoke.assert_called_once()


@pytest.mark.asyncio
async def test_agent_with_multiple_mcps():
    """여러 MCP를 가진 Agent 생성"""
    # Given
    client = StrandsAgentClient()
    agent_id = "agent-multi-mcp"
    version = "1.0.0"
    spec = AgentSpec(
        model_id="test-model",
        model_name="Test Model",
        provider="bedrock",
        system_prompt="Test prompt",
        mcps=[
            '{"command": "uvx", "args": ["mcp-server-fetch"]}',
            '{"command": "uvx", "args": ["mcp-server-time"]}',
        ],
    )

    # When
    with patch("app.playground.infrastructure.clients.strands_agent_client.BedrockModel"):
        with patch("app.playground.infrastructure.clients.strands_agent_client.Agent") as mock_agent_class:
            with patch("app.playground.infrastructure.clients.strands_agent_client.stdio_client"):
                mock_agent = MagicMock()
                mock_agent_class.return_value = mock_agent

                agent = client.get_or_create_agent(agent_id, version, spec)

                # Then
                assert agent is not None
                assert len(spec.mcps) == 2


@pytest.mark.asyncio
async def test_agent_with_multiple_kbs():
    """여러 KB를 가진 Agent 생성"""
    # Given
    client = StrandsAgentClient()
    agent_id = "agent-multi-kb"
    version = "1.0.0"
    spec = AgentSpec(
        model_id="test-model",
        model_name="Test Model",
        provider="bedrock",
        system_prompt="Test prompt",
        knowledge_bases=["kb-1", "kb-2", "kb-3"],
    )

    # When
    with patch("app.playground.infrastructure.clients.strands_agent_client.BedrockModel"):
        with patch("app.playground.infrastructure.clients.strands_agent_client.Agent") as mock_agent_class:
            with patch("app.playground.infrastructure.clients.strands_agent_client.retrieve"):
                mock_agent = MagicMock()
                mock_agent_class.return_value = mock_agent

                agent = client.get_or_create_agent(agent_id, version, spec)

                # Then
                assert agent is not None
                assert len(spec.knowledge_bases) == 3
