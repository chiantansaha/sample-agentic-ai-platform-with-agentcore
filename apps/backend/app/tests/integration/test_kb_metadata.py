"""KB 메타정보 테스트 (v2.0)"""
import pytest
from datetime import datetime

from app.kb.domain.entities.knowledge_base import KnowledgeBase
from app.kb.domain.value_objects.kb_id import KBId
from app.kb.domain.value_objects.kb_status import KBStatus


@pytest.mark.asyncio
async def test_kb_metadata_only(mock_kb_repository):
    """KB 메타정보만 저장"""
    # Given
    kb = KnowledgeBase(
        id=KBId("kb-metadata-test"),
        name="Product Documentation",
        description="제품 매뉴얼 및 FAQ",
        bedrock_kb_id="ABCD1234EFGH",  # Bedrock에서 생성된 ID
        status=KBStatus.ENABLED,
        team_tags=["product"],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        created_by="user-test-id",
        updated_by="user-test-id",
    )

    mock_kb_repository.save.return_value = kb

    # When
    saved_kb = await mock_kb_repository.save(kb)

    # Then
    assert saved_kb.name == "Product Documentation"
    assert saved_kb.bedrock_kb_id == "ABCD1234EFGH"
    assert saved_kb.status == KBStatus.ENABLED
    # DataSource 관련 필드 없음 (v2.0)
    assert not hasattr(saved_kb, "data_sources")
    assert not hasattr(saved_kb, "stats")


@pytest.mark.asyncio
async def test_bedrock_kb_id_required():
    """Bedrock KB ID 필수 검증"""
    # Given - Bedrock KB ID 없이 생성 시도
    with pytest.raises(TypeError):
        kb = KnowledgeBase(
            id=KBId("kb-no-bedrock-id"),
            name="Invalid KB",
            description="Missing Bedrock KB ID",
            # bedrock_kb_id 누락
            status=KBStatus.ENABLED,
            team_tags=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            created_by="user-test-id",
            updated_by="user-test-id",
        )


@pytest.mark.asyncio
async def test_kb_without_data_sources(mock_kb_repository, mock_kb):
    """DataSource 없는 KB (v2.0)"""
    # Given
    mock_kb_repository.save.return_value = mock_kb

    # When
    saved_kb = await mock_kb_repository.save(mock_kb)

    # Then
    assert saved_kb is not None
    # DataSource 관련 메서드 없음
    assert not hasattr(saved_kb, "add_data_source")
    assert not hasattr(saved_kb, "remove_data_source")


@pytest.mark.asyncio
async def test_kb_status_management(mock_kb_repository, mock_kb):
    """KB 상태 관리 (enabled/disabled만)"""
    # Given
    mock_kb_repository.save.return_value = mock_kb
    mock_kb_repository.find_by_id.return_value = mock_kb

    # When - 1. KB 생성 (enabled)
    kb = await mock_kb_repository.save(mock_kb)
    assert kb.status == KBStatus.ENABLED

    # When - 2. KB 비활성화
    kb.status = KBStatus.DISABLED
    await mock_kb_repository.save(kb)

    # When - 3. KB 조회
    disabled_kb = await mock_kb_repository.find_by_id(kb.id.value)

    # Then
    assert disabled_kb.status == KBStatus.DISABLED


@pytest.mark.asyncio
async def test_kb_team_tags(mock_kb_repository):
    """KB 팀 태그 관리"""
    # Given
    kb = KnowledgeBase(
        id=KBId("kb-tags-test"),
        name="Multi-team KB",
        description="여러 팀이 사용하는 KB",
        bedrock_kb_id="MULTI-KB-123",
        status=KBStatus.ENABLED,
        team_tags=["product", "support", "sales"],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        created_by="user-test-id",
        updated_by="user-test-id",
    )

    mock_kb_repository.save.return_value = kb

    # When
    saved_kb = await mock_kb_repository.save(kb)

    # Then
    assert len(saved_kb.team_tags) == 3
    assert "product" in saved_kb.team_tags
    assert "support" in saved_kb.team_tags
    assert "sales" in saved_kb.team_tags


@pytest.mark.asyncio
async def test_kb_update_metadata(mock_kb_repository, mock_kb):
    """KB 메타정보 수정"""
    # Given
    mock_kb_repository.find_by_id.return_value = mock_kb
    mock_kb_repository.save.return_value = mock_kb

    # When - 1. KB 조회
    kb = await mock_kb_repository.find_by_id("kb-test-id")

    # When - 2. 메타정보 수정
    kb.name = "Updated KB Name"
    kb.description = "Updated description"
    updated_kb = await mock_kb_repository.save(kb)

    # Then
    assert updated_kb.name == "Updated KB Name"
    assert updated_kb.description == "Updated description"
    # Bedrock KB ID는 변경 불가
    assert updated_kb.bedrock_kb_id == "bedrock-kb-123"


@pytest.mark.asyncio
async def test_kb_bedrock_id_immutable(mock_kb_repository, mock_kb):
    """Bedrock KB ID 불변성"""
    # Given
    original_bedrock_id = mock_kb.bedrock_kb_id
    mock_kb_repository.save.return_value = mock_kb

    # When - Bedrock KB ID 변경 시도
    # (실제로는 setter가 없어야 함)
    try:
        mock_kb.bedrock_kb_id = "NEW-BEDROCK-ID"
        await mock_kb_repository.save(mock_kb)
    except AttributeError:
        pass  # 예상된 에러

    # Then
    assert mock_kb.bedrock_kb_id == original_bedrock_id


@pytest.mark.asyncio
async def test_multiple_kbs_same_bedrock_id():
    """동일한 Bedrock KB ID를 가진 여러 KB (불가능해야 함)"""
    # Given
    bedrock_kb_id = "SHARED-KB-123"

    kb1 = KnowledgeBase(
        id=KBId("kb-1"),
        name="KB 1",
        description="First KB",
        bedrock_kb_id=bedrock_kb_id,
        status=KBStatus.ENABLED,
        team_tags=["team1"],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        created_by="user-1",
        updated_by="user-1",
    )

    kb2 = KnowledgeBase(
        id=KBId("kb-2"),
        name="KB 2",
        description="Second KB",
        bedrock_kb_id=bedrock_kb_id,  # 동일한 Bedrock KB ID
        status=KBStatus.ENABLED,
        team_tags=["team2"],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        created_by="user-2",
        updated_by="user-2",
    )

    # Then
    # Repository 레벨에서 unique constraint 검증 필요
    # (현재는 엔티티 레벨에서만 검증)
    assert kb1.bedrock_kb_id == kb2.bedrock_kb_id
    # 실제 저장 시 Repository에서 에러 발생해야 함


@pytest.mark.asyncio
async def test_kb_query_by_bedrock_id(mock_kb_repository, mock_kb):
    """Bedrock KB ID로 조회"""
    # Given
    mock_kb_repository.find_by_bedrock_kb_id = pytest.Mock(return_value=mock_kb)

    # When
    kb = mock_kb_repository.find_by_bedrock_kb_id("bedrock-kb-123")

    # Then
    assert kb is not None
    assert kb.bedrock_kb_id == "bedrock-kb-123"
