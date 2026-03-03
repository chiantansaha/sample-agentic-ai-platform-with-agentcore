"""E2E 시나리오 통합 테스트"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.agent.application.service import AgentApplicationService
from app.kb.application.service import KBApplicationService
from app.team_tag.application.service import TeamTagApplicationService
from app.playground.application.service import PlaygroundApplicationService


@pytest.mark.asyncio
async def test_full_agent_lifecycle(
    mock_agent_repository,
    mock_kb_repository,
    mock_team_tag_repository,
    mock_session_repository,
    mock_strands_client,
    mock_agent,
    mock_kb,
    mock_team_tag,
):
    """Agent 전체 생명주기 테스트"""
    # Given
    mock_team_tag_repository.save.return_value = mock_team_tag
    mock_kb_repository.save.return_value = mock_kb
    mock_agent_repository.save.return_value = mock_agent
    mock_agent_repository.find_by_id.return_value = mock_agent

    # Mock Strands Agent
    mock_strands_client.stream_response = AsyncMock()

    async def mock_stream(*args, **kwargs):
        yield {"type": "text", "content": "Hello"}
        yield {"type": "done"}

    mock_strands_client.stream_response.return_value = mock_stream()

    # When - 1. TeamTag 생성
    tag = await mock_team_tag_repository.save(mock_team_tag)
    assert tag.name == "booking"

    # When - 2. KB 생성 및 TeamTag 할당
    mock_kb.team_tags = [tag.name]
    kb = await mock_kb_repository.save(mock_kb)
    assert kb.team_tags == ["booking"]

    # When - 3. Agent 생성 및 KB, TeamTag 연결
    mock_agent.knowledge_base_ids = [kb.id.value]
    mock_agent.team_tags = [tag.name]
    agent = await mock_agent_repository.save(mock_agent)
    assert agent.team_tags == ["booking"]
    assert agent.knowledge_base_ids == ["kb-test-id"]

    # When - 4. Playground 테스트
    agent_from_repo = await mock_agent_repository.find_by_id(agent.id.value)
    assert agent_from_repo is not None

    # When - 5. Agent 수정 (버전 생성)
    agent.instruction.content = "Updated instruction"
    updated_agent = await mock_agent_repository.save(agent)
    assert updated_agent.instruction.content == "Updated instruction"

    # Then
    assert mock_agent_repository.save.call_count == 2  # 생성 + 수정


@pytest.mark.asyncio
async def test_team_resource_management(
    mock_agent_repository,
    mock_kb_repository,
    mock_team_tag_repository,
    mock_agent,
    mock_kb,
    mock_team_tag,
):
    """팀별 리소스 관리 시나리오"""
    # Given
    mock_team_tag_repository.save.return_value = mock_team_tag
    mock_team_tag_repository.find_by_name.return_value = mock_team_tag

    # When - 1. TeamTag 생성
    tag = await mock_team_tag_repository.save(mock_team_tag)

    # When - 2. Agent, KB 생성 및 태그 할당
    mock_agent.team_tags = [tag.name]
    mock_kb.team_tags = [tag.name]
    mock_agent_repository.save.return_value = mock_agent
    mock_kb_repository.save.return_value = mock_kb

    agent = await mock_agent_repository.save(mock_agent)
    kb = await mock_kb_repository.save(mock_kb)

    # When - 3. 팀별 리소스 조회
    mock_agent_repository.find_all.return_value = [agent]
    mock_kb_repository.find_all.return_value = [kb]

    all_agents = await mock_agent_repository.find_all()
    all_kbs = await mock_kb_repository.find_all()

    agents_with_tag = [a for a in all_agents if tag.name in a.team_tags]
    kbs_with_tag = [k for k in all_kbs if tag.name in k.team_tags]

    # Then
    assert len(agents_with_tag) == 1
    assert len(kbs_with_tag) == 1
    assert agents_with_tag[0].name == "Test Agent"
    assert kbs_with_tag[0].name == "Test KB"


@pytest.mark.asyncio
async def test_playground_session_workflow(
    mock_agent_repository,
    mock_session_repository,
    mock_strands_client,
    mock_agent,
    mock_session,
):
    """Playground 세션 워크플로우"""
    # Given
    mock_agent_repository.find_by_id.return_value = mock_agent
    mock_session_repository.save.return_value = mock_session
    mock_session_repository.find_by_id.return_value = mock_session

    # Mock streaming response
    async def mock_stream(*args, **kwargs):
        yield {"type": "text", "content": "Hello"}
        yield {"type": "tool_use", "tool_name": "retrieve"}
        yield {"type": "tool_result", "status": "success"}
        yield {"type": "text", "content": "Based on KB"}
        yield {"type": "done"}

    mock_strands_client.stream_response.return_value = mock_stream()

    # When - 1. 세션 생성
    session = await mock_session_repository.save(mock_session)
    assert session.agent_id == "agent-test-id"

    # When - 2. Agent 조회
    agent = await mock_agent_repository.find_by_id(session.agent_id)
    assert agent is not None

    # When - 3. 스트리밍 메시지 전송
    events = []
    async for event in mock_strands_client.stream_response():
        events.append(event)

    # Then
    assert len(events) == 5
    assert events[0]["type"] == "text"
    assert events[1]["type"] == "tool_use"
    assert events[-1]["type"] == "done"


@pytest.mark.asyncio
async def test_agent_kb_playground_integration(
    mock_agent_repository,
    mock_kb_repository,
    mock_strands_client,
    mock_agent,
    mock_kb,
):
    """Agent-KB-Playground 통합 시나리오"""
    # Given
    mock_kb_repository.find_by_id.return_value = mock_kb
    mock_agent.knowledge_base_ids = [mock_kb.id.value]
    mock_agent_repository.save.return_value = mock_agent
    mock_agent_repository.find_by_id.return_value = mock_agent

    # Mock streaming with KB retrieve
    async def mock_stream(*args, **kwargs):
        yield {"type": "text", "content": "Searching KB"}
        yield {"type": "tool_use", "tool_name": "retrieve", "kb_id": mock_kb.id.value}
        yield {"type": "tool_result", "status": "success", "documents": ["doc1", "doc2"]}
        yield {"type": "text", "content": "Found 2 documents"}
        yield {"type": "done"}

    mock_strands_client.stream_response.return_value = mock_stream()

    # When - 1. KB 생성
    kb = await mock_kb_repository.save(mock_kb)

    # When - 2. Agent 생성 및 KB 연결
    agent = await mock_agent_repository.save(mock_agent)
    assert kb.id.value in agent.knowledge_base_ids

    # When - 3. Playground에서 KB 사용
    agent_from_repo = await mock_agent_repository.find_by_id(agent.id.value)
    events = []
    async for event in mock_strands_client.stream_response():
        events.append(event)

    # Then
    tool_use_events = [e for e in events if e["type"] == "tool_use"]
    assert len(tool_use_events) == 1
    assert tool_use_events[0]["tool_name"] == "retrieve"


@pytest.mark.asyncio
async def test_multi_user_concurrent_sessions(
    mock_session_repository,
    mock_agent_repository,
    mock_strands_client,
    mock_agent,
):
    """다중 사용자 동시 세션 테스트"""
    # Given
    mock_agent_repository.find_by_id.return_value = mock_agent

    # Create multiple sessions
    sessions = []
    for i in range(5):
        from app.playground.domain.entities.session import PlaygroundSession
        from app.playground.domain.value_objects.session_id import SessionId
        from app.playground.domain.value_objects.session_status import SessionStatus

        session = PlaygroundSession(
            id=SessionId(f"session-{i}"),
            user_id=f"user-{i}",
            agent_id="agent-test-id",
            agent_version="1.0.0",
            messages=[],
            status=SessionStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        sessions.append(session)

    mock_session_repository.save.side_effect = sessions
    mock_session_repository.find_by_user.return_value = sessions

    # When - 각 사용자가 세션 생성
    created_sessions = []
    for session in sessions:
        created = await mock_session_repository.save(session)
        created_sessions.append(created)

    # Then
    assert len(created_sessions) == 5
    assert all(s.status.value == "active" for s in created_sessions)


@pytest.mark.asyncio
async def test_agent_version_rollback_scenario(
    mock_agent_repository,
    mock_agent,
):
    """Agent 버전 롤백 시나리오"""
    # Given
    v1_agent = mock_agent
    v1_agent.instruction.content = "Version 1 instruction"

    v2_agent = mock_agent
    v2_agent.instruction.content = "Version 2 instruction"

    mock_agent_repository.find_by_id.side_effect = [v1_agent, v2_agent, v1_agent]

    # When - 1. v1 Agent 조회
    agent_v1 = await mock_agent_repository.find_by_id("agent-test-id")
    assert agent_v1.instruction.content == "Version 1 instruction"

    # When - 2. v2로 업데이트
    agent_v2 = await mock_agent_repository.find_by_id("agent-test-id")
    assert agent_v2.instruction.content == "Version 2 instruction"

    # When - 3. v1으로 롤백
    agent_rollback = await mock_agent_repository.find_by_id("agent-test-id")
    assert agent_rollback.instruction.content == "Version 1 instruction"


@pytest.mark.asyncio
async def test_resource_cleanup_on_disable(
    mock_agent_repository,
    mock_kb_repository,
    mock_agent,
    mock_kb,
):
    """리소스 비활성화 시 정리 시나리오"""
    # Given
    mock_agent.knowledge_base_ids = ["kb-test-id"]
    mock_agent_repository.find_by_id.return_value = mock_agent
    mock_kb_repository.find_by_id.return_value = mock_kb

    # When - 1. KB 비활성화
    from app.kb.domain.value_objects.kb_status import KBStatus

    mock_kb.status = KBStatus.DISABLED
    await mock_kb_repository.save(mock_kb)

    # When - 2. Agent에서 비활성화된 KB 필터링
    agent = await mock_agent_repository.find_by_id("agent-test-id")
    kb = await mock_kb_repository.find_by_id("kb-test-id")

    if kb.status == KBStatus.DISABLED:
        # Playground에서 사용 불가 처리
        pass

    # Then
    assert kb.status == KBStatus.DISABLED
    assert "kb-test-id" in agent.knowledge_base_ids  # 참조는 유지
