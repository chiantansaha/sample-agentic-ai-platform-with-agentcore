"""Knowledge Base Version Entity 단위 테스트"""
import pytest
from datetime import datetime

from app.knowledge_bases.domain.entities.knowledge_base_version import KnowledgeBaseVersion
from app.knowledge_bases.domain.value_objects.knowledge_base_file import KnowledgeBaseFile
from app.knowledge_bases.domain.value_objects.version_changes import VersionChanges
from app.knowledge_bases.domain.value_objects.sync_status import SyncStatus


def test_create_version():
    """버전 생성 테스트"""
    files = [
        KnowledgeBaseFile(
            name="doc1.md",
            size=1024,
            content_type="text/markdown",
            s3_key="kb-123/v1/doc1.md",
            checksum="abc123"
        )
    ]
    
    changes = VersionChanges(added=["doc1.md"], deleted=[], modified=[])
    
    version = KnowledgeBaseVersion(
        kb_id="kb-123",
        version=1,
        files=files,
        change_log="Initial creation",
        changes=changes,
        created_by="user-123"
    )
    
    assert version.kb_id == "kb-123"
    assert version.version == 1
    assert len(version.files) == 1
    assert version.sync_status == SyncStatus.PENDING


def test_start_sync():
    """Sync 시작 테스트"""
    version = KnowledgeBaseVersion(
        kb_id="kb-123",
        version=1,
        files=[],
        change_log="Test",
        changes=VersionChanges([], [], []),
        created_by="user-123"
    )
    
    version.start_sync("job-123")
    
    assert version.sync_status == SyncStatus.SYNCING
    assert version.sync_job_id == "job-123"
    assert version.sync_started_at is not None


def test_complete_sync():
    """Sync 완료 테스트"""
    version = KnowledgeBaseVersion(
        kb_id="kb-123",
        version=1,
        files=[],
        change_log="Test",
        changes=VersionChanges([], [], []),
        created_by="user-123"
    )
    
    version.start_sync("job-123")
    version.complete_sync()
    
    assert version.sync_status == SyncStatus.COMPLETED
    assert version.sync_completed_at is not None


def test_fail_sync():
    """Sync 실패 테스트"""
    version = KnowledgeBaseVersion(
        kb_id="kb-123",
        version=1,
        files=[],
        change_log="Test",
        changes=VersionChanges([], [], []),
        created_by="user-123"
    )
    
    version.start_sync("job-123")
    version.fail_sync()
    
    assert version.sync_status == SyncStatus.FAILED
    assert version.sync_completed_at is not None
