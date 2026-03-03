"""Mock KB Version Repository for Demo Mode"""
from typing import List, Optional, Dict

from ...domain.repositories import VersionRepository
from ...domain.entities.knowledge_base_version import KnowledgeBaseVersion


class MockVersionRepository(VersionRepository):
    """Mock KB Version Repository - 메모리 기반 데모용 구현"""

    def __init__(self):
        # kb_id -> [versions] (최신순)
        self._versions: Dict[str, List[KnowledgeBaseVersion]] = {}

    async def save(self, version: KnowledgeBaseVersion) -> KnowledgeBaseVersion:
        """버전 저장"""
        kb_id = version.kb_id
        if kb_id not in self._versions:
            self._versions[kb_id] = []

        # 중복 체크
        existing = [v for v in self._versions[kb_id] if v.version == version.version]
        if not existing:
            self._versions[kb_id].insert(0, version)  # 최신 버전이 앞에

        return version

    async def find_by_kb_id(self, kb_id: str) -> List[KnowledgeBaseVersion]:
        """KB ID로 모든 버전 조회"""
        return self._versions.get(kb_id, [])

    async def find_by_kb_id_and_version(
        self, kb_id: str, version: int
    ) -> Optional[KnowledgeBaseVersion]:
        """KB ID와 버전 번호로 특정 버전 조회"""
        versions = self._versions.get(kb_id, [])
        for v in versions:
            if v.version == version:
                return v
        return None

    async def find_latest_by_kb_id(self, kb_id: str) -> Optional[KnowledgeBaseVersion]:
        """KB ID로 최신 버전 조회"""
        versions = self._versions.get(kb_id, [])
        return versions[0] if versions else None

    async def delete_by_kb_id(self, kb_id: str) -> None:
        """KB ID로 모든 버전 삭제"""
        if kb_id in self._versions:
            del self._versions[kb_id]
