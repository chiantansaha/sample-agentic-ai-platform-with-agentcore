"""통합 테스트 공통 Fixtures"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.agent.domain.entities.agent import Agent
from app.agent.domain.value_objects import AgentId, LLMModel, Instruction, Version, AgentStatus
from app.kb.domain.entities.kb import KB
from app.kb.domain.value_objects import KBId, VectorizationStatus
from app.team_tag.domain.entities.team_tag import TeamTag
from app.team_tag.domain.value_objects import TeamTagId


@pytest.fixture
def mock_agent():
    """Mock Agent Entity"""
    return Agent(
        id=AgentId("agent-test-id"),
        name="Test Agent",
        description="Test Description",
        llm_model=LLMModel("claude-3-5-sonnet-20241022"),
        instruction=Instruction("Test instruction"),
        version=Version("1.0.0"),
        status=AgentStatus.DRAFT,
        team_tags=["booking"],
        knowledge_base_ids=["kb-test-id"],
        created_at=datetime.utcnow()
    )


@pytest.fixture
def mock_kb():
    """Mock KB Entity"""
    return KB(
        id=KBId("kb-test-id"),
        name="Test KB",
        description="Test KB Description",
        vectorization_status=VectorizationStatus.COMPLETED,
        team_tags=["booking"],
        created_at=datetime.utcnow()
    )


@pytest.fixture
def mock_team_tag():
    """Mock TeamTag Entity"""
    return TeamTag(
        id=TeamTagId("tag-test-id"),
        name="booking",
        description="항공권 예약 관련 리소스",
        usage_count=0,
        created_at=datetime.utcnow()
    )


@pytest.fixture
def mock_agent_repository():
    """Mock Agent Repository"""
    return AsyncMock()


@pytest.fixture
def mock_kb_repository():
    """Mock KB Repository"""
    return AsyncMock()


@pytest.fixture
def mock_team_tag_repository():
    """Mock TeamTag Repository"""
    return AsyncMock()
