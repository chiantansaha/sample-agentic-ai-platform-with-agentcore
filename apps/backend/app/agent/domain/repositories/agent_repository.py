"""Agent Repository Interface"""
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple

from ..entities import Agent


class AgentRepository(ABC):
    """Agent Repository Interface"""
    
    @abstractmethod
    async def save(self, agent: Agent) -> Agent:
        """Agent 저장"""
        pass
    
    @abstractmethod
    async def find_by_id(self, agent_id: str) -> Optional[Agent]:
        """ID로 Agent 조회"""
        pass
    
    @abstractmethod
    async def find_all(self, page: int = 1, page_size: int = 20) -> Tuple[List[Agent], int]:
        """Agent 목록 조회 (페이징)
        
        Returns:
            Tuple[List[Agent], int]: (agents, total_count)
        """
        pass
    
    @abstractmethod
    async def find_enabled_agents(self) -> List[Agent]:
        """활성화된 Agent 목록 조회"""
        pass
