"""Agent ID Value Object"""
from dataclasses import dataclass
import uuid


@dataclass(frozen=True)
class AgentId:
    """Agent ID Value Object"""
    value: str
    
    @staticmethod
    def generate():
        """새 Agent ID 생성"""
        return AgentId(str(uuid.uuid4()))
    
    def __str__(self):
        return self.value
