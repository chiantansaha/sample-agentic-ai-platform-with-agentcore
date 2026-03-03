"""Mock KB Repository for Demo Mode"""
from typing import Optional, List, Tuple, Dict, Any

from app.shared.mock_data import MOCK_KNOWLEDGE_BASES
from ...domain.repositories import KBRepository
from ...domain.entities.knowledge_base import KnowledgeBase
from ...domain.value_objects import KBId, KBStatus


class MockKBRepository(KBRepository):
    """Mock KB Repository - 메모리 기반 데모용 구현"""

    def __init__(self):
        # Mock 데이터를 메모리에 로드
        self._kbs: Dict[str, KnowledgeBase] = {}
        for kb_data in MOCK_KNOWLEDGE_BASES:
            kb = self._dict_to_kb(kb_data)
            self._kbs[kb.id.value] = kb

    def _dict_to_kb(self, data: Dict[str, Any]) -> KnowledgeBase:
        """Dict -> KnowledgeBase Entity 변환"""
        # Map mock status to KBStatus
        status_map = {
            "ready": KBStatus.ENABLED,
            "syncing": KBStatus.ENABLED,
            "failed": KBStatus.DISABLED,
            "enabled": KBStatus.ENABLED,
            "disabled": KBStatus.DISABLED
        }
        status = status_map.get(data.get("status", "ready"), KBStatus.ENABLED)

        # Map mock status to sync_status
        sync_status_map = {
            "ready": "completed",
            "syncing": "syncing",
            "failed": "failed"
        }
        sync_status = sync_status_map.get(data.get("status", "ready"), "completed")

        return KnowledgeBase(
            id=KBId(data["id"]),
            name=data["name"],
            description=data["description"],
            bedrock_kb_id=data.get("bedrock_kb_id", ""),
            s3_bucket=f"demo-kb-bucket",
            s3_prefix=f"kb-{data['id']}/",
            data_source_id=data.get("data_source_id", ""),
            status=status,
            sync_status=sync_status,
            team_tags=data.get("team_tags", []),
            current_version=int(data.get("current_version", "1.0.0").split(".")[0]) if isinstance(data.get("current_version"), str) else data.get("current_version", 1),
            created_at=data.get("created_at", 0),
            updated_at=data.get("updated_at", 0),
            created_by=data.get("created_by", "demo-user"),
            updated_by=data.get("updated_by", "demo-user")
        )

    async def save(self, kb: KnowledgeBase) -> KnowledgeBase:
        """KB 저장"""
        self._kbs[kb.id.value] = kb
        return kb

    async def find_by_id(self, kb_id: str) -> Optional[KnowledgeBase]:
        """ID로 KB 조회"""
        return self._kbs.get(kb_id)

    async def find_all(self, page: int = 1, page_size: int = 20) -> Tuple[List[KnowledgeBase], int]:
        """KB 목록 조회 (페이징)"""
        kbs = list(self._kbs.values())
        total = len(kbs)

        # 페이징
        start = (page - 1) * page_size
        end = start + page_size
        paged_kbs = kbs[start:end]

        return paged_kbs, total
