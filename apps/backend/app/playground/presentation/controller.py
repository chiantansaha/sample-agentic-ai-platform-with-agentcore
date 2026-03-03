"""Playground REST API Controller"""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)
from fastapi.responses import StreamingResponse

from app.config import settings
from app.middleware.auth import verify_okta_token
from app.agent.application.service import AgentApplicationService
from app.agent.infrastructure.repositories.dynamodb_agent_repository import DynamoDBAgentRepository
from app.agent.infrastructure.repositories.dynamodb_agent_version_repository import DynamoDBAgentVersionRepository
from app.agent.infrastructure.repositories.mock_agent_repository import MockAgentRepository
from app.agent.infrastructure.repositories.mock_agent_version_repository import MockAgentVersionRepository
from app.knowledge_bases.infrastructure.repositories.dynamodb_kb_repository import DynamoDBKBRepository
from app.knowledge_bases.infrastructure.repositories.mock_kb_repository import MockKBRepository
from ..application.service import PlaygroundApplicationService, DeploymentService, ConversationService
from ..infrastructure.repositories.dynamodb_session_repository import DynamoDBSessionRepository
from ..infrastructure.repositories.dynamodb_deployment_repository import DynamoDBDeploymentRepository
from ..infrastructure.repositories.dynamodb_conversation_repository import DynamoDBConversationRepository
from ..infrastructure.clients.strands_agent_client import StrandsAgentClient
from ..infrastructure.clients.agentcore_client import AgentCoreClient
from app.mcp.infrastructure.mcp_repository_impl import DynamoDBMCPRepository
from app.mcp.infrastructure.mock_mcp_repository import MockMCPRepository
from ..infrastructure.code_generator import AgentCodeGenerator
from ..dto.request import (
    CreateSessionRequest, SendMessageRequest, StreamChatRequest,
    DeployAgentRequest, RuntimeChatRequest, CreateConversationRequest
)
from ..exception.exceptions import (
    SessionNotFoundException, AgentNotFoundException,
    DeploymentNotFoundException, DeploymentAlreadyExistsException,
    ConversationNotFoundException, RuntimeNotActiveException,
    MaxConversationsExceededException
)

router = APIRouter()

# 싱글톤 클라이언트들 (Container 방식)
_strands_client = StrandsAgentClient()
_agentcore_client = AgentCoreClient(
    region=settings.AWS_REGION,
    role_arn=settings.PLAYGROUND_RUNTIME_ROLE_ARN or settings.AGENTCORE_ROLE_ARN,
    ecr_repository=settings.PLAYGROUND_ECR_REPOSITORY,
    codebuild_project=settings.CODEBUILD_PROJECT_NAME,
    source_bucket=settings.AGENT_BUILD_SOURCE_BUCKET
)
_code_generator = AgentCodeGenerator()


def _is_mock_mode() -> bool:
    """Mock 모드 여부 확인"""
    return settings.ENVIRONMENT in ("dev", "development", "local")


def get_agent_service() -> AgentApplicationService:
    """Agent Service 의존성 주입"""
    if _is_mock_mode() and not settings.DYNAMODB_AGENT_TABLE:
        logger.info("📦 Using MockAgentRepository (demo mode)")
        repository = MockAgentRepository()
        version_repository = MockAgentVersionRepository()
    else:
        repository = DynamoDBAgentRepository()
        version_repository = DynamoDBAgentVersionRepository()
    return AgentApplicationService(repository, version_repository)


def get_playground_service() -> PlaygroundApplicationService:
    """Playground Service 의존성 주입"""
    session_repository = DynamoDBSessionRepository()
    if _is_mock_mode() and not settings.DYNAMODB_AGENT_TABLE:
        agent_repository = MockAgentRepository()
    else:
        agent_repository = DynamoDBAgentRepository()
    return PlaygroundApplicationService(session_repository, _strands_client, agent_repository)


