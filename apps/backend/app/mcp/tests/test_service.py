"""Application Service 테스트"""
import pytest
from ..exception.exceptions import MCPAlreadyExistsException, MCPNotFoundException


class TestMCPApplicationService:
    """MCP Application Service 테스트"""
    
    @pytest.mark.asyncio
    async def test_create_internal_create_mcp_success(self, mcp_service, sample_create_request):
        """TC-SERVICE-001: Internal Create MCP 생성 (정상)"""
        response = await mcp_service.create_internal_create_mcp(sample_create_request)
        
        # 응답 검증
        assert response.id is not None
        assert response.name == sample_create_request.name
        assert response.description == sample_create_request.description
        assert response.type == "internal-create"
        assert response.status == "enabled"  # 기본 상태는 enabled
        assert response.endpoint is not None  # Gateway 생성 후 엔드포인트 설정됨
        
        # Repository에 저장 확인
        saved_mcp = await mcp_service.mcp_repository.find_by_name(sample_create_request.name)
        assert saved_mcp is not None
    
    @pytest.mark.asyncio
    async def test_create_internal_create_mcp_duplicate_name(self, mcp_service, sample_create_request):
        """TC-SERVICE-002: Internal Create MCP 생성 (중복 이름)"""
        # 첫 번째 생성
        await mcp_service.create_internal_create_mcp(sample_create_request)
        
        # 중복 생성 시도
        with pytest.raises(MCPAlreadyExistsException):
            await mcp_service.create_internal_create_mcp(sample_create_request)
    
    @pytest.mark.asyncio
    async def test_list_mcps(self, mcp_service, sample_create_request):
        """TC-SERVICE-003: MCP 목록 조회"""
        # MCP 생성
        await mcp_service.create_internal_create_mcp(sample_create_request)
        
        # 목록 조회
        response = await mcp_service.list_mcps()
        
        assert response.total >= 1
        assert len(response.data) >= 1
        assert any(mcp.name == sample_create_request.name for mcp in response.data)
    
    @pytest.mark.asyncio
    async def test_get_mcp_success(self, mcp_service, sample_create_request):
        """TC-SERVICE-004: MCP 상세 조회 (정상)"""
        # MCP 생성
        created = await mcp_service.create_internal_create_mcp(sample_create_request)
        
        # 상세 조회
        response = await mcp_service.get_mcp(created.id)
        
        assert response.id == created.id
        assert response.name == sample_create_request.name
        assert response.description == sample_create_request.description
    
    @pytest.mark.asyncio
    async def test_get_mcp_not_found(self, mcp_service):
        """TC-SERVICE-005: MCP 상세 조회 (존재하지 않음)"""
        with pytest.raises(MCPNotFoundException):
            await mcp_service.get_mcp("mcp-nonexistent")
    
    @pytest.mark.asyncio
    async def test_toggle_mcp_status_enable(self, mcp_service, sample_create_request):
        """TC-SERVICE-006: MCP 상태 토글 (Enable)"""
        # MCP 생성 (기본 상태: enabled)
        created = await mcp_service.create_internal_create_mcp(sample_create_request)
        mcp_id_str = created.id  # 이미 문자열
        
        # 먼저 Disable
        from ..dto.request import MCPStatusRequest
        await mcp_service.toggle_mcp_status(mcp_id_str, MCPStatusRequest(status="disabled"))
        
        # 다시 Enable
        status_request = MCPStatusRequest(status="enabled")
        response = await mcp_service.toggle_mcp_status(mcp_id_str, status_request)
        
        assert response.status == "enabled"
        
        # Repository에서 확인
        from ..domain.value_objects import MCPId
        mcp = await mcp_service.mcp_repository.find_by_id(MCPId(mcp_id_str))
        assert mcp.status.value == "enabled"
    
    @pytest.mark.asyncio
    async def test_toggle_mcp_status_disable(self, mcp_service, sample_create_request):
        """TC-SERVICE-007: MCP 상태 토글 (Disable)"""
        # MCP 생성 (기본 상태: enabled)
        created = await mcp_service.create_internal_create_mcp(sample_create_request)
        mcp_id_str = created.id  # 이미 문자열
        
        # Disable
        from ..dto.request import MCPStatusRequest
        status_request = MCPStatusRequest(status="disabled")
        response = await mcp_service.toggle_mcp_status(mcp_id_str, status_request)
        
        assert response.status == "disabled"
        
        # Repository에서 확인
        from ..domain.value_objects import MCPId
        mcp = await mcp_service.mcp_repository.find_by_id(MCPId(mcp_id_str))
        assert mcp.status.value == "disabled"
