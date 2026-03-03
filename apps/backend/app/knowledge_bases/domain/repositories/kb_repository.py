"""KB Repository Interface"""
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple

from ..entities.knowledge_base import KnowledgeBase


class KBRepository(ABC):
    """KB Repository Interface"""
    
    @abstractmethod
    async def save(self, kb: KnowledgeBase) -> KnowledgeBase:
        pass
    
    @abstractmethod
    async def find_by_id(self, kb_id: str) -> Optional[KnowledgeBase]:
        pass
    
    @abstractmethod
    async def find_all(self, page: int = 1, page_size: int = 20) -> Tuple[List[KnowledgeBase], int]:
        pass
