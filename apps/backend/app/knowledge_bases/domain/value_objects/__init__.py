"""KB Value Objects - 메타정보만 관리"""
from dataclasses import dataclass
from enum import Enum
import uuid


@dataclass(frozen=True)
class KBId:
    """KB ID Value Object"""
    value: str

    @staticmethod
    def generate():
        return KBId(str(uuid.uuid4()))

    def __str__(self):
        return self.value


class KBStatus(str, Enum):
    """KB Status Enum"""
    CREATING = "creating"  # KB 생성 중 (OpenSearch 인덱스 전파 대기 포함)
    ENABLED = "enabled"
    DISABLED = "disabled"
    FAILED = "failed"  # KB 생성 실패


__all__ = ['KBId', 'KBStatus']
