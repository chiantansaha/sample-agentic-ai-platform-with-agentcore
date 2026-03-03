"""Knowledge Base Aggregate Root - 파일 업로드 및 버전 관리"""
from dataclasses import dataclass, field
from typing import List, Optional

from ..value_objects import KBId, KBStatus
from app.shared.utils.timestamp import now_timestamp


@dataclass
class KnowledgeBase:
    """Knowledge Base Aggregate Root

    파일 업로드를 통한 KB 생성 및 버전 관리를 지원합니다.
    """
    id: KBId
    name: str
    description: str
    bedrock_kb_id: str = ""  # Bedrock KB ID (자동 생성)
    s3_bucket: str = ""
    s3_prefix: str = ""  # kb-{id}/
    data_source_id: str = ""  # Bedrock Data Source ID
    status: KBStatus = KBStatus.ENABLED
    sync_status: Optional[str] = None  # uploaded, syncing, completed, failed
    team_tags: List[str] = field(default_factory=list)
    current_version: int = 0
    created_at: int = field(default_factory=now_timestamp)
    updated_at: int = field(default_factory=now_timestamp)
    created_by: str = ""
    updated_by: str = ""

    def enable(self):
        """KB 활성화"""
        if self.status == KBStatus.ENABLED:
            return
        self.status = KBStatus.ENABLED
        self.updated_at = now_timestamp()

    def disable(self):
        """KB 비활성화"""
        if self.status == KBStatus.DISABLED:
            return
        self.status = KBStatus.DISABLED
        self.updated_at = now_timestamp()

    def update(self, name: str = None, description: str = None, team_tags: List[str] = None, user_id: str = None):
        """KB 메타정보 업데이트"""
        if name:
            self.name = name
        if description:
            self.description = description
        if team_tags is not None:
            self.team_tags = team_tags
        if user_id:
            self.updated_by = user_id
        self.updated_at = now_timestamp()

    def increment_version(self):
        """버전 증가"""
        self.current_version += 1
        self.updated_at = now_timestamp()

    def set_bedrock_info(self, bedrock_kb_id: str, s3_bucket: str, s3_prefix: str, data_source_id: str):
        """Bedrock 정보 설정"""
        self.bedrock_kb_id = bedrock_kb_id
        self.s3_bucket = s3_bucket
        self.s3_prefix = s3_prefix
        self.data_source_id = data_source_id
        self.updated_at = now_timestamp()

