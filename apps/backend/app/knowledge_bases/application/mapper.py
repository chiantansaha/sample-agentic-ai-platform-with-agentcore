"""KB Mapper - Entity <-> DTO 변환"""
from typing import List

from ..domain.entities.knowledge_base import KnowledgeBase
from ..domain.value_objects import KBId
from ..dto.request import CreateKBRequest
from ..dto.response import KBResponse


class KBMapper:
    """KB Entity와 DTO 간 변환"""

    @staticmethod
    def to_entity(request: CreateKBRequest, bedrock_kb_id: str, user_id: str) -> KnowledgeBase:
        """CreateKBRequest -> KnowledgeBase Entity (기존 방식)"""
        return KnowledgeBase(
            id=KBId.generate(),
            name=request.name,
            description=request.description,
            bedrock_kb_id=bedrock_kb_id,
            team_tags=request.team_tags or [],
            created_by=user_id,
            updated_by=user_id
        )
    
    @staticmethod
    def to_entity_for_creation(name: str, description: str, team_tags: List[str], user_id: str) -> KnowledgeBase:
        """파일 업로드를 통한 KB 생성"""
        return KnowledgeBase(
            id=KBId.generate(),
            name=name,
            description=description,
            team_tags=team_tags or [],
            created_by=user_id,
            updated_by=user_id
        )

    @staticmethod
    def to_response(kb: KnowledgeBase) -> KBResponse:
        """KnowledgeBase Entity -> KBResponse"""
        return KBResponse(
            id=kb.id.value,
            name=kb.name,
            description=kb.description,
            knowledge_base_id=kb.bedrock_kb_id,
            status=kb.status.value,
            team_tags=kb.team_tags,
            current_version=kb.current_version,
            sync_status=kb.sync_status,
            created_at=kb.created_at,
            updated_at=kb.updated_at,
            created_by=kb.created_by,
            updated_by=kb.updated_by
        )
