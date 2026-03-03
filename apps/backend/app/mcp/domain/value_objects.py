"""MCP Domain Value Objects"""
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


class MCPType(Enum):
    """MCP 타입"""
    EXTERNAL = "external"
    INTERNAL_DEPLOY = "internal-deploy"
    INTERNAL_CREATE = "internal-create"


class Status(Enum):
    """MCP 상태"""
    ENABLED = "enabled"
    DISABLED = "disabled"


class ExternalAuthType(Enum):
    """External MCP 인증 타입"""
    NO_AUTH = "no_auth"  # 공용 Cognito 사용
    OAUTH = "oauth"  # 사용자 선택 User Pool


@dataclass(frozen=True)
class MCPId:
    """MCP 고유 식별자"""
    value: str
    
    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("MCP ID cannot be empty")


@dataclass(frozen=True)
class ToolEndpoint:
    """Tool의 개별 endpoint 정보

    하나의 OpenAPI Schema에 여러 paths가 있을 때 각 endpoint 정보를 담습니다.
    """
    method: str  # HTTP method (GET, POST, etc.)
    path: str  # API path (/reference-data/locations)
    summary: str  # Endpoint 요약 설명
    input_schema: Dict[str, Any]  # 해당 endpoint의 parameters (JSON Schema)
    responses: Optional[Dict[str, Any]] = None  # OpenAPI responses schema


@dataclass(frozen=True)
class Tool:
    """MCP 도구 정보 (MCP Protocol 표준)

    MCP Protocol Specification:
    - name: 도구의 고유 식별자 (unique identifier)
    - description: 도구 설명
    - inputSchema: JSON Schema 형식의 입력 파라미터
    - endpoints: 여러 endpoint 정보 (하나의 API에 여러 paths가 있을 때)
    - responses: OpenAPI 응답 스키마 (optional, for UI display)
    - method: HTTP method (optional, for UI display)
    - endpoint: API endpoint base URL (optional, for UI display)
    - auth_type: Authentication type (optional, for UI display)

    Reference: https://spec.modelcontextprotocol.io/specification/server/tools/
    """
    name: str
    description: str
    input_schema: Dict[str, Any]  # Python naming convention (MCP Protocol: inputSchema)
    endpoints: Optional[List['ToolEndpoint']] = None  # 여러 endpoint 정보
    responses: Optional[Dict[str, Any]] = None  # OpenAPI responses schema (첫 번째 endpoint 기준)
    method: Optional[str] = None  # HTTP method (GET, POST, etc.) - 첫 번째 endpoint 기준
    endpoint: Optional[str] = None  # API endpoint base URL
    auth_type: Optional[str] = None  # Authentication type (oauth, api_key, none)


@dataclass(frozen=True)
class AuthConfig:
    """인증 설정"""
    type: str  # "oauth" | "api_key" | "none"
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    token_url: Optional[str] = None
    api_key: Optional[str] = None  # Smithery API key


@dataclass(frozen=True)
class DeploymentConfig:
    """배포 설정"""
    resources: Dict[str, Any]
    environment: Dict[str, str]


@dataclass(frozen=True)
class APITarget:
    """API 타겟 정보"""
    id: str
    name: str
    api_id: str
    method: str
    auth_type: str
    openapi_schema: Optional[Dict[str, Any]] = None  # OpenAPI 3.0 Schema for Gateway Target
    endpoint: Optional[str] = None  # openapi_schema.servers[0].url에서 추출 가능
    team_tag_ids: Optional[List[str]] = None  # Team Tag IDs


@dataclass(frozen=True)
class MCPVersion:
    """MCP 버전 정보"""
    mcp_id: str
    version: str
    endpoint: str
    description: str
    change_log: str
    status: Status
    tool_list: List[Tool]
    created_at: int  # Unix timestamp (seconds)
    created_by: str

    # MCP configuration snapshot
    mcp_type: MCPType
    team_tag_ids: List[str]

    # Type-specific configuration
    server_url: Optional[str] = None  # External MCP
    auth_config: Optional[AuthConfig] = None  # External MCP with OAuth
    ecr_repository: Optional[str] = None  # Internal Deploy
    image_tag: Optional[str] = None  # Internal Deploy
    targets: Optional[List[APITarget]] = None  # Internal Create
