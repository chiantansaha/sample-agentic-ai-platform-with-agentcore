"""E2E Tests - Conversation Resume Flow (대화 이어하기)"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.playground.dto.response import (
    ConversationResponse,
    ConversationListResponse,
    DeploymentResponse,
    DeploymentStatusResponse,
    DestroyResponse
)
from app.playground.presentation.controller import (
    get_deployment_service,
    get_conversation_service
)


# Note: client, app_with_auth, mock_token_payload fixtures are provided by conftest.py


class TestConversationResumeFlow:
    """대화 이어하기 E2E 플로우 테스트"""

    def test_resume_conversation_flow(
        self,
        app_with_auth,
        client,
        mock_token_payload
    ):
        """대화 이어하기 전체 플로우: 대화목록 조회 → 이전 대화로 배포 → 채팅 계속"""
        mock_conv_service = AsyncMock()
        mock_deploy_service = AsyncMock()
        app_with_auth.dependency_overrides[get_conversation_service] = lambda: mock_conv_service
        app_with_auth.dependency_overrides[get_deployment_service] = lambda: mock_deploy_service

        agent_id = "agent-456"
        version = "1.0.0"
        conversation_id = "conv-existing-123"

        # Step 1: 대화 목록 조회 - 이전 대화가 있음
        mock_conv_service.list_conversations.return_value = ConversationListResponse(
            conversations=[
                ConversationResponse(
                    id=conversation_id,
                    agent_id=agent_id,
                    agent_version=version,
                    agent_name="Test Agent",
                    title="이전 대화",
                    message_count=10,
                    last_message_preview="이전에 대화한 내용입니다.",
                    created_at="2024-01-01T00:00:00",
                    updated_at="2024-01-01T01:00:00"
                )
            ],
            total=1,
            max_allowed=5
        )

        list_response = client.get(
            "/playground/conversations",
            params={"agent_id": agent_id, "version": version},
        )

        assert list_response.status_code == 200
        list_data = list_response.json()["data"]
        assert list_data["total"] == 1
        assert list_data["conversations"][0]["id"] == conversation_id
        assert list_data["conversations"][0]["message_count"] == 10

        # Step 2: 이전 대화로 Runtime 배포 (conversation_id 포함)
        mock_deploy_service.deploy_agent.return_value = DeploymentResponse(
            id="deploy-resume-123",
            agent_id=agent_id,
            version=version,
            status="ready",
            runtime_id="runtime-resume-001",
            runtime_arn="arn:aws:runtime:resume",
            endpoint_url="https://runtime.resume.endpoint",
            conversation_id=conversation_id,  # 이전 대화 ID
            is_resumed=True,  # 이어하기
            message_count=10,  # 이전 메시지 수
            idle_timeout=300,
            max_lifetime=1800,
            created_at="2024-01-01T02:00:00",
            updated_at="2024-01-01T02:00:00",
            expires_at="2024-01-01T02:30:00"
        )

        deploy_response = client.post(
            "/playground/runtime/deploy",
            json={
                "agent_id": agent_id,
                "version": version,
                "conversation_id": conversation_id  # 이어하기
            },
        )

        assert deploy_response.status_code == 200
        deploy_data = deploy_response.json()["data"]
        assert deploy_data["is_resumed"] is True
        assert deploy_data["conversation_id"] == conversation_id
        assert deploy_data["message_count"] == 10

        deployment_id = deploy_data["id"]

        # Step 3: 이어서 채팅
        async def mock_stream():
            yield {"type": "text", "content": "이전 대화를 기억하고 있습니다. "}
            yield {"type": "text", "content": "무엇을 도와드릴까요?"}
            yield {"type": "done"}

        mock_deploy_service.stream_runtime_chat = MagicMock(return_value=mock_stream())

        chat_response = client.post(
            f"/playground/runtime/deployments/{deployment_id}/chat/stream",
            json={"message": "이전에 얘기하던 내용 기억해?"},
        )

        assert chat_response.status_code == 200
        assert "text/event-stream" in chat_response.headers["content-type"]

        # Step 4: 대화 종료
        mock_deploy_service.destroy_deployment.return_value = DestroyResponse(
            deployment_id=deployment_id,
            status="destroyed",
            message="Runtime이 성공적으로 종료되었습니다."
        )

        destroy_response = client.delete(
            f"/playground/runtime/deployments/{deployment_id}",
        )

        assert destroy_response.status_code == 200

        # Step 5: 대화 목록 다시 조회 - 메시지 수 증가 확인
        mock_conv_service.list_conversations.return_value = ConversationListResponse(
            conversations=[
                ConversationResponse(
                    id=conversation_id,
                    agent_id=agent_id,
                    agent_version=version,
                    agent_name="Test Agent",
                    title="이전 대화",
                    message_count=12,  # 2개 증가 (사용자 + 봇)
                    last_message_preview="무엇을 도와드릴까요?",
                    created_at="2024-01-01T00:00:00",
                    updated_at="2024-01-01T02:05:00"
                )
            ],
            total=1,
            max_allowed=5
        )

        updated_list_response = client.get(
            "/playground/conversations",
            params={"agent_id": agent_id, "version": version},
        )

        assert updated_list_response.status_code == 200
        updated_data = updated_list_response.json()["data"]
        assert updated_data["conversations"][0]["message_count"] == 12

    def test_new_conversation_creation(
        self,
        app_with_auth,
        client,
        mock_token_payload
    ):
        """새 대화 생성 플로우"""
        mock_conv_service = AsyncMock()
        app_with_auth.dependency_overrides[get_conversation_service] = lambda: mock_conv_service

        agent_id = "agent-456"
        version = "1.0.0"

        # Step 1: 대화 목록 조회 - 비어있음
        mock_conv_service.list_conversations.return_value = ConversationListResponse(
            conversations=[],
            total=0,
            max_allowed=5
        )

        list_response = client.get(
            "/playground/conversations",
            params={"agent_id": agent_id, "version": version},
        )

        assert list_response.status_code == 200
        assert list_response.json()["data"]["total"] == 0

        # Step 2: 새 대화 생성
        mock_conv_service.create_conversation.return_value = ConversationResponse(
            id="conv-new-123",
            agent_id=agent_id,
            agent_version=version,
            agent_name="Test Agent",
            title="새로운 대화",
            message_count=1,
            last_message_preview="안녕하세요!",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00"
        )

        create_response = client.post(
            "/playground/conversations",
            json={
                "agent_id": agent_id,
                "version": version,
                "first_message": "안녕하세요!"
            },
        )

        assert create_response.status_code == 200
        create_data = create_response.json()["data"]
        assert create_data["id"] == "conv-new-123"
        assert create_data["message_count"] == 1

    def test_delete_conversation_from_list(
        self,
        app_with_auth,
        client,
        mock_token_payload
    ):
        """대화 목록에서 삭제 플로우"""
        mock_conv_service = AsyncMock()
        app_with_auth.dependency_overrides[get_conversation_service] = lambda: mock_conv_service

        agent_id = "agent-456"
        version = "1.0.0"
        conversation_id = "conv-to-delete"

        # Step 1: 대화 목록 조회
        mock_conv_service.list_conversations.return_value = ConversationListResponse(
            conversations=[
                ConversationResponse(
                    id=conversation_id,
                    agent_id=agent_id,
                    agent_version=version,
                    agent_name="Test Agent",
                    title="삭제할 대화",
                    message_count=5,
                    last_message_preview="...",
                    created_at="2024-01-01T00:00:00",
                    updated_at="2024-01-01T00:00:00"
                )
            ],
            total=1,
            max_allowed=5
        )

        list_response = client.get(
            "/playground/conversations",
            params={"agent_id": agent_id, "version": version},
        )

        assert list_response.status_code == 200
        assert list_response.json()["data"]["total"] == 1

        # Step 2: 대화 삭제
        mock_conv_service.delete_conversation.return_value = DestroyResponse(
            conversation_id=conversation_id,
            status="deleted",
            message="대화가 삭제되었습니다."
        )

        delete_response = client.delete(
            f"/playground/conversations/{conversation_id}",
        )

        assert delete_response.status_code == 200
        assert delete_response.json()["data"]["status"] == "deleted"

        # Step 3: 대화 목록 다시 조회 - 비어있음
        mock_conv_service.list_conversations.return_value = ConversationListResponse(
            conversations=[],
            total=0,
            max_allowed=5
        )

        updated_list_response = client.get(
            "/playground/conversations",
            params={"agent_id": agent_id, "version": version},
        )

        assert updated_list_response.status_code == 200
        assert updated_list_response.json()["data"]["total"] == 0
