"""Playground Application Service Integration Tests"""
import pytest
from unittest.mock import AsyncMock
from datetime import datetime

from app.playground.application.service import PlaygroundApplicationService
from app.playground.domain.entities.session import PlaygroundSession
from app.playground.domain.value_objects import SessionId, SessionStatus
from app.playground.exception.exceptions import SessionNotFoundException


@pytest.fixture
def mock_session_repository():
    """Mock Session Repository"""
    return AsyncMock()


@pytest.fixture
def mock_strands_client():
    """Mock Strands Client"""
    return AsyncMock()


@pytest.fixture
def service(mock_session_repository, mock_strands_client):
    """Playground Application Service"""
    return PlaygroundApplicationService(
        mock_session_repository,
        mock_strands_client
    )


@pytest.mark.asyncio
async def test_create_session(service, mock_session_repository):
    """세션 생성 테스트"""
    mock_session = PlaygroundSession(
        id=SessionId("test-session-id"),
        user_id="user-123",
        agent_id="agent-456",
        agent_version="1.0.0"
    )
    mock_session_repository.save.return_value = mock_session
    
    result = await service.create_session("user-123", "agent-456", "1.0.0")
    
    assert result.user_id == "user-123"
    assert result.agent_id == "agent-456"
    assert result.status == "active"


@pytest.mark.asyncio
async def test_send_message(service, mock_session_repository, mock_strands_client):
    """메시지 전송 테스트"""
    mock_session = PlaygroundSession(
        id=SessionId("test-session-id"),
        user_id="user-123",
        agent_id="agent-456",
        agent_version="1.0.0"
    )
    mock_session_repository.find_by_id.return_value = mock_session
    mock_strands_client.invoke_agent.return_value = "Agent response"
    
    result = await service.send_message("test-session-id", "Hello")
    
    assert result.session_id == "test-session-id"
    assert result.message.role == "assistant"
    assert result.message.content == "Agent response"


@pytest.mark.asyncio
async def test_get_session_not_found(service, mock_session_repository):
    """세션 조회 실패 테스트"""
    mock_session_repository.find_by_id.return_value = None
    
    with pytest.raises(SessionNotFoundException):
        await service.get_session("non-existent-id")
