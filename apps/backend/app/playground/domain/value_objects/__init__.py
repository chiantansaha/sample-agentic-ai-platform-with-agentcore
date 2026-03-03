"""Playground Value Objects"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from app.shared.utils.timestamp import now_timestamp


@dataclass(frozen=True)
class SessionId:
    """Session ID Value Object"""
    value: str


@dataclass(frozen=True)
class DeploymentId:
    """Deployment ID Value Object"""
    value: str


@dataclass(frozen=True)
class ConversationId:
    """Conversation ID Value Object"""
    value: str


@dataclass(frozen=True)
class Message:
    """Message Value Object"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: int = field(default_factory=now_timestamp)  # Unix timestamp (seconds)


class SessionStatus(Enum):
    """Session Status"""
    ACTIVE = "active"
    CLOSED = "closed"


class DeploymentStatus(Enum):
    """Deployment Status for AgentCore Runtime (Container 방식)"""
    PENDING = "pending"
    BUILDING = "building"        # Docker 빌드 및 ECR 푸시 중
    CREATING = "creating"        # AgentCore Runtime 생성 중
    READY = "ready"
    FAILED = "failed"
    DELETING = "deleting"
    DELETED = "deleted"


class ConversationStatus(Enum):
    """Conversation Status"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"