def get_deployment_service() -> DeploymentService:
    """Deployment Service 의존성 주입"""
    deployment_repository = DynamoDBDeploymentRepository()
    conversation_repository = DynamoDBConversationRepository()

    if _is_mock_mode() and not settings.DYNAMODB_AGENT_TABLE:
        agent_repository = MockAgentRepository()
    else:
        agent_repository = DynamoDBAgentRepository()

    if _is_mock_mode() and not settings.DYNAMODB_KB_TABLE:
        kb_repository = MockKBRepository()
    else:
        kb_repository = DynamoDBKBRepository()

    if _is_mock_mode() and not settings.DYNAMODB_MCP_TABLE:
        mcp_repository = MockMCPRepository()
    else:
        mcp_repository = DynamoDBMCPRepository()

    return DeploymentService(
        deployment_repository=deployment_repository,
        conversation_repository=conversation_repository,
        agent_repository=agent_repository,
        kb_repository=kb_repository,
        agentcore_client=_agentcore_client,
        code_generator=_code_generator,
        mcp_repository=mcp_repository
    )


def get_conversation_service() -> ConversationService:
    """Conversation Service 의존성 주입"""
    conversation_repository = DynamoDBConversationRepository()
    if _is_mock_mode() and not settings.DYNAMODB_AGENT_TABLE:
        agent_repository = MockAgentRepository()
    else:
        agent_repository = DynamoDBAgentRepository()
    return ConversationService(conversation_repository, agent_repository)


@router.get("/agents", response_model=dict)
async def get_production_agents(
    token_payload: dict = Depends(verify_okta_token),
    agent_service: AgentApplicationService = Depends(get_agent_service)
):
    """Production Agent 목록 조회 (enabled 상태만, draft 제외)"""
    agents = await agent_service.list_agents()
    # Status가 enabled인 Agent만 반환 (draft, disabled 제외)
    enabled_agents = [a for a in agents.items if a.status == "enabled"]
    return {
        "data": [a.dict() for a in enabled_agents],
        "status": 200
    }


@router.get("/agents/{agent_id}/versions", response_model=dict)
async def get_agent_versions(
    agent_id: str,
    token_payload: dict = Depends(verify_okta_token),
    agent_service: AgentApplicationService = Depends(get_agent_service)
):
    """Agent 버전 목록 조회"""
    versions = await agent_service.get_version_history(agent_id)
    return {
        "data": versions,
        "status": 200
    }


@router.post("/chat/stream")
async def stream_chat(
    request: StreamChatRequest,
    token_payload: dict = Depends(verify_okta_token),
    service: PlaygroundApplicationService = Depends(get_playground_service)
):
    """SSE 스트리밍 채팅"""

    async def generate():
        try:
            async for event in service.stream_message(
                request.agent_id,
                request.version,
                request.message
            ):
                # 이벤트 타입별 필터링
                if isinstance(event, dict):
                    # contentBlockDelta 이벤트에서 텍스트 추출
                    if "event" in event:
                        event_data = event["event"]
                        if "contentBlockDelta" in event_data:
                            delta = event_data["contentBlockDelta"].get("delta", {})
                            if "text" in delta:
                                yield f"data: {json.dumps({'type': 'text', 'content': delta['text']}, ensure_ascii=False)}\n\n"
                        # 메시지 완료 이벤트
                        elif "messageStop" in event_data:
                            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
                    # 최종 메시지 전체
                    elif "message" in event:
                        message_content = event["message"].get("content", [])
                        if message_content and len(message_content) > 0:
                            full_text = message_content[0].get("text", "")
                            yield f"data: {json.dumps({'type': 'complete', 'content': full_text}, ensure_ascii=False)}\n\n"

        except AgentNotFoundException as e:
            logger.error(f"SSE stream error - AgentNotFound: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"SSE stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # nginx 버퍼링 비활성화
        }
    )


@router.post("/sessions", response_model=dict)
async def create_session(
    request: CreateSessionRequest,
    token_payload: dict = Depends(verify_okta_token),
    service: PlaygroundApplicationService = Depends(get_playground_service)
):
    """Playground 세션 생성"""
    try:
        user_id = token_payload["sub"]
        session = await service.create_session(
            user_id=user_id,
            agent_id=request.agent_id,
            agent_version=request.agent_version
        )
        return {"data": session.dict(), "status": 200}
    except AgentNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/sessions/{session_id}/messages", response_model=dict)
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    token_payload: dict = Depends(verify_okta_token),
    service: PlaygroundApplicationService = Depends(get_playground_service)
):
    """메시지 전송 (비스트리밍)"""
    try:
        response = await service.send_message(session_id, request.message)
        return {"data": response.dict(), "status": 200}
    except SessionNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AgentNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/sessions/{session_id}/messages/stream")
