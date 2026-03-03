"""Version Changes Value Object"""
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class VersionChanges:
    """버전 변경 내역 Value Object"""
    added: List[str]
    deleted: List[str]
    modified: List[str]
