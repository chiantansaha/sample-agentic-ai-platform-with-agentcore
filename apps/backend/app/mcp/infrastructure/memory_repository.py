"""In-Memory MCP Repository for Testing"""

from typing import List, Optional, Dict
from ..domain.entities import MCP
from ..domain.repositories import MCPRepository
from ..domain.value_objects import MCPId, Status, MCPType


class InMemoryMCPRepository(MCPRepository):
    """In-memory implementation of MCP repository for testing"""
    
    def __init__(self):
        self._mcps: Dict[str, MCP] = {}
    
    async def save(self, mcp: MCP) -> None:
        """Save MCP"""
        self._mcps[mcp.id.value] = mcp
    
    async def find_by_id(self, mcp_id: MCPId) -> Optional[MCP]:
        """Find MCP by ID"""
        return self._mcps.get(mcp_id.value)
    
    async def find_by_name(self, name: str) -> Optional[MCP]:
        """Find MCP by name"""
        for mcp in self._mcps.values():
            if mcp.name == name:
                return mcp
        return None
    
    async def find_all(self) -> List[MCP]:
        """Find all MCPs"""
        return list(self._mcps.values())
    
    async def find_by_status(self, status: Status) -> List[MCP]:
        """Find MCPs by status"""
        return [mcp for mcp in self._mcps.values() if mcp.status == status]
    
    async def find_by_type(self, mcp_type: MCPType) -> List[MCP]:
        """Find MCPs by type"""
        return [mcp for mcp in self._mcps.values() if mcp.type == mcp_type]
    
    async def delete(self, mcp_id: MCPId) -> None:
        """Delete MCP"""
        if mcp_id.value in self._mcps:
            del self._mcps[mcp_id.value]

    async def update_status(self, mcp_id: MCPId, status: Status) -> None:
        """MCP 상태만 업데이트 (부분 업데이트)"""
        mcp = self._mcps.get(mcp_id.value)
        if mcp:
            if status == Status.ENABLED:
                mcp.enable()
            else:
                mcp.disable()

    def clear(self) -> None:
        """Clear all MCPs (for testing)"""
        self._mcps.clear()
