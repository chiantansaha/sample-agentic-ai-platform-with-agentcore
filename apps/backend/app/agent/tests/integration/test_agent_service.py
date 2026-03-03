"""Agent Application Service 통합 테스트"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from ...application.service import AgentApplicationService
from ...domain.entities import Agent
from ...domain.value_objects import AgentId, LLMModel, Instruction, AgentStatus
from ...dto.request import CreateAgentRequest, UpdateAgentRequest
from ...exception.exceptions import AgentNotFoundException


@pytest.fixture
def mock_agent_repository():
    """Mock Agent Repository"""
    return AsyncMock()


@pytest.fixture
def mock_version_repository():
    """Mock Version Repository"""
    return AsyncMock()


@pytest.fixture
def agent_service(mock_agent_repository, mock_version_repository):
    """Agent Service 인스턴스"""
    return AgentApplicationService(mock_agent_repository, mock_version_repository)


@pytest.mark.asyncio
async def test_create_agent(agent_service, mock_agent_repository):
    """Agent 생성 테스트"""
    request = CreateAgentRequest(
        name="Test Agent",
        description="Test Description",
        llm_model_id="claude-3",
        llm_model_name="Claude 3",
        llm_provider="Anthropic",
        system_prompt="You are helpful",
        temperature=0.7,
        max_tokens=2000
    )
    
    # Mock repository save
    mock_agent_repository.save.return_value = Agent(
        id=AgentId.generate(),
        name=request.name,
        description=request.description,
        llm_model=LLMModel(request.llm_model_id, request.llm_model_name, request.llm_provider),
        instruction=Instruction(request.system_prompt, request.temperature, request.max_tokens)
    )
    
    result = await agent_service.create_agent(request, "user-123")
    
    assert result.name == "Test Agent"
    assert mock_agent_repository.save.called


@pytest.mark.asyncio
async def test_get_agent_not_found(agent_service, mock_agent_repository):
    """Agent 조회 실패 테스트"""
    mock_agent_repository.find_by_id.return_value = None
    
    with pytest.raises(AgentNotFoundException):
        await agent_service.get_agent("non-existent-id")


@pytest.mark.asyncio
async def test_update_agent(agent_service, mock_agent_repository):
    """Agent 수정 테스트"""
    agent_id = "test-agent-id"
    
    # Mock existing agent
    existing_agent = Agent(
        id=AgentId(agent_id),
        name="Old Name",
        description="Old Description",
        llm_model=LLMModel("claude-3", "Claude 3", "Anthropic"),
        instruction=Instruction("Old prompt")
    )
    mock_agent_repository.find_by_id.return_value = existing_agent
    mock_agent_repository.save.return_value = existing_agent
    
    request = UpdateAgentRequest(
        name="New Name",
        description="New Description",
        llm_model_id="gpt-4",
        llm_model_name="GPT-4",
        llm_provider="OpenAI",
        system_prompt="New prompt",
        temperature=0.8,
        max_tokens=3000,
        knowledge_bases=[],
        mcps=[],
        team_tags=[]
    )
    
    result = await agent_service.update_agent(agent_id, request, "user-123")
    
    assert result.name == "New Name"
    assert mock_agent_repository.save.called


@pytest.mark.asyncio
async def test_change_agent_status(agent_service, mock_agent_repository):
    """Agent 상태 변경 테스트"""
    agent_id = "test-agent-id"
    
    agent = Agent(
        id=AgentId(agent_id),
        name="Test Agent",
        description="Test",
        llm_model=LLMModel("claude-3", "Claude 3", "Anthropic"),
        instruction=Instruction("You are helpful")
    )
    mock_agent_repository.find_by_id.return_value = agent
    mock_agent_repository.save.return_value = agent
    
    result = await agent_service.change_agent_status(agent_id, False)
    
    assert result.status == "disabled"
    assert mock_agent_repository.save.called
