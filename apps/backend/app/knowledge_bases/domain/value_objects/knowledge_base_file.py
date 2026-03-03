"""Knowledge Base File Value Object"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class KnowledgeBaseFile:
    """파일 정보 Value Object"""
    name: str
    size: int
    content_type: str
    s3_key: str
    checksum: str
    uploaded_at: Optional[int] = None  # Unix timestamp (seconds)
    status: Optional[str] = "uploaded"  # uploaded, indexed, failed
