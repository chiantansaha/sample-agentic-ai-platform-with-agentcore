"""Agent Aggregate Root"""
from dataclasses import dataclass, field
from typing import List

from ..value_objects import AgentId, LLMModel, Instruction, Version, AgentStatus
from app.shared.utils.timestamp import now_timestamp


@dataclass
class Agent:
    """Agent Aggregate Root"""
    id: AgentId
    name: str
    description: str
    llm_model: LLMModel
    instruction: Instruction
    knowledge_bases: List[str] = field(default_factory=list)
    mcps: List[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.ENABLED
    current_version: Version = field(default_factory=lambda: Version(1, 0, 0))
    team_tags: List[str] = field(default_factory=list)
    created_at: int = field(default_factory=now_timestamp)
    updated_at: int = field(default_factory=now_timestamp)
    created_by: str = ""
    updated_by: str = ""
    
    # Domain Events
    _events: List = field(default_factory=list, init=False, repr=False)
    
    def update(self, name: str, description: str, llm_model: LLMModel,
               instruction: Instruction, knowledge_bases: List[str],
               mcps: List[str], team_tags: List[str], updated_by: str):
        """Agent 정보 업데이트"""
        self.name = name
        self.description = description
        self.llm_model = llm_model
        self.instruction = instruction
        self.knowledge_bases = knowledge_bases
        self.mcps = mcps
        self.team_tags = team_tags
        self.updated_by = updated_by
        self.updated_at = now_timestamp()

        # Draft 상태의 Agent를 편집하면 자동으로 enabled 상태로 변경
        if self.status == AgentStatus.DRAFT:
            self.status = AgentStatus.ENABLED
    
    def enable(self):
        """Agent 활성화"""
        if self.status == AgentStatus.ENABLED:
            return
        self.status = AgentStatus.ENABLED
        self.updated_at = now_timestamp()

    def disable(self):
        """Agent 비활성화"""
        if self.status == AgentStatus.DISABLED:
            return
        self.status = AgentStatus.DISABLED
        self.updated_at = now_timestamp()

    def increment_version(self, new_version: Version):
        """버전 증가"""
        self.current_version = new_version
        self.updated_at = now_timestamp()
