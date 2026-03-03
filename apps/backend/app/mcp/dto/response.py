"""MCP Response DTOs"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class ToolEndpointResponse:
    """Tool의 개별 endpoint 응답

    하나의 OpenAPI Schema에 여러 paths가 있을 때 각 endpoint 정보를 담습니다.
    """
    method: str  # HTTP method (GET, POST, etc.)
    path: str  # API path (/reference-data/locations)
    summary: str  # Endpoint 요약 설명
    inputSchema: Dict[str, Any]  # 해당 endpoint의 parameters (JSON Schema) - camelCase
    responses: Optional[Dict[str, Any]] = None  # OpenAPI responses schema


@dataclass
class ToolResponse:
    """도구 응답 (MCP Protocol 표준)

    MCP Protocol Specification:
    - name: 도구의 고유 식별자
    - description: 도구 설명
    - inputSchema: JSON Schema 형식의 입력 파라미터 (camelCase for API response)
    - endpoints: 여러 endpoint 정보 (하나의 API에 여러 paths가 있을 때)
    - responses: OpenAPI 응답 스키마 (optional, for UI display) - 첫 번째 endpoint 기준
    - method: HTTP method (optional, for UI display) - 첫 번째 endpoint 기준
    - endpoint: API endpoint (optional, for UI display)
    - authType: Authentication type (optional, for UI display)
    """
    name: str
    description: str
    inputSchema: Dict[str, Any]  # API 응답은 camelCase 사용
    endpoints: Optional[List[ToolEndpointResponse]] = None  # 여러 endpoint 정보
    responses: Optional[Dict[str, Any]] = None  # OpenAPI responses schema
    method: Optional[str] = None  # HTTP method (GET, POST, etc.)
    endpoint: Optional[str] = None  # API endpoint URL
    authType: Optional[str] = None  # Authentication type (oauth, api_key, none)


@dataclass
class TeamTagResponse:
    """팀 태그 응답"""
    id: str
    name: str


@dataclass
class MCPResponse:
    """MCP 응답"""
    id: str
    name: str
    description: str
    type: str
    status: str
    version: str
    endpoint: str
    toolList: List[ToolResponse]  # camelCase for frontend
    teamTagIds: List[str]  # camelCase for frontend
    createdAt: int  # camelCase for frontend, Unix timestamp (seconds)
    updatedAt: int  # camelCase for frontend, Unix timestamp (seconds)

    # External MCP sub-type 구분 (endpoint | container | legacy)
    subType: Optional[str] = None

    # External MCP (Endpoint URL 타입)
    endpointUrl: Optional[str] = None  # MCP 서버 엔드포인트 URL
    authType: Optional[str] = None  # 인증 타입 (no_auth | oauth)
    oauthProviderArn: Optional[str] = None  # OAuth 사용 시 AgentCore Identity OAuth2 Credential Provider ARN
    userPoolId: Optional[str] = None  # (Legacy) OAuth 사용 시 Cognito User Pool ID

    # External MCP (Container 타입) - ecrRepository, imageTag는 아래에서 공유
    environment: Optional[Dict[str, str]] = None  # 컨테이너 환경변수

    # Legacy External MCP (Multi-MCP Proxy) - 기존 JSON config 방식
    serverName: Optional[str] = None  # Tool prefix (예: "youtube", "github")
    mcpConfig: Optional[Dict[str, Any]] = None  # {command, args, env}
    serverUrl: Optional[str] = None  # Legacy: Smithery server URL
    authConfig: Optional[Dict[str, Any]] = None  # Legacy: Auth config
    config: Optional[Dict[str, Any]] = None  # Legacy: MCP Configuration JSON
    targetId: Optional[str] = None  # Gateway Target ID (External MCP)

    # Internal Deploy MCP (Container) & External Container MCP
    ecrRepository: Optional[str] = None  # ECR repository name
    imageTag: Optional[str] = None  # Docker image tag

    # Shared (External & Internal Deploy)
    runtimeId: Optional[str] = None  # AgentCore Runtime ID
    runtimeUrl: Optional[str] = None  # Runtime endpoint URL

    # Internal Create MCP (API)
    selectedApiTargets: Optional[List[Dict[str, Any]]] = None  # API targets

    # Internal MCP (Deploy & Create) - Semantic Search
    enableSemanticSearch: Optional[bool] = None  # Semantic Search enabled


@dataclass
class MCPListResponse:
    """MCP 목록 응답"""
    data: List[MCPResponse]
    total: int


@dataclass
class DashboardStatsResponse:
    """Dashboard 통계 응답"""
    mcps: Dict[str, int]
    agents: Dict[str, int]
    knowledge_bases: Dict[str, int]
