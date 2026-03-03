"""DTO 검증 테스트"""
import pytest
from ..dto.request import TargetInfo, CreateInternalCreateMCPRequest


class TestTargetInfo:
    """TargetInfo 테스트"""
    
    def test_create_target_info(self, sample_target_info):
        """TC-DTO-001: TargetInfo 생성 검증"""
        assert sample_target_info.name == "GetFlightSchedule"
        assert sample_target_info.description == "항공편 스케줄 조회 API"
        assert sample_target_info.endpoint == "https://api.example.aws/v1/flights/schedule"
        assert sample_target_info.method == "GET"
        assert sample_target_info.openApiSchema is not None
        assert "openapi" in sample_target_info.openApiSchema


class TestCreateInternalCreateMCPRequest:
    """CreateInternalCreateMCPRequest 테스트"""
    
    def test_create_request_valid(self, sample_create_request):
        """TC-DTO-002: CreateInternalCreateMCPRequest 검증 (정상)"""
        assert sample_create_request.name == "flight-schedule-mcp"
        assert sample_create_request.description == "항공편 스케줄 조회 MCP"
        assert len(sample_create_request.team_tags) == 2
        assert len(sample_create_request.targets) == 1
    
    def test_create_request_name_too_long(self, sample_targets):
        """TC-DTO-003: CreateInternalCreateMCPRequest 검증 (이름 길이 초과)"""
        with pytest.raises(ValueError, match="must be between 1 and 64 characters"):
            CreateInternalCreateMCPRequest(
                name="a" * 65,
                description="테스트",
                team_tags=["team-a"],
                targets=sample_targets
            )
    
    def test_create_request_invalid_characters(self, sample_targets):
        """TC-DTO-004: CreateInternalCreateMCPRequest 검증 (잘못된 문자)"""
        with pytest.raises(ValueError, match="can only use letters, numbers, hyphens"):
            CreateInternalCreateMCPRequest(
                name="mcp@invalid!",
                description="테스트",
                team_tags=["team-a"],
                targets=sample_targets
            )
    
    def test_create_request_empty_name(self, sample_targets):
        """TC-DTO-005: CreateInternalCreateMCPRequest 검증 (빈 이름)"""
        with pytest.raises(ValueError, match="must be between 1 and 64 characters"):
            CreateInternalCreateMCPRequest(
                name="",
                description="테스트",
                team_tags=["team-a"],
                targets=sample_targets
            )
    
    def test_create_request_valid_names(self, valid_mcp_names, sample_targets):
        """유효한 MCP 이름들 검증"""
        for name in valid_mcp_names:
            request = CreateInternalCreateMCPRequest(
                name=name,
                description="테스트",
                team_tags=["team-a"],
                targets=sample_targets
            )
            assert request.name == name
