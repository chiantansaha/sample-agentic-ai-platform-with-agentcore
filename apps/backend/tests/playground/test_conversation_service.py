"""Conversation Service Tests"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.playground.application.service import ConversationService
from app.playground.domain.entities.conversation import Conversation
from app.playground.domain.value_objects import ConversationId, ConversationStatus
from app.playground.exception.exceptions import ConversationNotFoundException


@pytest.fixture
def mock_conversation_repository():
    return AsyncMock()


@pytest.fixture
def mock_agent_repository():
    return AsyncMock()


@pytest.fixture
def conversation_service(mock_conversation_repository, mock_agent_repository):
    return ConversationService(mock_conversation_repository, mock_agent_repository)


class TestListConversations:
    """list_conversations 테스트"""

    @pytest.mark.asyncio
    async def test_list_conversations_success(
        self,
        conversation_service,
        mock_conversation_repository,
        mock_agent_repository
    ):
        """대화 목록 조회 성공 테스트"""
        # Arrange
        user_id = "user-123"
        agent_id = "agent-456"
        version = "1.0.0"

        mock_conversations = [
            MagicMock(
                id=MagicMock(value="conv-1"),
                agent_id=agent_id,
                agent_version=version,
                title="대화 1",
                message_count=5,
                last_message_preview="안녕하세요",
                created_at=MagicMock(isoformat=lambda: "2024-01-01T00:00:00"),
                updated_at=MagicMock(isoformat=lambda: "2024-01-01T01:00:00")
            )
        ]
        mock_conversation_repository.list_by_agent_version.return_value = mock_conversations
        mock_conversation_repository.count_by_agent_version.return_value = 1

        mock_agent = MagicMock()
        mock_agent.name = "Test Agent"
        mock_agent_repository.find_by_id.return_value = mock_agent

        # Act
        result = await conversation_service.list_conversations(user_id, agent_id, version)

        # Assert
        assert len(result.conversations) == 1
        assert result.total == 1
        assert result.max_allowed == 5

    @pytest.mark.asyncio
    async def test_list_conversations_empty(
        self,
        conversation_service,
        mock_conversation_repository,
        mock_agent_repository
    ):
        """대화 목록이 비어있는 경우 테스트"""
        # Arrange
        mock_conversation_repository.list_by_agent_version.return_value = []
        mock_conversation_repository.count_by_agent_version.return_value = 0
        mock_agent_repository.find_by_id.return_value = MagicMock(name="Agent")

        # Act
        result = await conversation_service.list_conversations("user-123", "agent-456", "1.0.0")

        # Assert
        assert len(result.conversations) == 0
        assert result.total == 0


class TestCreateConversation:
    """create_conversation 테스트"""

    @pytest.mark.asyncio
    async def test_create_conversation_success(
        self,
        conversation_service,
        mock_conversation_repository,
        mock_agent_repository
    ):
        """대화 생성 성공 테스트"""
        # Arrange
        user_id = "user-123"
        agent_id = "agent-456"
        version = "1.0.0"
        first_message = "안녕하세요, 도움이 필요합니다."

        mock_conversation_repository.count_by_agent_version.return_value = 0
        mock_conversation_repository.save.return_value = MagicMock()

        mock_agent = MagicMock()
        mock_agent.name = "Test Agent"
        mock_agent_repository.find_by_id.return_value = mock_agent

        # Act
        result = await conversation_service.create_conversation(
            user_id, agent_id, version, first_message
        )

        # Assert
        assert result is not None
        mock_conversation_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_conversation_auto_delete_oldest(
        self,
        conversation_service,
        mock_conversation_repository,
        mock_agent_repository
    ):
        """최대 대화 수 초과 시 가장 오래된 대화 삭제 테스트"""
        # Arrange
        mock_conversation_repository.count_by_agent_version.return_value = 5

        oldest_conv = MagicMock()
        oldest_conv.id.value = "oldest-conv"
        mock_conversation_repository.find_oldest_by_agent_version.return_value = oldest_conv

        mock_agent = MagicMock()
        mock_agent.name = "Test Agent"
        mock_agent_repository.find_by_id.return_value = mock_agent

        # Act
        await conversation_service.create_conversation(
            "user-123", "agent-456", "1.0.0", "Hello"
        )

        # Assert
        mock_conversation_repository.delete.assert_called_once_with("oldest-conv")


class TestDeleteConversation:
    """delete_conversation 테스트"""

    @pytest.mark.asyncio
    async def test_delete_conversation_success(
        self,
        conversation_service,
        mock_conversation_repository
    ):
        """대화 삭제 성공 테스트"""
        # Arrange
        user_id = "user-123"
        conversation_id = "conv-456"

        mock_conversation = MagicMock()
        mock_conversation.user_id = user_id
        mock_conversation_repository.find_by_id.return_value = mock_conversation

        # Act
        result = await conversation_service.delete_conversation(user_id, conversation_id)

        # Assert
        assert result.status == "deleted"
        mock_conversation_repository.delete.assert_called_once_with(conversation_id)

    @pytest.mark.asyncio
    async def test_delete_conversation_not_found(
        self,
        conversation_service,
        mock_conversation_repository
    ):
        """대화가 존재하지 않는 경우 테스트"""
        # Arrange
        mock_conversation_repository.find_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ConversationNotFoundException):
            await conversation_service.delete_conversation("user-123", "nonexistent")

    @pytest.mark.asyncio
    async def test_delete_conversation_wrong_user(
        self,
        conversation_service,
        mock_conversation_repository
    ):
        """다른 사용자의 대화 삭제 시도 테스트"""
        # Arrange
        mock_conversation = MagicMock()
        mock_conversation.user_id = "other-user"
        mock_conversation_repository.find_by_id.return_value = mock_conversation

        # Act & Assert
        with pytest.raises(ConversationNotFoundException):
            await conversation_service.delete_conversation("user-123", "conv-456")
