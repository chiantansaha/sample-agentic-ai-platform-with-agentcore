"""Conversation API Endpoints Tests"""
import pytest
from unittest.mock import AsyncMock

from app.playground.dto.response import (
    ConversationResponse,
    ConversationListResponse,
    DestroyResponse
)
from app.playground.presentation.controller import get_conversation_service


# Note: client, app_with_auth, mock_token_payload fixtures are provided by conftest.py


@pytest.fixture
def mock_conversation_response():
    """Mock conversation response"""
    return ConversationResponse(
        id="conv-123",
        agent_id="agent-456",
        agent_version="1.0.0",
        agent_name="Test Agent",
        title="테스트 대화",
        message_count=5,
        last_message_preview="안녕하세요",
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T01:00:00"
    )


@pytest.fixture
def mock_conversation_list_response(mock_conversation_response):
    """Mock conversation list response"""
    return ConversationListResponse(
        conversations=[mock_conversation_response],
        total=1,
        max_allowed=5
    )


class TestListConversationsEndpoint:
    """GET /playground/conversations 테스트"""

    def test_list_conversations_success(
        self,
        app_with_auth,
        client,
        mock_conversation_list_response
    ):
        """대화 목록 조회 성공 테스트"""
        # Arrange
        mock_service = AsyncMock()
        mock_service.list_conversations.return_value = mock_conversation_list_response
        app_with_auth.dependency_overrides[get_conversation_service] = lambda: mock_service

        # Act
        response = client.get(
            "/playground/conversations",
            params={"agent_id": "agent-456", "version": "1.0.0"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == 200
        assert len(data["data"]["conversations"]) == 1
        assert data["data"]["total"] == 1
        assert data["data"]["max_allowed"] == 5

    def test_list_conversations_empty(
        self,
        app_with_auth,
        client
    ):
        """대화 목록 비어있음 테스트"""
        # Arrange
        mock_service = AsyncMock()
        mock_service.list_conversations.return_value = ConversationListResponse(
            conversations=[],
            total=0,
            max_allowed=5
        )
        app_with_auth.dependency_overrides[get_conversation_service] = lambda: mock_service

        # Act
        response = client.get(
            "/playground/conversations",
            params={"agent_id": "agent-456", "version": "1.0.0"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["conversations"]) == 0
        assert data["data"]["total"] == 0


class TestCreateConversationEndpoint:
    """POST /playground/conversations 테스트"""

    def test_create_conversation_success(
        self,
        app_with_auth,
        client,
        mock_conversation_response
    ):
        """대화 생성 성공 테스트"""
        # Arrange
        mock_service = AsyncMock()
        mock_service.create_conversation.return_value = mock_conversation_response
        app_with_auth.dependency_overrides[get_conversation_service] = lambda: mock_service

        # Act
        response = client.post(
            "/playground/conversations",
            json={
                "agent_id": "agent-456",
                "version": "1.0.0",
                "first_message": "안녕하세요, 도움이 필요합니다."
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["id"] == "conv-123"
        assert data["data"]["title"] == "테스트 대화"

    def test_create_conversation_agent_not_found(
        self,
        app_with_auth,
        client
    ):
        """Agent 미존재 테스트"""
        from app.playground.exception.exceptions import AgentNotFoundException

        # Arrange
        mock_service = AsyncMock()
        mock_service.create_conversation.side_effect = AgentNotFoundException("agent-999")
        app_with_auth.dependency_overrides[get_conversation_service] = lambda: mock_service

        # Act
        response = client.post(
            "/playground/conversations",
            json={
                "agent_id": "agent-999",
                "version": "1.0.0",
                "first_message": "Hello"
            },
        )

        # Assert
        assert response.status_code == 404


class TestDeleteConversationEndpoint:
    """DELETE /playground/conversations/{id} 테스트"""

    def test_delete_conversation_success(
        self,
        app_with_auth,
        client
    ):
        """대화 삭제 성공 테스트"""
        # Arrange
        mock_service = AsyncMock()
        mock_service.delete_conversation.return_value = DestroyResponse(
            conversation_id="conv-123",
            status="deleted",
            message="대화가 삭제되었습니다."
        )
        app_with_auth.dependency_overrides[get_conversation_service] = lambda: mock_service

        # Act
        response = client.delete("/playground/conversations/conv-123")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "deleted"

    def test_delete_conversation_not_found(
        self,
        app_with_auth,
        client
    ):
        """대화 미존재 테스트"""
        from app.playground.exception.exceptions import ConversationNotFoundException

        # Arrange
        mock_service = AsyncMock()
        mock_service.delete_conversation.side_effect = ConversationNotFoundException("conv-999")
        app_with_auth.dependency_overrides[get_conversation_service] = lambda: mock_service

        # Act
        response = client.delete("/playground/conversations/conv-999")

        # Assert
        assert response.status_code == 404

    def test_delete_conversation_wrong_user(
        self,
        app_with_auth,
        client
    ):
        """다른 사용자 대화 삭제 시도 테스트"""
        from app.playground.exception.exceptions import ConversationNotFoundException

        # Arrange - 다른 사용자의 대화로 인해 NotFound 반환
        mock_service = AsyncMock()
        mock_service.delete_conversation.side_effect = ConversationNotFoundException("conv-other-user")
        app_with_auth.dependency_overrides[get_conversation_service] = lambda: mock_service

        # Act
        response = client.delete("/playground/conversations/conv-other-user")

        # Assert
        assert response.status_code == 404
