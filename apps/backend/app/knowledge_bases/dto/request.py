"""KB Request DTOs - 메타정보만 관리"""
from pydantic import BaseModel, Field
from typing import List, Optional


class CreateKBRequest(BaseModel):
    """KB 생성 요청

    Bedrock KB ID는 사용자가 Bedrock Console에서 KB를 생성한 후 입력합니다.
    """
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=500)
    knowledge_base_id: str = Field(..., description="Bedrock KB ID")
    team_tags: Optional[List[str]] = []


class UpdateKBRequest(BaseModel):
    """KB 수정 요청"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    team_tags: Optional[List[str]] = None


class KBStatusUpdate(BaseModel):
    """KB 상태 변경 요청"""
    enabled: bool
