"""Value Objects"""
from dataclasses import dataclass
from enum import Enum

from .agent_id import AgentId


@dataclass(frozen=True)
class LLMModel:
    """LLM Model Value Object"""
    model_id: str
    model_name: str
    provider: str


@dataclass(frozen=True)
class Instruction:
    """Instruction Value Object"""
    system_prompt: str
    temperature: float = 0.7
    max_tokens: int = 2000


@dataclass(frozen=True)
class Version:
    """Version Value Object (Semantic Versioning)"""
    major: int
    minor: int
    patch: int
    
    def __str__(self):
        return f"v{self.major}.{self.minor}.{self.patch}"
    
    def increment_minor(self):
        """마이너 버전 증가 (y가 9이면 major 증가: 1.9.0 → 2.0.0)"""
        if self.minor >= 9:
            return Version(self.major + 1, 0, 0)
        return Version(self.major, self.minor + 1, 0)
    
    def increment_major(self):
        """메이저 버전 증가"""
        return Version(self.major + 1, 0, 0)
    
    @staticmethod
    def from_string(version_str: str):
        """문자열에서 Version 생성 (예: 'v1.2.0')"""
        version_str = version_str.lstrip('v')
        parts = version_str.split('.')
        return Version(int(parts[0]), int(parts[1]), int(parts[2]))


class AgentStatus(str, Enum):
    """Agent Status Enum"""
    ENABLED = "enabled"
    DISABLED = "disabled"
    DRAFT = "draft"


__all__ = ['AgentId', 'LLMModel', 'Instruction', 'Version', 'AgentStatus']
