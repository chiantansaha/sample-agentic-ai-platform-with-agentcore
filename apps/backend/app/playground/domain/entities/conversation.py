"""Conversation Entity for AgentCore Runtime"""
from dataclasses import dataclass, field
from typing import Optional

from ..value_objects import ConversationId, ConversationStatus
from app.shared.utils.timestamp import now_timestamp


@dataclass
class Conversation:
    """Conversation Metadata Aggregate Root

    대화 메타데이터를 관리합니다.
    실제 대화 내용은 S3에 저장되며 (S3SessionManager 활용),
    이 엔티티는 대화의 메타정보만 관리합니다.
    """
    id: ConversationId
    user_id: str
    agent_id: str
    agent_version: str
    title: str  # 첫 메시지 기반 자동 생성
    message_count: int = 0
    s3_prefix: str = ""  # S3SessionManager에서 사용하는 prefix
    status: ConversationStatus = ConversationStatus.ACTIVE
    last_message_preview: Optional[str] = None
    created_at: int = field(default_factory=now_timestamp)
    updated_at: int = field(default_factory=now_timestamp)

    def increment_message_count(self, last_message: str):
        """메시지 수 증가 및 마지막 메시지 프리뷰 업데이트"""
        self.message_count += 1
        self.last_message_preview = last_message[:100] if len(last_message) > 100 else last_message
        self.updated_at = now_timestamp()

    def update_title(self, title: str):
        """대화 제목 업데이트"""
        self.title = title[:50] if len(title) > 50 else title
        self.updated_at = now_timestamp()

    def archive(self):
        """대화 아카이브"""
        self.status = ConversationStatus.ARCHIVED
        self.updated_at = now_timestamp()

    def mark_deleted(self):
        """대화 삭제 상태로 변경"""
        self.status = ConversationStatus.DELETED
        self.updated_at = now_timestamp()

    def is_active(self) -> bool:
        """활성 상태인지 확인"""
        return self.status == ConversationStatus.ACTIVE

    @staticmethod
    def generate_title_from_message(message: str) -> str:
        """첫 메시지로부터 제목 생성"""
        # 첫 문장 또는 첫 50자
        title = message.split('\n')[0].strip()
        if len(title) > 50:
            title = title[:47] + "..."
        return title if title else "새 대화"

    @staticmethod
    def generate_s3_prefix(user_id: str, agent_id: str, version: str, conversation_id: str) -> str:
        """S3 prefix 생성 (Strands S3SessionManager 형식)

        Strands S3SessionManager는 항상 다음 형식을 사용합니다:
        sessions/{user_id}/{agent_id}/{version}/session_{conversation_id}/

        주의: 'conversations'가 아니라 'sessions'이며, conversation_id 앞에 'session_' prefix가 붙습니다.
        """
        return f"sessions/{user_id}/{agent_id}/{version}/session_{conversation_id}"
