"""PlaygroundSession Repository Interface"""
from abc import ABC, abstractmethod
from typing import Optional, List

from ..entities.session import PlaygroundSession


class SessionRepository(ABC):
    """Session Repository Interface"""
    
    @abstractmethod
    async def save(self, session: PlaygroundSession) -> PlaygroundSession:
        pass
    
    @abstractmethod
    async def find_by_id(self, session_id: str) -> Optional[PlaygroundSession]:
        pass
    
    @abstractmethod
    async def find_by_user(self, user_id: str) -> List[PlaygroundSession]:
        pass
