"""Playground Request DTOs"""
from pydantic import BaseModel, Field
from typing import Optional


class CreateSessionRequest(BaseModel):
    """세션 생성 요청"""
    agent_id: str = Field(..., description="Agent ID")
    agent_version: str = Field(..., description="Agent Version")


class SendMessageRequest(BaseModel):
    """메시지 전송 요청"""
    message: str = Field(..., description="사용자 메시지")


class StreamChatRequest(BaseModel):
    """스트리밍 채팅 요청 (세션 없이)"""
    agent_id: str = Field(..., description="Agent ID")
    version: str = Field(..., description="Agent Version")
    message: str = Field(..., description="사용자 메시지")


# ==================== AgentCore Runtime ====================

class DeployAgentRequest(BaseModel):
    """AgentCore Runtime 배포 요청 (Container 방식)"""
    agent_id: str = Field(..., description="Agent ID")
    version: str = Field(..., description="Agent Version")
    conversation_id: Optional[str] = Field(None, description="기존 대화 이어하기용 Conversation ID")
    force_rebuild: bool = Field(False, description="ECR 이미지 강제 재빌드 여부")


class RuntimeChatRequest(BaseModel):
    """Runtime 채팅 요청"""
    message: str = Field(..., description="사용자 메시지")


class CreateConversationRequest(BaseModel):
    """대화 생성 요청"""
    agent_id: str = Field(..., description="Agent ID")
    version: str = Field(..., description="Agent Version")
    first_message: str = Field(..., description="첫 메시지 (제목 생성용)")
