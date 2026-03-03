"""KB Response DTOs"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class KBFileResponse(BaseModel):
    """KB 파일 응답"""
    name: str
    size: int
    content_type: str
    s3_key: str
    checksum: str
    uploaded_at: Optional[int] = None  # Unix timestamp (seconds)
    status: Optional[str] = "uploaded"  # uploaded, indexed, failed


class VersionChangesResponse(BaseModel):
    """버전 변경사항 응답"""
    added: List[str]
    deleted: List[str]
    modified: List[str]


class KBVersionResponse(BaseModel):
    """KB 버전 응답"""
    kb_id: str
    version: int
    files: List[KBFileResponse]
    change_log: str
    changes: VersionChangesResponse
    sync_status: str
    sync_job_id: Optional[str] = None
    sync_started_at: Optional[int] = None  # Unix timestamp (seconds)
    sync_completed_at: Optional[int] = None  # Unix timestamp (seconds)
    created_at: int  # Unix timestamp (seconds)
    created_by: str


class KBResponse(BaseModel):
    """KB 응답"""
    id: str
    name: str
    description: str
    knowledge_base_id: str  # Bedrock KB ID
    status: str
    team_tags: List[str]
    current_version: int
    file_count: Optional[int] = None
    sync_status: Optional[str] = None
    sync_started_at: Optional[int] = None  # Unix timestamp (seconds)
    sync_completed_at: Optional[int] = None  # Unix timestamp (seconds)
    created_at: int  # Unix timestamp (seconds)
    updated_at: int  # Unix timestamp (seconds)
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


class KBListResponse(BaseModel):
    """KB 목록 응답"""
    items: List[KBResponse]
    total: int
    page: int
    page_size: int


class KBFilesResponse(BaseModel):
    """KB 파일 목록 응답"""
    kb_id: str
    current_version: int
    files: List[KBFileResponse]
    total_size: int
    sync_status: Optional[str] = "unknown"  # uploaded, syncing, completed, failed


class KBVersionListResponse(BaseModel):
    """KB 버전 목록 응답"""
    kb_id: str
    current_version: int
    versions: List[KBVersionResponse]
    total: int
