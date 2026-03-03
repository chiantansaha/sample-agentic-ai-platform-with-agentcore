"""MCP Domain Repositories"""
from abc import ABC, abstractmethod
from typing import List, Optional
from ..entities import MCP
from ..value_objects import MCPId, Status, MCPType


class MCPRepository(ABC):
    """MCP 리포지토리 인터페이스"""
    
    @abstractmethod
    async def save(self, mcp: MCP) -> None:
        """MCP 저장"""
        pass
    
    @abstractmethod
    async def find_by_id(self, mcp_id: MCPId) -> Optional[MCP]:
        """ID로 MCP 조회"""
        pass
    
    @abstractmethod
    async def find_all(self) -> List[MCP]:
        """모든 MCP 조회"""
        pass
    
    @abstractmethod
    async def find_by_status(self, status: Status) -> List[MCP]:
        """상태별 MCP 조회"""
        pass
    
    @abstractmethod
    async def find_by_type(self, mcp_type: MCPType) -> List[MCP]:
        """타입별 MCP 조회"""
        pass
    
    @abstractmethod
    async def find_by_name(self, name: str) -> Optional[MCP]:
        """이름으로 MCP 조회"""
        pass
    
    @abstractmethod
    async def delete(self, mcp_id: MCPId) -> None:
        """MCP 삭제 (실제로는 사용하지 않음)"""
        pass

    @abstractmethod
    async def update_status(self, mcp_id: MCPId, status: Status) -> None:
        """MCP 상태만 업데이트 (부분 업데이트)"""
        pass
