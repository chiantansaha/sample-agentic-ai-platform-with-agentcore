"""Response DTOs"""
from pydantic import BaseModel, field_validator
from typing import List, Dict, Any, Optional


class ResourceInfo(BaseModel):
    """리소스 정보 (ID + 이름)"""
    id: str
    name: str


class AgentResponse(BaseModel):
    """Agent 응답"""
    id: str
    name: str
    description: str
    llm_model: Dict[str, str]
    instruction: Dict
    knowledge_bases: List[ResourceInfo]
    mcps: List[ResourceInfo]
    status: str
    current_version: str
    team_tags: List[str]
    created_at: int  # Unix timestamp (seconds)
    updated_at: int  # Unix timestamp (seconds)

    @field_validator('current_version', mode='before')
    @classmethod
    def validate_current_version(cls, v: Any) -> str:
        """Version 객체를 문자열로 변환"""
        if isinstance(v, str):
            return v
        if hasattr(v, '__str__'):
            return str(v)
        if isinstance(v, dict) and 'major' in v:
            return f"v{v['major']}.{v['minor']}.{v['patch']}"
        return str(v)


class AgentListResponse(BaseModel):
    """Agent 목록 응답"""
    items: List[AgentResponse]
    total: int
    page: int
    page_size: int
