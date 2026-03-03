"""Agent Version Repository Interface"""
from abc import ABC, abstractmethod
from typing import List, Optional

from ..entities.agent_version import AgentVersion


class AgentVersionRepository(ABC):
    """Agent Version Repository Interface"""
    
    @abstractmethod
    async def save(self, version: AgentVersion) -> AgentVersion:
        """버전 저장"""
        pass
    
    @abstractmethod
    async def find_by_agent_id(self, agent_id: str) -> List[AgentVersion]:
        """Agent ID로 버전 목록 조회"""
        pass
    
    @abstractmethod
    async def find_latest_version(self, agent_id: str) -> Optional[AgentVersion]:
        """최신 버전 조회"""
        pass
