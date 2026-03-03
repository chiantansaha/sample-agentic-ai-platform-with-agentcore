"""Local Chat API Controller

Agent 편집 페이지에서 AgentCore Runtime 배포 없이 로컬에서 즉시 Agent를 테스트할 수 있는 API.
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.middleware.auth import verify_okta_token
from app.agent.application.local_chat_service import LocalChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/local-chat", tags=["Local Chat"])


class PrepareRequest(BaseModel):
    """로컬 Agent 준비 요청"""
    system_prompt: str
    model: str
    mcp_ids: list[str] = []
    kb_ids: list[str] = []


class PrepareResponse(BaseModel):
    """로컬 Agent 준비 응답"""
    status: str
    session_id: str
    message: str


class ChatRequest(BaseModel):
    """로컬 채팅 요청"""
    session_id: str
    message: str


def get_local_chat_service() -> LocalChatService:
    """LocalChatService 의존성 주입"""
    return LocalChatService()


@router.post("/{agent_id}/prepare", response_model=PrepareResponse)
async def prepare_local_agent(
    agent_id: str,
    request: PrepareRequest,
    service: LocalChatService = Depends(get_local_chat_service),
    token_payload: dict = Depends(verify_okta_token),
):
    """로컬 Agent 준비

    AgentCore Runtime에 배포하지 않고 로컬에서 Agent를 즉시 실행.
    사용자당 1개 세션만 허용되며, 새 Prepare 요청 시 기존 세션은 자동 종료.
    """
    try:
        user_id = token_payload.get("sub", "anonymous")
        
        # 디버깅: 전달받은 model 값 로깅
        logger.info(f"🔍 Local chat prepare - model: {request.model}")
        print(f"🔍 Local chat prepare - model: {request.model}")

        session_id = await service.prepare_agent(
            agent_id=agent_id,
            user_id=user_id,
            system_prompt=request.system_prompt,
            model=request.model,
            mcp_ids=request.mcp_ids,
            kb_ids=request.kb_ids,
        )

        return PrepareResponse(
            status="ready",
            session_id=session_id,
            message="Agent가 준비되었습니다. 채팅을 시작하세요.",
        )

    except ValueError as e:
        logger.warning(f"Prepare failed - validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Prepare failed: {e}")
        raise HTTPException(status_code=500, detail=f"Agent 준비 실패: {str(e)}")


@router.post("/{agent_id}/stream")
async def stream_local_chat(
    agent_id: str,
    request: ChatRequest,
    service: LocalChatService = Depends(get_local_chat_service),
    token_payload: dict = Depends(verify_okta_token),
):
    """로컬 Agent 채팅 (SSE 스트리밍)

    Playground와 동일한 SSE 응답 포맷으로 스트리밍.
    - content: 텍스트 응답
    - tool_use: 도구 호출 시작
    - tool_result: 도구 호출 결과
    - done: 스트리밍 완료
    - error: 에러 발생
    """

    async def event_generator():
        try:
            async for chunk in service.stream_chat(
                session_id=request.session_id,
                message=request.message,
            ):
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        except ValueError as e:
            logger.warning(f"Local chat stream error - ValueError: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        except Exception as e:
            logger.error(f"Local chat stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': f'스트리밍 오류: {str(e)}'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginx 버퍼링 비활성화
        },
    )


@router.delete("/{agent_id}/session/{session_id}")
async def cleanup_session(
    agent_id: str,
    session_id: str,
    service: LocalChatService = Depends(get_local_chat_service),
    token_payload: dict = Depends(verify_okta_token),
):
    """세션 정리

    로컬 테스트 완료 후 세션을 명시적으로 정리.
    세션 타임아웃(30분)에 도달하면 자동으로 정리되지만,
    명시적으로 정리하면 리소스를 즉시 해제할 수 있음.
    """
    try:
        service.cleanup(session_id)
        return {"status": "success", "message": "세션이 정리되었습니다."}
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=f"세션 정리 실패: {str(e)}")


@router.post("/{agent_id}/session/{session_id}/cleanup")
async def cleanup_session_beacon(
    agent_id: str,
    session_id: str,
    service: LocalChatService = Depends(get_local_chat_service),
):
    """세션 정리 (navigator.sendBeacon용)

    브라우저가 페이지를 떠날 때 sendBeacon으로 호출됩니다.
    sendBeacon은 DELETE를 지원하지 않으므로 POST 엔드포인트를 별도 제공.
    인증 없이 호출 가능 (세션 ID만으로 정리).
    """
    try:
        service.cleanup(session_id)
        return {"status": "success"}
    except Exception as e:
        logger.warning(f"Beacon cleanup failed: {e}")
        return {"status": "error", "message": str(e)}
