"""Repository 테스트"""
import pytest
from ..domain.value_objects import MCPId


class TestMCPRepository:
    """MCP Repository 테스트"""
    
    @pytest.mark.asyncio
    async def test_save_mcp(self, memory_repository, sample_mcp_entity):
        """TC-REPO-001: MCP 저장"""
        await memory_repository.save(sample_mcp_entity)
        
        # 저장 확인
        saved_mcp = await memory_repository.find_by_id(sample_mcp_entity.id)
        assert saved_mcp is not None
        assert saved_mcp.id == sample_mcp_entity.id
    
    @pytest.mark.asyncio
    async def test_find_by_id_exists(self, memory_repository, sample_mcp_entity):
        """TC-REPO-002: MCP 조회 (ID) - 존재"""
        await memory_repository.save(sample_mcp_entity)
        
        found_mcp = await memory_repository.find_by_id(sample_mcp_entity.id)
        assert found_mcp is not None
        assert found_mcp.id == sample_mcp_entity.id
        assert found_mcp.name == sample_mcp_entity.name
    
    @pytest.mark.asyncio
    async def test_find_by_name_exists(self, memory_repository, sample_mcp_entity):
        """TC-REPO-003: MCP 조회 (이름) - 존재"""
        await memory_repository.save(sample_mcp_entity)
        
        found_mcp = await memory_repository.find_by_name(sample_mcp_entity.name)
        assert found_mcp is not None
        assert found_mcp.name == sample_mcp_entity.name
    
    @pytest.mark.asyncio
    async def test_find_by_id_not_exists(self, memory_repository):
        """TC-REPO-004: MCP 조회 (존재하지 않음)"""
        non_existent_id = MCPId("mcp-nonexistent")
        found_mcp = await memory_repository.find_by_id(non_existent_id)
        assert found_mcp is None
    
    @pytest.mark.asyncio
    async def test_find_all(self, memory_repository, sample_mcp_entity, sample_api_target):
        """TC-REPO-005: MCP 목록 조회"""
        # 첫 번째 MCP 저장
        await memory_repository.save(sample_mcp_entity)
        
        # 두 번째 MCP 생성 및 저장
        from ..domain.entities import InternalCreateMCP
        mcp2 = InternalCreateMCP(
            id=MCPId("mcp-test456"),
            name="another-mcp",
            description="또 다른 MCP",
            team_tag_ids=["team-b"],
            selected_api_targets=[sample_api_target]
        )
        await memory_repository.save(mcp2)
        
        # 전체 조회
        all_mcps = await memory_repository.find_all()
        assert len(all_mcps) == 2
        assert any(mcp.id == sample_mcp_entity.id for mcp in all_mcps)
        assert any(mcp.id == mcp2.id for mcp in all_mcps)
