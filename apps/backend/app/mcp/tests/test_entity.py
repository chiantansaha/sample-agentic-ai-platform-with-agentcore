"""Domain Entity 테스트"""
import pytest
from ..domain.entities import InternalCreateMCP
from ..domain.value_objects import MCPId, Status


class TestInternalCreateMCP:
    """InternalCreateMCP 엔티티 테스트"""
    
    def test_create_entity(self, sample_mcp_entity):
        """TC-ENTITY-001: InternalCreateMCP 생성"""
        assert sample_mcp_entity.id.value == "mcp-test123"
        assert sample_mcp_entity.name == "flight-schedule-mcp"
        assert sample_mcp_entity.description == "항공편 스케줄 조회 MCP"
        assert sample_mcp_entity.status == Status.DISABLED
        assert len(sample_mcp_entity.selected_api_targets) == 1
        assert sample_mcp_entity.endpoint == ""
    
    def test_enable_mcp(self, sample_mcp_entity):
        """TC-ENTITY-002: MCP 상태 변경 (Enable)"""
        sample_mcp_entity.enable()
        assert sample_mcp_entity.status == Status.ENABLED
    
    def test_disable_mcp(self, sample_mcp_entity):
        """TC-ENTITY-002: MCP 상태 변경 (Disable)"""
        sample_mcp_entity.enable()
        sample_mcp_entity.disable()
        assert sample_mcp_entity.status == Status.DISABLED
    
    def test_set_endpoint(self, sample_mcp_entity):
        """TC-ENTITY-003: MCP 엔드포인트 설정"""
        gateway_url = "https://gw-12345678.gateway.bedrock-agentcore.ap-northeast-2.amazonaws.com/mcp"
        sample_mcp_entity.set_endpoint(gateway_url)
        assert sample_mcp_entity.endpoint == gateway_url
    
    def test_validate_configuration_valid(self, sample_mcp_entity):
        """TC-ENTITY-004: MCP 설정 검증 (유효)"""
        assert sample_mcp_entity.validate_configuration() is True
    
    def test_validate_configuration_no_targets(self, sample_api_target):
        """TC-ENTITY-004: MCP 설정 검증 (Target 없음)"""
        mcp = InternalCreateMCP(
            id=MCPId("mcp-test"),
            name="test-mcp",
            description="테스트",
            team_tag_ids=["team-a"],
            selected_api_targets=[]  # 빈 targets
        )
        assert mcp.validate_configuration() is False
