"""KB Version Repository Interface"""
from abc import ABC, abstractmethod
from typing import List, Optional
from ..entities.knowledge_base_version import KnowledgeBaseVersion


class VersionRepository(ABC):
    """버전 저장소 인터페이스"""

    @abstractmethod
    async def save(self, version: KnowledgeBaseVersion) -> KnowledgeBaseVersion:
        """버전 저장"""
        pass

    @abstractmethod
    async def find_by_kb_id(self, kb_id: str) -> List[KnowledgeBaseVersion]:
        """KB ID로 모든 버전 조회"""
        pass

    @abstractmethod
    async def find_by_kb_id_and_version(
        self, kb_id: str, version: int
    ) -> Optional[KnowledgeBaseVersion]:
        """KB ID와 버전 번호로 특정 버전 조회"""
        pass

    @abstractmethod
    async def find_latest_by_kb_id(self, kb_id: str) -> Optional[KnowledgeBaseVersion]:
        """KB ID로 최신 버전 조회"""
        pass

    @abstractmethod
    async def delete_by_kb_id(self, kb_id: str) -> None:
        """KB ID로 모든 버전 삭제"""
        pass