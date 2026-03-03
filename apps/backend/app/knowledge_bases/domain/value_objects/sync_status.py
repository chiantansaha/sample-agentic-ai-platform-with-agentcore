"""Sync Status Value Object"""
from enum import Enum


class SyncStatus(Enum):
    """Sync 상태"""
    UPLOADED = "uploaded"  # 파일 업로드 완료, 인덱싱 대기 중
    PENDING = "pending"    # 인덱싱 시작 대기
    SYNCING = "syncing"    # 인덱싱 진행 중
    COMPLETED = "completed"  # 인덱싱 완료
    FAILED = "failed"      # 인덱싱 실패
