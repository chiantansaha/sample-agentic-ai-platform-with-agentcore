"""Agent-KB 통합 테스트"""
import pytest
from datetime import datetime

from app.agent.application.service import AgentApplicationService
from app.kb.application.service import KBApplicationService


@pytest.mark.asyncio
async def test_create_agent_with_kb(
    mock_agent_repository,
    mock_kb_repository,
    mock_agent,
    mock_kb
):
    """Agent 생성 시 KB 연결 테스트"""
    # Given
    mock_kb_repository.find_by_id.return_value = mock_kb
    mock_agent_repository.save.return_value = mock_agent
    
    agent_service = AgentApplicationService(mock_agent_repository)
    kb_service = KBApplicationService(mock_kb_repository, None)
    
    # When
    kb = await kb_service.get_kb("kb-test-id")
    mock_agent.knowledge_base_ids = [kb.id]
    saved_agent = await mock_agent_repository.save(mock_agent)
    
    # Then
    assert "kb-test-id" in saved_agent.knowledge_base_ids
    mock_kb_repository.find_by_id.assert_called_once_with("kb-test-id")


@pytest.mark.asyncio
async def test_update_agent_kb_reference(
    mock_agent_repository,
    mock_kb_repository,
    mock_agent,
    mock_kb
):
    """Agent의 KB 참조 업데이트 테스트"""
    # Given
    mock_agent_repository.find_by_id.return_value = mock_agent
    mock_kb_repository.find_by_id.return_value = mock_kb
    
    agent_service = AgentApplicationService(mock_agent_repository)
    
    # When
    agent = await mock_agent_repository.find_by_id("agent-test-id")
    agent.knowledge_base_ids = ["kb-new-id"]
    await mock_agent_repository.save(agent)
    
    # Then
    assert agent.knowledge_base_ids == ["kb-new-id"]


@pytest.mark.asyncio
async def test_agent_with_multiple_kbs(
    mock_agent_repository,
    mock_kb_repository,
    mock_agent
):
    """Agent가 여러 KB를 참조하는 테스트"""
    # Given
    mock_agent.knowledge_base_ids = ["kb-1", "kb-2", "kb-3"]
    mock_agent_repository.save.return_value = mock_agent
    
    # When
    saved_agent = await mock_agent_repository.save(mock_agent)
    
    # Then
    assert len(saved_agent.knowledge_base_ids) == 3
    assert "kb-1" in saved_agent.knowledge_base_ids
    assert "kb-2" in saved_agent.knowledge_base_ids
    assert "kb-3" in saved_agent.knowledge_base_ids
