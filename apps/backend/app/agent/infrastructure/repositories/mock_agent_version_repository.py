"""Mock Agent Version Repository for Demo Mode"""
from typing import List, Optional, Dict

from ...domain.repositories import AgentVersionRepository
from ...domain.entities.agent_version import AgentVersion


class MockAgentVersionRepository(AgentVersionRepository):
    """Mock Agent Version Repository - 메모리 기반 데모용 구현"""

    def __init__(self):
        # agent_id -> [versions] (최신순)
        self._versions: Dict[str, List[AgentVersion]] = {}

    async def save(self, version: AgentVersion) -> AgentVersion:
        """버전 저장"""
        agent_id = version.agent_id
        if agent_id not in self._versions:
            self._versions[agent_id] = []

        # 중복 체크
        existing = [v for v in self._versions[agent_id] if v.version == version.version]
        if not existing:
            self._versions[agent_id].insert(0, version)  # 최신 버전이 앞에

        return version

    async def find_by_agent_id(self, agent_id: str) -> List[AgentVersion]:
        """Agent ID로 버전 목록 조회"""
        return self._versions.get(agent_id, [])

    async def find_latest_version(self, agent_id: str) -> Optional[AgentVersion]:
        """최신 버전 조회"""
        versions = self._versions.get(agent_id, [])
        return versions[0] if versions else None
