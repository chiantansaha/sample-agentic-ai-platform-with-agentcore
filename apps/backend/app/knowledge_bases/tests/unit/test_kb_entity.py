"""KB Entity 단위 테스트 - 메타정보만 관리"""
import pytest

from ...domain.entities.knowledge_base import KnowledgeBase
from ...domain.value_objects import KBId, KBStatus


def test_kb_creation():
    """KB 생성 테스트"""
    kb = KnowledgeBase(
        id=KBId.generate(),
        name="Test KB",
        description="Test Description",
        knowledge_base_id="bedrock-kb-123"
    )

    assert kb.name == "Test KB"
    assert kb.description == "Test Description"
    assert kb.knowledge_base_id == "bedrock-kb-123"
    assert kb.status == KBStatus.ENABLED


def test_kb_enable_disable():
    """KB 활성화/비활성화 테스트"""
    kb = KnowledgeBase(
        id=KBId.generate(),
        name="Test KB",
        description="Test",
        knowledge_base_id="bedrock-kb-123"
    )

    assert kb.status == KBStatus.ENABLED

    kb.disable()
    assert kb.status == KBStatus.DISABLED

    kb.enable()
    assert kb.status == KBStatus.ENABLED


def test_kb_update():
    """KB 메타정보 업데이트 테스트"""
    kb = KnowledgeBase(
        id=KBId.generate(),
        name="Test KB",
        description="Test",
        knowledge_base_id="bedrock-kb-123",
        created_by="user-1"
    )

    original_updated_at = kb.updated_at

    kb.update(name="Updated KB", description="Updated Description", user_id="user-2")

    assert kb.name == "Updated KB"
    assert kb.description == "Updated Description"
    assert kb.updated_by == "user-2"
    assert kb.updated_at > original_updated_at
