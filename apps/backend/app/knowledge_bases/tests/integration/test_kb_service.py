"""KB Application Service 통합 테스트 - 메타정보만 관리"""
import pytest
from unittest.mock import AsyncMock

from ...application.service import KBApplicationService
from ...domain.entities.knowledge_base import KnowledgeBase
from ...domain.value_objects import KBId, KBStatus
from ...dto.request import CreateKBRequest, UpdateKBRequest
from ...exception.exceptions import KBNotFoundException


@pytest.fixture
def mock_kb_repository():
    """Mock KB Repository"""
    return AsyncMock()


@pytest.fixture
def kb_service(mock_kb_repository):
    """KB Service 인스턴스"""
    return KBApplicationService(mock_kb_repository)


@pytest.mark.asyncio
async def test_create_kb(kb_service, mock_kb_repository):
    """KB 메타정보 등록 테스트"""
    request = CreateKBRequest(
        name="Test KB",
        description="Test Description",
        knowledge_base_id="bedrock-kb-123",
        team_tags=[]
    )

    mock_kb_repository.save.return_value = KnowledgeBase(
        id=KBId.generate(),
        name=request.name,
        description=request.description,
        knowledge_base_id=request.knowledge_base_id
    )

    result = await kb_service.create_kb(request, "user-123")

    assert result.name == "Test KB"
    assert result.knowledge_base_id == "bedrock-kb-123"
    assert mock_kb_repository.save.called


@pytest.mark.asyncio
async def test_update_kb(kb_service, mock_kb_repository):
    """KB 메타정보 수정 테스트"""
    kb_id = "test-kb-id"

    kb = KnowledgeBase(
        id=KBId(kb_id),
        name="Test KB",
        description="Test",
        knowledge_base_id="bedrock-kb-123"
    )
    mock_kb_repository.find_by_id.return_value = kb
    mock_kb_repository.save.return_value = kb

    request = UpdateKBRequest(
        name="Updated KB",
        description="Updated Description"
    )

    result = await kb_service.update_kb(kb_id, request, "user-456")

    assert result.name == "Updated KB"
    assert mock_kb_repository.save.called


@pytest.mark.asyncio
async def test_get_kb_not_found(kb_service, mock_kb_repository):
    """KB 조회 실패 테스트"""
    mock_kb_repository.find_by_id.return_value = None
    
    with pytest.raises(KBNotFoundException):
        await kb_service.get_kb("non-existent-id")


@pytest.mark.asyncio
async def test_change_kb_status(kb_service, mock_kb_repository):
    """KB 상태 변경 테스트"""
    kb_id = "test-kb-id"
    
    kb = KnowledgeBase(
        id=KBId(kb_id),
        name="Test KB",
        description="Test",
        knowledge_base_id="bedrock-kb-123"
    )
    mock_kb_repository.find_by_id.return_value = kb
    mock_kb_repository.save.return_value = kb
    
    result = await kb_service.change_kb_status(kb_id, False)
    
    assert result.status == "disabled"
    assert mock_kb_repository.save.called


@pytest.mark.asyncio
async def test_list_kbs(kb_service, mock_kb_repository):
    """KB 목록 조회 테스트"""
    kbs = [
        KnowledgeBase(
            id=KBId.generate(),
            name="KB 1",
            description="Test",
            knowledge_base_id="bedrock-kb-1"
        ),
        KnowledgeBase(
            id=KBId.generate(),
            name="KB 2",
            description="Test",
            knowledge_base_id="bedrock-kb-2"
        )
    ]
    mock_kb_repository.find_all.return_value = (kbs, 2)
    
    result = await kb_service.list_kbs(1, 20)
    
    assert len(result.items) == 2
    assert result.total == 2
