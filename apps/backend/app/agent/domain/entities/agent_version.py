"""Agent Version Entity"""
from dataclasses import dataclass

from ..value_objects import Version


@dataclass
class AgentVersion:
    """Agent Version Entity"""
    id: str  # UUID
    agent_id: str
    version: Version
    change_log: str
    snapshot: dict  # Agent 설정 스냅샷
    deployed_by: str
    deployed_at: int  # Unix timestamp (seconds)
