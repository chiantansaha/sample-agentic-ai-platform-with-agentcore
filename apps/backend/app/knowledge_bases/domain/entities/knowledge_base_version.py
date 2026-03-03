"""Knowledge Base Version Entity"""
from dataclasses import dataclass, field
from typing import List, Optional

from app.shared.utils.timestamp import now_timestamp
from ..value_objects.knowledge_base_file import KnowledgeBaseFile
from ..value_objects.version_changes import VersionChanges
from ..value_objects.sync_status import SyncStatus


@dataclass
class KnowledgeBaseVersion:
    """Knowledge Base 버전 Entity"""
    kb_id: str
    version: int
    files: List[KnowledgeBaseFile]
    change_log: str
    changes: VersionChanges
    sync_status: SyncStatus = SyncStatus.PENDING
    sync_job_id: str = ""
    sync_started_at: Optional[int] = None  # Unix timestamp (seconds)
    sync_completed_at: Optional[int] = None  # Unix timestamp (seconds)
    created_by: str = ""
    created_at: int = field(default_factory=now_timestamp)  # Unix timestamp (seconds)

    def start_sync(self, job_id: str):
        """Sync 시작"""
        self.sync_status = SyncStatus.SYNCING
        self.sync_job_id = job_id
        self.sync_started_at = now_timestamp()

    def complete_sync(self):
        """Sync 완료"""
        self.sync_status = SyncStatus.COMPLETED
        self.sync_completed_at = now_timestamp()

    def fail_sync(self):
        """Sync 실패"""
        self.sync_status = SyncStatus.FAILED
        self.sync_completed_at = now_timestamp()
