"""MCP Version Repository Interface"""
from abc import ABC, abstractmethod
from typing import List, Optional
from ..value_objects import MCPVersion


class MCPVersionRepository(ABC):
    """MCP 버전 리포지토리 인터페이스"""

    @abstractmethod
    async def save(self, version: MCPVersion) -> None:
        """버전 저장"""
        pass

    @abstractmethod
    async def find_by_mcp_id(self, mcp_id: str) -> List[MCPVersion]:
        """MCP ID로 모든 버전 조회 (최신순)"""
        pass

    @abstractmethod
    async def find_by_mcp_id_and_version(self, mcp_id: str, version: str) -> Optional[MCPVersion]:
        """특정 MCP의 특정 버전 조회"""
        pass

    @abstractmethod
    async def get_latest_version(self, mcp_id: str) -> Optional[MCPVersion]:
        """MCP의 최신 버전 조회"""
        pass
