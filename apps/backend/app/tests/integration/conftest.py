"""통합 테스트용 Fixtures"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.agent.domain.entities.agent import Agent
from app.agent.domain.value_objects.agent_id import AgentId
from app.agent.domain.value_objects.llm_model import LLMModel
from app.agent.domain.value_objects.instruction import Instruction
from app.agent.domain.value_objects.agent_status import AgentStatus

from app.kb.domain.entities.knowledge_base import KnowledgeBase
from app.kb.domain.value_objects.kb_id import KBId
from app.kb.domain.value_objects.kb_status import KBStatus

from app.team_tag.domain.entities.team_tag import TeamTag
from app.team_tag.domain.value_objects.team_tag_id import TeamTagId

from app.playground.domain.entities.session import PlaygroundSession
from app.playground.domain.value_objects.session_id import SessionId
from app.playground.domain.value_objects.session_status import SessionStatus


# ==================== Repository Mocks ====================

@pytest.fixture
def mock_agent_repository():
    """Agent Repository Mock"""
    mock = AsyncMock()
    mock.save = AsyncMock()
    mock.find_by_id = AsyncMock()
    mock.find_all = AsyncMock()
    mock.find_enabled_agents = AsyncMock()
    return mock


@pytest.fixture
def mock_kb_repository():
    """KB Repository Mock"""
    mock = AsyncMock()
    mock.save = AsyncMock()
    mock.find_by_id = AsyncMock()
    mock.find_all = AsyncMock()
    mock.find_enabled_kbs = AsyncMock()
    return mock


@pytest.fixture
def mock_team_tag_repository():
    """TeamTag Repository Mock"""
    mock = AsyncMock()
    mock.save = AsyncMock()
    mock.find_by_id = AsyncMock()
    mock.find_all = AsyncMock()
    mock.find_by_name = AsyncMock()
    return mock


@pytest.fixture
def mock_session_repository():
    """Session Repository Mock"""
    mock = AsyncMock()
    mock.save = AsyncMock()
    mock.find_by_id = AsyncMock()
    mock.find_by_user = AsyncMock()
    return mock


# ==================== Entity Fixtures ====================

@pytest.fixture
def mock_agent():
    """Agent Entity Fixture"""
    agent = Agent(
        id=AgentId("agent-test-id"),
        name="Test Agent",
        description="Test Agent Description",
        llm_model=LLMModel(
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            name="Claude 3 Sonnet",
            provider="bedrock",
            temperature=0.7,
            max_tokens=2000,
        ),
        instruction=Instruction(
            content="You are a helpful assistant.",
            temperature=0.7,
            max_tokens=2000,
        ),
        knowledge_base_ids=["kb-test-id"],
        mcp_ids=["mcp-test-id"],
        status=AgentStatus.ENABLED,
        team_tags=["booking"],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        created_by="user-test-id",
        updated_by="user-test-id",
    )
    return agent


@pytest.fixture
def mock_kb():
    """KB Entity Fixture"""
    kb = KnowledgeBase(
        id=KBId("kb-test-id"),
        name="Test KB",
        description="Test KB Description",
        bedrock_kb_id="bedrock-kb-123",
        status=KBStatus.ENABLED,
        team_tags=["booking"],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        created_by="user-test-id",
        updated_by="user-test-id",
    )
    return kb


@pytest.fixture
def mock_team_tag():
    """TeamTag Entity Fixture"""
    tag = TeamTag(
        id=TeamTagId("tag-test-id"),
        name="booking",
        description="Booking team resources",
        keis_id="KEIS-001",
        usage_count=10,
        synced_at=datetime.now(),
        created_at=datetime.now(),
    )
    return tag


@pytest.fixture
def mock_session():
    """PlaygroundSession Entity Fixture"""
    session = PlaygroundSession(
        id=SessionId("session-test-id"),
        user_id="user-test-id",
        agent_id="agent-test-id",
        agent_version="1.0.0",
        messages=[],
        status=SessionStatus.ACTIVE,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    return session


# ==================== External Service Mocks ====================

@pytest.fixture
def mock_strands_client():
    """Strands Agent Client Mock"""
    mock = MagicMock()
    mock.get_or_create_agent = MagicMock()
    mock.invoke_agent = AsyncMock()
    mock.stream_response = AsyncMock()
    return mock


@pytest.fixture
def mock_bedrock_model():
    """Bedrock Model Mock"""
    mock = MagicMock()
    mock.model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
    mock.invoke = AsyncMock(return_value={"content": "Mock response"})
    return mock


@pytest.fixture
def mock_mcp_client():
    """MCP Client Mock"""
    mock = AsyncMock()
    mock.call_tool = AsyncMock(return_value={"result": "Mock tool result"})
    return mock


@pytest.fixture
def mock_kb_retrieve_tool():
    """KB Retrieve Tool Mock"""
    mock = MagicMock()
    mock.name = "retrieve"
    mock.description = "Retrieve documents from knowledge base"
    return mock


# ==================== Agent Spec Fixtures ====================

@pytest.fixture
def basic_agent_spec():
    """기본 Agent 스펙"""
    from app.playground.infrastructure.clients.strands_agent_client import AgentSpec

    return AgentSpec(
        model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        model_name="Claude 3 Sonnet",
        provider="bedrock",
        system_prompt="You are a helpful assistant.",
        temperature=0.7,
        max_tokens=2000,
    )


@pytest.fixture
def agent_spec_with_mcps():
    """MCP가 포함된 Agent 스펙"""
    from app.playground.infrastructure.clients.strands_agent_client import AgentSpec

    return AgentSpec(
        model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        model_name="Claude 3 Sonnet",
        provider="bedrock",
        system_prompt="You are a helpful assistant.",
        temperature=0.7,
        max_tokens=2000,
        mcps=['{"command": "uvx", "args": ["mcp-server-fetch"]}'],
    )


@pytest.fixture
def agent_spec_with_kbs():
    """KB가 포함된 Agent 스펙"""
    from app.playground.infrastructure.clients.strands_agent_client import AgentSpec

    return AgentSpec(
        model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        model_name="Claude 3 Sonnet",
        provider="bedrock",
        system_prompt="You are a helpful assistant.",
        temperature=0.7,
        max_tokens=2000,
        knowledge_bases=["bedrock-kb-123"],
    )
