"""PlaygroundSession Entity"""
from dataclasses import dataclass, field
from typing import List

from ..value_objects import SessionId, Message, SessionStatus
from app.shared.utils.timestamp import now_timestamp


@dataclass
class PlaygroundSession:
    """Playground Session Aggregate Root"""
    id: SessionId
    user_id: str
    agent_id: str
    agent_version: str
    messages: List[Message] = field(default_factory=list)
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: int = field(default_factory=now_timestamp)
    updated_at: int = field(default_factory=now_timestamp)

    def add_message(self, message: Message):
        """메시지 추가"""
        self.messages.append(message)
        self.updated_at = now_timestamp()

    def close(self):
        """세션 종료"""
        self.status = SessionStatus.CLOSED
        self.updated_at = now_timestamp()
