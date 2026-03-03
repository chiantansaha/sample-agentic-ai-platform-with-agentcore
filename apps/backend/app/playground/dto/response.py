"""Playground Response DTOs"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class MessageResponse(BaseModel):
    """메시지 응답"""
    role: str
    content: str
    timestamp: int  # Unix timestamp (seconds)


class SessionResponse(BaseModel):
    """세션 응답"""
    id: str
    user_id: str
    agent_id: str
    agent_version: str
    messages: List[MessageResponse]
    status: str
    created_at: int  # Unix timestamp (seconds)
    updated_at: int  # Unix timestamp (seconds)


class ChatResponse(BaseModel):
    """채팅 응답"""
    session_id: str
    message: MessageResponse


# ==================== AgentCore Runtime ====================

class DeploymentResponse(BaseModel):
    """배포 응답"""
    id: str
    agent_id: str
    version: str
    status: str
    runtime_id: Optional[str] = None
    runtime_arn: Optional[str] = None
    endpoint_url: Optional[str] = None
    conversation_id: Optional[str] = None
    is_resumed: bool = False
    message_count: int = 0
    build_id: Optional[str] = None
    build_phase: Optional[str] = None
    build_phase_message: Optional[str] = None
    idle_timeout: int = 300
    max_lifetime: int = 3600
    created_at: int  # Unix timestamp (seconds)
    updated_at: int  # Unix timestamp (seconds)
    expires_at: Optional[int] = None  # Unix timestamp (seconds)
    error_message: Optional[str] = None


class DeploymentStatusResponse(BaseModel):
    """배포 상태 응답"""
    deployment_id: str
    agent_id: str
    version: str
    status: str
    runtime_id: Optional[str] = None
    runtime_arn: Optional[str] = None
    endpoint_url: Optional[str] = None
    build_id: Optional[str] = None
    build_phase: Optional[str] = None
    build_phase_message: Optional[str] = None
    created_at: int  # Unix timestamp (seconds)
    idle_timeout: int
    max_lifetime: int
    expires_at: Optional[int] = None  # Unix timestamp (seconds)
    error_message: Optional[str] = None


class ConversationResponse(BaseModel):
    """대화 응답"""
    id: str
    agent_id: str
    agent_version: str
    agent_name: Optional[str] = None
    title: str
    message_count: int
    last_message_preview: Optional[str] = None
    created_at: int  # Unix timestamp (seconds)
    updated_at: int  # Unix timestamp (seconds)


class ConversationListResponse(BaseModel):
    """대화 목록 응답"""
    conversations: List[ConversationResponse]
    total: int
    max_allowed: int = 5


class DestroyResponse(BaseModel):
    """종료 응답"""
    deployment_id: Optional[str] = None
    conversation_id: Optional[str] = None
    status: str
    message: str
