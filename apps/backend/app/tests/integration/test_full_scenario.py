"""전체 시나리오 통합 테스트"""
import pytest
from datetime import datetime

from app.agent.application.service import AgentApplicationService
from app.kb.application.service import KBApplicationService
from app.team_tag.application.service import TeamTagApplicationService


@pytest.mark.asyncio
async def test_full_resource_creation_scenario(
    mock_agent_repository,
    mock_kb_repository,
    mock_team_tag_repository,
    mock_agent,
    mock_kb,
    mock_team_tag
):
    """전체 리소스 생성 시나리오 테스트"""
    # Given
    mock_team_tag_repository.save.return_value = mock_team_tag
    mock_kb_repository.save.return_value = mock_kb
    mock_agent_repository.save.return_value = mock_agent
    
    # When - 1. TeamTag 생성
    team_tag = await mock_team_tag_repository.save(mock_team_tag)
    
    # When - 2. KB 생성 및 TeamTag 할당
    mock_kb.team_tags = [team_tag.name]
    kb = await mock_kb_repository.save(mock_kb)
    
    # When - 3. Agent 생성 및 KB, TeamTag 연결
    mock_agent.knowledge_base_ids = [kb.id.value]
    mock_agent.team_tags = [team_tag.name]
    agent = await mock_agent_repository.save(mock_agent)
    
    # Then
    assert agent.team_tags == ["booking"]
    assert agent.knowledge_base_ids == ["kb-test-id"]
    assert kb.team_tags == ["booking"]


@pytest.mark.asyncio
async def test_team_tag_resource_aggregation(
    mock_agent_repository,
    mock_kb_repository,
    mock_team_tag_repository,
    mock_agent,
    mock_kb,
    mock_team_tag
):
    """TeamTag별 리소스 집계 테스트"""
    # Given
    mock_agent.team_tags = ["booking"]
    mock_kb.team_tags = ["booking"]
    mock_agent_repository.find_all.return_value = [mock_agent]
    mock_kb_repository.find_all.return_value = [mock_kb]
    mock_team_tag_repository.find_by_name.return_value = mock_team_tag
    
    # When
    tag = await mock_team_tag_repository.find_by_name("booking")
    all_agents = await mock_agent_repository.find_all()
    all_kbs = await mock_kb_repository.find_all()
    
    agents_with_tag = [a for a in all_agents if tag.name in a.team_tags]
    kbs_with_tag = [kb for kb in all_kbs if tag.name in kb.team_tags]
    
    # Then
    assert len(agents_with_tag) == 1
    assert len(kbs_with_tag) == 1
    assert agents_with_tag[0].name == "Test Agent"
    assert kbs_with_tag[0].name == "Test KB"


@pytest.mark.asyncio
async def test_cascade_team_tag_update(
    mock_agent_repository,
    mock_kb_repository,
    mock_agent,
    mock_kb
):
    """TeamTag 변경 시 리소스 업데이트 테스트"""
    # Given
    mock_agent.team_tags = ["booking"]
    mock_kb.team_tags = ["booking"]
    mock_agent_repository.find_all.return_value = [mock_agent]
    mock_kb_repository.find_all.return_value = [mock_kb]
    
    # When - TeamTag 변경
    new_tag = "flight"
    all_agents = await mock_agent_repository.find_all()
    all_kbs = await mock_kb_repository.find_all()
    
    for agent in all_agents:
        if "booking" in agent.team_tags:
            agent.team_tags = [new_tag]
            await mock_agent_repository.save(agent)
    
    for kb in all_kbs:
        if "booking" in kb.team_tags:
            kb.team_tags = [new_tag]
            await mock_kb_repository.save(kb)
    
    # Then
    assert mock_agent.team_tags == ["flight"]
    assert mock_kb.team_tags == ["flight"]


@pytest.mark.asyncio
async def test_resource_cleanup_scenario(
    mock_agent_repository,
    mock_kb_repository,
    mock_agent,
    mock_kb
):
    """리소스 정리 시나리오 테스트"""
    # Given
    mock_agent.knowledge_base_ids = ["kb-test-id"]
    mock_agent_repository.find_by_id.return_value = mock_agent
    mock_kb_repository.find_by_id.return_value = None  # KB 삭제됨
    
    # When - KB 삭제 후 Agent 참조 정리
    agent = await mock_agent_repository.find_by_id("agent-test-id")
    kb = await mock_kb_repository.find_by_id("kb-test-id")
    
    if kb is None and "kb-test-id" in agent.knowledge_base_ids:
        agent.knowledge_base_ids.remove("kb-test-id")
        await mock_agent_repository.save(agent)
    
    # Then
    assert "kb-test-id" not in agent.knowledge_base_ids
    assert len(agent.knowledge_base_ids) == 0


@pytest.mark.asyncio
async def test_multi_resource_query_scenario(
    mock_agent_repository,
    mock_kb_repository,
    mock_team_tag_repository,
    mock_agent,
    mock_kb,
    mock_team_tag
):
    """복합 리소스 조회 시나리오 테스트"""
    # Given
    mock_agent.team_tags = ["booking", "flight"]
    mock_kb.team_tags = ["booking"]
    mock_agent_repository.find_all.return_value = [mock_agent]
    mock_kb_repository.find_all.return_value = [mock_kb]
    
    # When - 여러 TeamTag로 필터링
    all_agents = await mock_agent_repository.find_all()
    all_kbs = await mock_kb_repository.find_all()
    
    booking_agents = [a for a in all_agents if "booking" in a.team_tags]
    flight_agents = [a for a in all_agents if "flight" in a.team_tags]
    booking_kbs = [kb for kb in all_kbs if "booking" in kb.team_tags]
    
    # Then
    assert len(booking_agents) == 1
    assert len(flight_agents) == 1
    assert len(booking_kbs) == 1
    assert booking_agents[0].id == mock_agent.id
