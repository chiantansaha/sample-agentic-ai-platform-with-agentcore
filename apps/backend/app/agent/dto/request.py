"""Request DTOs"""
from pydantic import BaseModel, Field
from typing import List, Optional


class CreateAgentRequest(BaseModel):
    """Agent 생성 요청"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=500)
    llm_model_id: str
    llm_model_name: str
    llm_provider: str
    system_prompt: str
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    max_tokens: int = Field(default=2000, ge=1, le=4096)
    knowledge_bases: Optional[List[str]] = []
    mcps: Optional[List[str]] = []
    team_tags: Optional[List[str]] = []


class UpdateAgentRequest(BaseModel):
    """Agent 수정 요청"""
    name: str
    description: str
    llm_model_id: str
    llm_model_name: str
    llm_provider: str
    system_prompt: str
    temperature: float
    max_tokens: int
    knowledge_bases: List[str]
    mcps: List[str]
    team_tags: Optional[List[str]] = []


class AgentStatusUpdate(BaseModel):
    """Agent 상태 변경 요청"""
    enabled: bool


class DeployDraftAgentRequest(BaseModel):
    """Draft Agent 배포 요청 (Agent Edit/Create 테스트용)"""
    agent_id: Optional[str] = None  # Edit 모드에서는 agent_id 있음
    name: str
    description: str
    llm_model_id: str
    llm_model_name: str
    llm_provider: str
    system_prompt: str
    temperature: float = 0.7
    max_tokens: int = 2000
    knowledge_bases: List[str] = []
    mcps: List[str] = []
    force_rebuild: bool = False
