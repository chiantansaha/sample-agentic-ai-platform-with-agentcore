"""E2E Tests - Conversation Limit Flow (대화 제한)"""
import pytest
from unittest.mock import AsyncMock

from app.playground.dto.response import (
    ConversationResponse,
    ConversationListResponse,
    DestroyResponse
)
from app.playground.exception.exceptions import MaxConversationsExceededException
from app.playground.presentation.controller import get_conversation_service


# Note: client, app_with_auth, mock_token_payload fixtures are provided by conftest.py


class TestConversationLimitFlow:
    """대화 제한 E2E 플로우 테스트"""

    def test_max_conversations_limit_exceeded(
        self,
        app_with_auth,
        client,
        mock_token_payload
    ):
        """최대 대화 수 초과 테스트: 5개 제한일 때 6번째 대화 생성 시도"""
        mock_conv_service = AsyncMock()
        app_with_auth.dependency_overrides[get_conversation_service] = lambda: mock_conv_service

        agent_id = "agent-456"
        version = "1.0.0"

        # Step 1: 대화 목록 조회 - 이미 5개 있음
        existing_conversations = [
            ConversationResponse(
                id=f"conv-{i}",
                agent_id=agent_id,
                agent_version=version,
                agent_name="Test Agent",
                title=f"대화 {i}",
                message_count=i + 1,
                last_message_preview=f"메시지 {i}",
                created_at=f"2024-01-0{i+1}T00:00:00",
                updated_at=f"2024-01-0{i+1}T00:00:00"
            )
            for i in range(5)
        ]

        mock_conv_service.list_conversations.return_value = ConversationListResponse(
            conversations=existing_conversations,
            total=5,
            max_allowed=5
        )

        list_response = client.get(
            "/playground/conversations",
            params={"agent_id": agent_id, "version": version},
        )

        assert list_response.status_code == 200
        list_data = list_response.json()["data"]
        assert list_data["total"] == 5
        assert list_data["max_allowed"] == 5

        # Step 2: 6번째 대화 생성 시도 - 실패
        mock_conv_service.create_conversation.side_effect = MaxConversationsExceededException(
            max_count=5
        )

        create_response = client.post(
            "/playground/conversations",
            json={
                "agent_id": agent_id,
                "version": version,
                "first_message": "새 대화 시작"
            },
        )

        # 409 Conflict 또는 다른 적절한 에러 코드
        assert create_response.status_code in [409, 400]

    def test_auto_delete_oldest_when_limit_exceeded(
        self,
        app_with_auth,
        client,
        mock_token_payload
    ):
        """오래된 대화 자동 삭제 플로우 테스트"""
        mock_conv_service = AsyncMock()
        app_with_auth.dependency_overrides[get_conversation_service] = lambda: mock_conv_service

        agent_id = "agent-456"
        version = "1.0.0"

        # Step 1: 대화 목록 조회 - 이미 5개 있음
        existing_conversations = [
            ConversationResponse(
                id=f"conv-{i}",
                agent_id=agent_id,
                agent_version=version,
                agent_name="Test Agent",
                title=f"대화 {i}",
                message_count=i + 1,
                last_message_preview=f"메시지 {i}",
                created_at=f"2024-01-0{i+1}T00:00:00",
                updated_at=f"2024-01-0{i+1}T00:00:00"
            )
            for i in range(5)
        ]

        mock_conv_service.list_conversations.return_value = ConversationListResponse(
            conversations=existing_conversations,
            total=5,
            max_allowed=5
        )

        list_response = client.get(
            "/playground/conversations",
            params={"agent_id": agent_id, "version": version},
        )

        assert list_response.status_code == 200
        assert list_response.json()["data"]["total"] == 5

        # Step 2: 가장 오래된 대화 삭제
        oldest_id = "conv-0"
        mock_conv_service.delete_conversation.return_value = DestroyResponse(
            conversation_id=oldest_id,
            status="deleted",
            message="대화가 삭제되었습니다."
        )

        delete_response = client.delete(
            f"/playground/conversations/{oldest_id}",
        )

        assert delete_response.status_code == 200

        # Step 3: 새 대화 생성 - 성공
        mock_conv_service.create_conversation.return_value = ConversationResponse(
            id="conv-new",
            agent_id=agent_id,
            agent_version=version,
            agent_name="Test Agent",
            title="새 대화",
            message_count=1,
            last_message_preview="새 메시지",
            created_at="2024-01-10T00:00:00",
            updated_at="2024-01-10T00:00:00"
        )

        create_response = client.post(
            "/playground/conversations",
            json={
                "agent_id": agent_id,
                "version": version,
                "first_message": "새 대화 시작"
            },
        )

        assert create_response.status_code == 200
        assert create_response.json()["data"]["id"] == "conv-new"

    def test_conversation_count_per_agent_version(
        self,
        app_with_auth,
        client,
        mock_token_payload
    ):
        """Agent/버전별 대화 수 분리 테스트"""
        mock_conv_service = AsyncMock()
        app_with_auth.dependency_overrides[get_conversation_service] = lambda: mock_conv_service

        # Agent 1, Version 1.0.0 - 3개 대화
        mock_conv_service.list_conversations.return_value = ConversationListResponse(
            conversations=[
                ConversationResponse(
                    id=f"conv-a1-v1-{i}",
                    agent_id="agent-1",
                    agent_version="1.0.0",
                    agent_name="Agent 1",
                    title=f"대화 {i}",
                    message_count=i + 1,
                    last_message_preview="...",
                    created_at="2024-01-01T00:00:00",
                    updated_at="2024-01-01T00:00:00"
                )
                for i in range(3)
            ],
            total=3,
            max_allowed=5
        )

        response_a1_v1 = client.get(
            "/playground/conversations",
            params={"agent_id": "agent-1", "version": "1.0.0"},
        )

        assert response_a1_v1.status_code == 200
        assert response_a1_v1.json()["data"]["total"] == 3

        # Agent 1, Version 2.0.0 - 2개 대화
        mock_conv_service.list_conversations.return_value = ConversationListResponse(
            conversations=[
                ConversationResponse(
                    id=f"conv-a1-v2-{i}",
                    agent_id="agent-1",
                    agent_version="2.0.0",
                    agent_name="Agent 1",
                    title=f"대화 {i}",
                    message_count=i + 1,
                    last_message_preview="...",
                    created_at="2024-01-01T00:00:00",
                    updated_at="2024-01-01T00:00:00"
                )
                for i in range(2)
            ],
            total=2,
            max_allowed=5
        )

        response_a1_v2 = client.get(
            "/playground/conversations",
            params={"agent_id": "agent-1", "version": "2.0.0"},
        )

        assert response_a1_v2.status_code == 200
        assert response_a1_v2.json()["data"]["total"] == 2

        # Agent 2, Version 1.0.0 - 0개 대화
        mock_conv_service.list_conversations.return_value = ConversationListResponse(
            conversations=[],
            total=0,
            max_allowed=5
        )

        response_a2_v1 = client.get(
            "/playground/conversations",
            params={"agent_id": "agent-2", "version": "1.0.0"},
        )

        assert response_a2_v1.status_code == 200
        assert response_a2_v1.json()["data"]["total"] == 0

    def test_approaching_limit_warning(
        self,
        app_with_auth,
        client,
        mock_token_payload
    ):
        """제한 도달 임박 경고 테스트"""
        mock_conv_service = AsyncMock()
        app_with_auth.dependency_overrides[get_conversation_service] = lambda: mock_conv_service

        agent_id = "agent-456"
        version = "1.0.0"

        # 4/5 대화 사용 중
        mock_conv_service.list_conversations.return_value = ConversationListResponse(
            conversations=[
                ConversationResponse(
                    id=f"conv-{i}",
                    agent_id=agent_id,
                    agent_version=version,
                    agent_name="Test Agent",
                    title=f"대화 {i}",
                    message_count=1,
                    last_message_preview="...",
                    created_at="2024-01-01T00:00:00",
                    updated_at="2024-01-01T00:00:00"
                )
                for i in range(4)
            ],
            total=4,
            max_allowed=5
        )

        response = client.get(
            "/playground/conversations",
            params={"agent_id": agent_id, "version": version},
        )

        assert response.status_code == 200
        data = response.json()["data"]

        # 프론트엔드에서 사용할 수 있는 정보 확인
        assert data["total"] == 4
        assert data["max_allowed"] == 5

        # 남은 슬롯 계산 가능
        remaining_slots = data["max_allowed"] - data["total"]
        assert remaining_slots == 1