async def stream_session_message(
    session_id: str,
    request: SendMessageRequest,
    token_payload: dict = Depends(verify_okta_token),
    service: PlaygroundApplicationService = Depends(get_playground_service)
):
    """세션 기반 SSE 스트리밍 채팅"""

    async def generate():
        try:
            async for event in service.stream_session_message(
                session_id,
                request.message
            ):
                # 이벤트 타입별 필터링
                if isinstance(event, dict):
                    # contentBlockDelta 이벤트에서 텍스트 추출
                    if "event" in event:
                        event_data = event["event"]
                        if "contentBlockDelta" in event_data:
                            delta = event_data["contentBlockDelta"].get("delta", {})
                            if "text" in delta:
                                yield f"data: {json.dumps({'type': 'text', 'content': delta['text']}, ensure_ascii=False)}\n\n"
                        # 메시지 완료 이벤트
                        elif "messageStop" in event_data:
                            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
                    # 최종 메시지 전체
                    elif "message" in event:
                        message_content = event["message"].get("content", [])
                        if message_content and len(message_content) > 0:
                            full_text = message_content[0].get("text", "")
                            yield f"data: {json.dumps({'type': 'complete', 'content': full_text}, ensure_ascii=False)}\n\n"

        except SessionNotFoundException as e:
            logger.error(f"SSE session stream error - SessionNotFound: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"
        except AgentNotFoundException as e:
            logger.error(f"SSE session stream error - AgentNotFound: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"SSE session stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            # 캐싱 완전 비활성화
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",

            # 연결 유지
            "Connection": "keep-alive",

            # Nginx/프록시 버퍼링 비활성화
            "X-Accel-Buffering": "no",

            # Content-Type 강제 (브라우저가 무시하지 못하게)
            "X-Content-Type-Options": "nosniff",

            # Transfer-Encoding chunked 힌트 (FastAPI가 자동으로 설정하지만 명시)
            # "Transfer-Encoding": "chunked" - FastAPI가 자동으로 설정하므로 주석 처리
        }
    )


@router.get("/sessions/{session_id}", response_model=dict)
async def get_session(
    session_id: str,
    token_payload: dict = Depends(verify_okta_token),
    service: PlaygroundApplicationService = Depends(get_playground_service)
):
    """세션 조회"""
    try:
        session = await service.get_session(session_id)
        return {"data": session.dict(), "status": 200}
    except SessionNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/sessions", response_model=dict)
async def get_user_sessions(
    token_payload: dict = Depends(verify_okta_token),
    service: PlaygroundApplicationService = Depends(get_playground_service)
):
    """사용자 세션 목록"""
    user_id = token_payload["sub"]
    sessions = await service.get_user_sessions(user_id)
    return {
        "data": [s.dict() for s in sessions],
        "status": 200
    }


# ==================== AgentCore Runtime API ====================

@router.post("/runtime/deploy", response_model=dict)
async def deploy_agent_runtime(
    request: DeployAgentRequest,
    token_payload: dict = Depends(verify_okta_token),
    service: DeploymentService = Depends(get_deployment_service)
):
    """Agent를 AgentCore Runtime으로 배포 (Container 방식)

    ECR 컨테이너 빌드 후 AgentCore Runtime에 배포합니다.
    """
    try:
        user_id = token_payload["sub"]
        deployment = await service.deploy_agent(
            user_id=user_id,
            agent_id=request.agent_id,
            version=request.version,
            conversation_id=request.conversation_id,
            force_rebuild=request.force_rebuild
        )
        return {"data": deployment.dict(), "status": 200}
    except AgentNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DeploymentAlreadyExistsException as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runtime/deployments/active", response_model=dict)
async def get_active_deployment(
    agent_id: str,
    version: str,
    token_payload: dict = Depends(verify_okta_token),
    service: DeploymentService = Depends(get_deployment_service)
):
    """기존 활성 배포 조회 (ready 상태인 것만 반환)"""
    try:
        user_id = token_payload.get("sub", "anonymous")
        deployment = await service.get_active_deployment(user_id, agent_id, version)
        if deployment:
            return {"data": deployment.dict(), "status": 200}
        return {"data": None, "status": 200}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runtime/deployments/{deployment_id}/status", response_model=dict)
