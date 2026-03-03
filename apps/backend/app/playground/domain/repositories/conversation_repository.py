"""Conversation Repository Interface"""
from abc import ABC, abstractmethod
from typing import Optional, List

from ..entities.conversation import Conversation


class ConversationRepository(ABC):
    """Conversation Repository Interface"""

    @abstractmethod
    async def save(self, conversation: Conversation) -> Conversation:
        """대화 메타데이터 저장"""
        pass

    @abstractmethod
    async def find_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """ID로 대화 조회"""
        pass

    @abstractmethod
    async def list_by_agent_version(
        self,
        user_id: str,
        agent_id: str,
        agent_version: str,
        limit: int = 5
    ) -> List[Conversation]:
        """에이전트/버전별 대화 목록 조회 (최신순, 최대 limit개)"""
        pass

    @abstractmethod
    async def list_by_user(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Conversation]:
        """사용자의 전체 대화 목록 조회 (최신순)"""
        pass

    @abstractmethod
    async def count_by_agent_version(
        self,
        user_id: str,
        agent_id: str,
        agent_version: str
    ) -> int:
        """에이전트/버전별 대화 수 조회"""
        pass

    @abstractmethod
    async def delete(self, conversation_id: str) -> None:
        """대화 삭제 (메타데이터만, S3는 별도 처리)"""
        pass

    @abstractmethod
    async def find_oldest_by_agent_version(
        self,
        user_id: str,
        agent_id: str,
        agent_version: str
    ) -> Optional[Conversation]:
        """가장 오래된 대화 조회 (5개 초과 시 삭제용)"""
        pass
