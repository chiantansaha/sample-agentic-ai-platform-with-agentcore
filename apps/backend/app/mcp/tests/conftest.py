"""Test Fixtures and Configuration"""
import pytest
from typing import Dict, Any, List
from ..dto.request import TargetInfo, CreateInternalCreateMCPRequest
from ..domain.value_objects import MCPId, APITarget, Status
from ..domain.entities import InternalCreateMCP
from ..infrastructure.memory_repository import InMemoryMCPRepository
from ..infrastructure.gateway_service_impl import BedrockGatewayService
from ..application.service import MCPApplicationService


# ==================== 실제 KEIS API 테스트 데이터 ====================

@pytest.fixture
def sample_openapi_schema() -> Dict[str, Any]:
    """실제 KEIS API OpenAPI Schema"""
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Flight Schedule API",
            "version": "1.0.0",
            "description": "AWS Flight Schedule API"
        },
        "paths": {
            "/flights/schedule": {
                "get": {
                    "summary": "Get flight schedule",
                    "description": "항공편 스케줄 조회",
                    "operationId": "getFlightSchedule",
                    "parameters": [
                        {
                            "name": "date",
                            "in": "query",
                            "required": True,
                            "description": "조회 날짜 (YYYY-MM-DD)",
                            "schema": {"type": "string", "format": "date"}
                        },
                        {
                            "name": "origin",
                            "in": "query",
                            "required": False,
                            "description": "출발지 공항 코드",
                            "schema": {"type": "string"}
                        },
                        {
                            "name": "destination",
                            "in": "query",
                            "required": False,
                            "description": "도착지 공항 코드",
                            "schema": {"type": "string"}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "flights": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "flightNumber": {"type": "string"},
                                                        "origin": {"type": "string"},
                                                        "destination": {"type": "string"},
                                                        "departureTime": {"type": "string"},
                                                        "arrivalTime": {"type": "string"}
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "400": {
                            "description": "Bad Request"
                        },
                        "500": {
                            "description": "Internal Server Error"
                        }
                    }
                }
            }
        }
    }


@pytest.fixture
def sample_target_info(sample_openapi_schema) -> TargetInfo:
    """실제 KEIS API Target 정보"""
    return TargetInfo(
        name="GetFlightSchedule",
        description="항공편 스케줄 조회 API",
        endpoint="https://api.example.aws/v1/flights/schedule",
        method="GET",
        openApiSchema=sample_openapi_schema
    )


@pytest.fixture
def sample_targets(sample_target_info) -> List[TargetInfo]:
    """여러 개의 Target 정보"""
    return [sample_target_info]


@pytest.fixture
def sample_create_request(sample_targets) -> CreateInternalCreateMCPRequest:
    """Internal Create MCP 생성 요청"""
    return CreateInternalCreateMCPRequest(
        name="flight-schedule-mcp",
        description="항공편 스케줄 조회 MCP",
        team_tags=["team-flight", "team-operations"],
        targets=sample_targets
    )


@pytest.fixture
def sample_api_target(sample_openapi_schema) -> APITarget:
    """Domain APITarget 객체"""
    return APITarget(
        id="api-001",
        name="GetFlightSchedule",
        api_id="flight-schedule-api",
        method="GET",
        auth_type="none",
        openapi_schema=sample_openapi_schema,
        endpoint="https://api.example.aws/v1/flights/schedule"
    )


@pytest.fixture
def sample_mcp_entity(sample_api_target) -> InternalCreateMCP:
    """InternalCreateMCP 엔티티"""
    mcp_id = MCPId("mcp-test123")
    return InternalCreateMCP(
        id=mcp_id,
        name="flight-schedule-mcp",
        description="항공편 스케줄 조회 MCP",
        team_tag_ids=["team-flight", "team-operations"],
        selected_api_targets=[sample_api_target],
        status=Status.DISABLED
    )


# ==================== Repository & Service Fixtures ====================

@pytest.fixture
def memory_repository():
    """In-Memory Repository"""
    return InMemoryMCPRepository()


@pytest.fixture
def gateway_service():
    """실제 Bedrock Gateway Service"""
    return BedrockGatewayService()


@pytest.fixture
def mcp_service(memory_repository, gateway_service):
    """MCP Application Service"""
    # ECR Service와 KEIS Service는 Mock 사용 (MCP 생성에 직접 사용 안함)
    from unittest.mock import Mock
    version_repository = Mock()
    ecr_service = Mock()
    keis_service = Mock()

    return MCPApplicationService(
        mcp_repository=memory_repository,
        version_repository=version_repository,
        gateway_service=gateway_service,
        ecr_service=ecr_service,
        keis_service=keis_service
    )


# ==================== 유효성 검증 테스트 데이터 ====================

@pytest.fixture
def invalid_mcp_names() -> List[str]:
    """잘못된 MCP 이름 목록"""
    return [
        "",  # 빈 문자열
        "a" * 65,  # 64자 초과
        "mcp@invalid",  # 특수문자 포함
        "mcp name",  # 공백 포함
        "123-mcp",  # 숫자로 시작 (허용되지만 테스트용)
        "mcp!@#$%",  # 여러 특수문자
    ]


@pytest.fixture
def valid_mcp_names() -> List[str]:
    """유효한 MCP 이름 목록"""
    return [
        "mcp-test",
        "my_mcp_123",
        "MCP-Test-123",
        "a",  # 최소 길이
        "a" * 64,  # 최대 길이
    ]


# ==================== API 테스트 데이터 ====================

@pytest.fixture
def api_create_request_payload(sample_openapi_schema) -> Dict[str, Any]:
    """API 생성 요청 페이로드"""
    return {
        "type": "internal-create",
        "name": "test-flight-mcp",
        "description": "테스트 항공편 MCP",
        "team_tags": ["team-test"],
        "targets": [
            {
                "name": "GetFlightSchedule",
                "description": "항공편 스케줄 조회",
                "endpoint": "https://api.example.aws/v1/flights/schedule",
                "method": "GET",
                "openapi_schema": sample_openapi_schema
            }
        ]
    }


@pytest.fixture
def api_status_toggle_payload() -> Dict[str, str]:
    """API 상태 토글 페이로드"""
    return {"status": "enabled"}