async def get_deployment_status(
    deployment_id: str,
    token_payload: dict = Depends(verify_okta_token),
    service: DeploymentService = Depends(get_deployment_service)
):
    """배포 상태 조회"""
    try:
        status = await service.get_deployment_status(deployment_id)
        return {"data": status.dict(), "status": 200}
    except DeploymentNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/runtime/deployments/{deployment_id}", response_model=dict)
async def destroy_deployment(
    deployment_id: str,
    token_payload: dict = Depends(verify_okta_token),
    service: DeploymentService = Depends(get_deployment_service)
):
    """Runtime 종료"""
    try:
        result = await service.destroy_deployment(deployment_id)
        return {"data": result.dict(), "status": 200}
    except DeploymentNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/runtime/deployments/{deployment_id}/chat/stream")
async def stream_runtime_chat(
    deployment_id: str,
    request: RuntimeChatRequest,
    token_payload: dict = Depends(verify_okta_token),
    service: DeploymentService = Depends(get_deployment_service)
):
    """Runtime 스트리밍 채팅"""
    async def generate():
        import asyncio
        try:
            async for event in service.stream_runtime_chat(
                deployment_id,
                request.message
            ):
                event_json = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_json}\n\n"
                # 이벤트 루프에 제어권을 넘겨 즉시 flush
                await asyncio.sleep(0)

        except DeploymentNotFoundException as e:
            logger.error(f"Runtime chat error - DeploymentNotFound: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"
        except RuntimeNotActiveException as e:
            logger.error(f"Runtime chat error - RuntimeNotActive: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"Runtime chat error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            # 캐싱 완전 비활성화
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",

            # 연결 유지
            "Connection": "keep-alive",

            # Nginx/프록시 버퍼링 비활성화
            "X-Accel-Buffering": "no",

            # Content-Type 강제 (브라우저가 무시하지 못하게)
            "X-Content-Type-Options": "nosniff",

            # Transfer-Encoding chunked 힌트 (FastAPI가 자동으로 설정하지만 명시)
            # "Transfer-Encoding": "chunked" - FastAPI가 자동으로 설정하므로 주석 처리
        }
    )


# ==================== Conversation API ====================

@router.get("/conversations", response_model=dict)
async def list_conversations(
    agent_id: str,
    version: str,
    token_payload: dict = Depends(verify_okta_token),
    service: ConversationService = Depends(get_conversation_service)
):
    """대화 목록 조회"""
    user_id = token_payload["sub"]
    result = await service.list_conversations(user_id, agent_id, version)
    return {"data": result.dict(), "status": 200}


@router.post("/conversations", response_model=dict)
async def create_conversation(
    request: CreateConversationRequest,
    token_payload: dict = Depends(verify_okta_token),
    service: ConversationService = Depends(get_conversation_service)
):
    """대화 생성"""
    try:
        user_id = token_payload["sub"]
        conversation = await service.create_conversation(
            user_id=user_id,
            agent_id=request.agent_id,
            version=request.version,
            first_message=request.first_message
        )
        return {"data": conversation.dict(), "status": 200}
    except AgentNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except MaxConversationsExceededException as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/conversations/{conversation_id}/messages", response_model=dict)
async def get_conversation_messages(
    conversation_id: str,
    token_payload: dict = Depends(verify_okta_token),
    service: ConversationService = Depends(get_conversation_service)
):
    """대화 메시지 이력 조회"""
    try:
        user_id = token_payload["sub"]
        messages = await service.get_conversation_messages(user_id, conversation_id)
        return {"data": messages, "status": 200}
    except ConversationNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/conversations/{conversation_id}", response_model=dict)
async def delete_conversation(
    conversation_id: str,
    token_payload: dict = Depends(verify_okta_token),
    service: ConversationService = Depends(get_conversation_service)
):
    """대화 삭제"""
    try:
        user_id = token_payload["sub"]
        result = await service.delete_conversation(user_id, conversation_id)
        return {"data": result.dict(), "status": 200}
    except ConversationNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
