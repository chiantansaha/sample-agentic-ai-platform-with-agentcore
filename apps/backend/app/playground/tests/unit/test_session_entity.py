"""PlaygroundSession Entity Unit Tests"""
import pytest
from datetime import datetime

from app.playground.domain.entities.session import PlaygroundSession
from app.playground.domain.value_objects import SessionId, Message, SessionStatus


def test_create_session():
    """세션 생성 테스트"""
    session = PlaygroundSession(
        id=SessionId("test-session-id"),
        user_id="user-123",
        agent_id="agent-456",
        agent_version="1.0.0"
    )
    
    assert session.id.value == "test-session-id"
    assert session.user_id == "user-123"
    assert session.agent_id == "agent-456"
    assert session.status == SessionStatus.ACTIVE
    assert len(session.messages) == 0


def test_add_message():
    """메시지 추가 테스트"""
    session = PlaygroundSession(
        id=SessionId("test-session-id"),
        user_id="user-123",
        agent_id="agent-456",
        agent_version="1.0.0"
    )
    
    message = Message(role="user", content="Hello")
    session.add_message(message)
    
    assert len(session.messages) == 1
    assert session.messages[0].role == "user"
    assert session.messages[0].content == "Hello"


def test_close_session():
    """세션 종료 테스트"""
    session = PlaygroundSession(
        id=SessionId("test-session-id"),
        user_id="user-123",
        agent_id="agent-456",
        agent_version="1.0.0"
    )
    
    session.close()
    
    assert session.status == SessionStatus.CLOSED
