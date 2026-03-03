"""Mock MCP Version Repository for Demo Mode"""
from typing import List, Optional, Dict

from ..domain.repositories import MCPVersionRepository
from ..domain.value_objects import MCPVersion


class MockMCPVersionRepository(MCPVersionRepository):
    """Mock MCP Version Repository - 메모리 기반 데모용 구현"""

    def __init__(self):
        # mcp_id -> [versions] (최신순)
        self._versions: Dict[str, List[MCPVersion]] = {}

    async def save(self, version: MCPVersion) -> None:
        """버전 저장"""
        mcp_id = version.mcp_id
        if mcp_id not in self._versions:
            self._versions[mcp_id] = []

        # 중복 체크
        existing = [v for v in self._versions[mcp_id] if v.version == version.version]
        if not existing:
            self._versions[mcp_id].insert(0, version)  # 최신 버전이 앞에

    async def find_by_mcp_id(self, mcp_id: str) -> List[MCPVersion]:
        """MCP ID로 모든 버전 조회 (최신순)"""
        return self._versions.get(mcp_id, [])

    async def find_by_mcp_id_and_version(self, mcp_id: str, version: str) -> Optional[MCPVersion]:
        """특정 MCP의 특정 버전 조회"""
        versions = self._versions.get(mcp_id, [])
        for v in versions:
            if v.version == version:
                return v
        return None

    async def get_latest_version(self, mcp_id: str) -> Optional[MCPVersion]:
        """MCP의 최신 버전 조회"""
        versions = self._versions.get(mcp_id, [])
        return versions[0] if versions else None
