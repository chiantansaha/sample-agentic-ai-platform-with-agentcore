"""MCP Request DTOs"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import re


@dataclass
class TargetInfo:
    """Target 정보"""
    name: str
    description: str
    endpoint: str
    method: str
    openApiSchema: Dict[str, Any]
    apiId: Optional[str] = None  # API Catalog의 실제 API ID
    teamTagIds: Optional[List[str]] = None  # Target의 team tag IDs


@dataclass
class MCPServerConfig:
    """MCP Server Configuration (Claude Desktop/Cline format)

    Standard MCP server configuration format used by Claude Desktop and Cline.
    """
    command: str  # Command to run (e.g., "npx", "node", "python")
    args: List[str]  # Command arguments
    env: Dict[str, str]  # Environment variables

    def __post_init__(self):
        if not self.command:
            raise ValueError("Command is required")
        if self.args is None:
            object.__setattr__(self, 'args', [])
        if self.env is None:
            object.__setattr__(self, 'env', {})


@dataclass
class CreateExternalMCPRequest:
    """외부 MCP 생성 요청

    표준 MCP 서버 설정 JSON을 사용하여 외부 MCP를 연동합니다.
    - server_name: 서버 이름 (Tool prefix로 사용, 예: youtube → youtube__search_videos)
    - mcp_config: MCP 서버 설정 (command, args, env)
    """
    name: str
    description: str
    server_name: str  # Tool prefix (예: "youtube", "github", "filesystem")
    mcp_config: Dict[str, Any]  # {command, args, env}
    team_tags: List[str] = field(default_factory=list)  # Optional - 기능 제거됨

    def __post_init__(self):
        """MCP 이름 검증 (AWS Gateway 명명 규칙)"""
        if not self.name or len(self.name) < 1 or len(self.name) > 64:
            raise ValueError("MCP name must be between 1 and 64 characters")

        # AWS 리소스 명명 규칙: 영문자, 숫자, 하이픈, 언더스코어만 허용
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$', self.name):
            raise ValueError("MCP name can only use letters, numbers, hyphens (-), and underscores (_). Example: my-external-mcp")

        # Server name 검증: 영문자, 숫자, 언더스코어, 점, 하이픈 허용
        if not self.server_name or not re.match(r'^[a-zA-Z][a-zA-Z0-9_.\-]*$', self.server_name):
            raise ValueError("Server name must start with a letter and contain only letters, numbers, underscores, dots, and hyphens")

        # MCP config 검증
        if not self.mcp_config:
            raise ValueError("MCP configuration is required")
        if not self.mcp_config.get('command'):
            raise ValueError("MCP configuration must contain 'command' field")

    def get_config(self) -> MCPServerConfig:
        """MCPServerConfig 객체 반환"""
        return MCPServerConfig(
            command=self.mcp_config.get('command', ''),
            args=self.mcp_config.get('args', []),
            env=self.mcp_config.get('env', {})
        )


@dataclass
class CreateInternalDeployMCPRequest:
    """내부 배포 MCP 생성 요청"""
    name: str
    description: str
    ecr_repository: str
    image_tag: str
    resources: Dict[str, Any]
    environment: Dict[str, str]
    team_tags: List[str] = field(default_factory=list)  # Optional - 기능 제거됨
    enable_semantic_search: bool = False  # Enable semantic search for tool discovery


@dataclass
class CreateInternalCreateMCPRequest:
    """내부 생성 MCP 생성 요청 (API 기반)"""
    name: str
    description: str
    targets: List[TargetInfo]  # Task 1: selected_api_ids → targets 변경
    team_tags: List[str] = field(default_factory=list)  # Optional - 기능 제거됨
    enable_semantic_search: bool = False  # Enable semantic search for tool discovery

    def __post_init__(self):
        """MCP 이름 검증 (AWS Gateway 명명 규칙)"""
        if not self.name or len(self.name) < 1 or len(self.name) > 64:
            raise ValueError("MCP name must be between 1 and 64 characters")
        
        # AWS 리소스 명명 규칙: 영문자, 숫자, 하이픈, 언더스코어만 허용
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$', self.name):
            raise ValueError("MCP name can only use letters, numbers, hyphens (-), and underscores (_). Example: my-mcp-name")


@dataclass
class CreateExternalEndpointMCPRequest:
    """외부 MCP (Endpoint URL) 생성 요청

    기존 MCP 서버의 엔드포인트 URL에 직접 연결합니다.
    - endpoint_url: MCP 서버 엔드포인트 (예: https://knowledge-mcp.global.api.aws/)
    - auth_type: 인증 방식 (no_auth: 공용 Cognito, oauth: AgentCore Identity OAuth Provider)
    - oauth_provider_arn: OAuth 사용 시 선택한 AgentCore Identity OAuth2 Credential Provider ARN
    - user_pool_id: (Legacy) OAuth 사용 시 선택한 Cognito User Pool ID
    """
    name: str
    description: str
    endpoint_url: str
    team_tags: List[str] = field(default_factory=list)  # Optional - 기능 제거됨
    auth_type: str = "no_auth"  # "no_auth" | "oauth"
    oauth_provider_arn: Optional[str] = None  # OAuth2 Credential Provider ARN
    user_pool_id: Optional[str] = None  # Legacy

    def __post_init__(self):
        """입력 검증"""
        if not self.name or len(self.name) < 1 or len(self.name) > 64:
            raise ValueError("MCP name must be between 1 and 64 characters")

        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$', self.name):
            raise ValueError("MCP name can only use letters, numbers, hyphens (-), and underscores (_)")

        if not self.endpoint_url:
            raise ValueError("Endpoint URL is required")

        if not self.endpoint_url.startswith(('http://', 'https://')):
            raise ValueError("Endpoint URL must start with http:// or https://")

        if self.auth_type not in ("no_auth", "oauth"):
            raise ValueError("auth_type must be 'no_auth' or 'oauth'")

        # OAuth 선택 시 oauth_provider_arn 또는 user_pool_id 중 하나 필요
        if self.auth_type == "oauth" and not self.oauth_provider_arn and not self.user_pool_id:
            raise ValueError("oauth_provider_arn or user_pool_id is required when auth_type is 'oauth'")


@dataclass
class CreateExternalContainerMCPRequest:
    """외부 MCP (Container Image) 생성 요청

    ECR 이미지를 Runtime으로 배포 후 Gateway Target으로 연결합니다.
    - ecr_repository: ECR 리포지토리 이름
    - image_tag: 이미지 태그
    - auth_type: 인증 방식 (no_auth: 공용 Cognito, oauth: 사용자 선택 User Pool)
    - user_pool_id: OAuth 사용 시 선택한 Cognito User Pool ID
    - environment: 컨테이너 환경변수
    """
    name: str
    description: str
    ecr_repository: str
    image_tag: str
    team_tags: List[str] = field(default_factory=list)  # Optional - 기능 제거됨
    auth_type: str = "no_auth"  # "no_auth" | "oauth"
    user_pool_id: Optional[str] = None
    environment: Optional[Dict[str, str]] = None

    def __post_init__(self):
        """입력 검증"""
        if not self.name or len(self.name) < 1 or len(self.name) > 64:
            raise ValueError("MCP name must be between 1 and 64 characters")

        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$', self.name):
            raise ValueError("MCP name can only use letters, numbers, hyphens (-), and underscores (_)")

        if not self.ecr_repository:
            raise ValueError("ECR repository is required")

        if not self.image_tag:
            raise ValueError("Image tag is required")

        if self.auth_type not in ("no_auth", "oauth"):
            raise ValueError("auth_type must be 'no_auth' or 'oauth'")

        if self.auth_type == "oauth" and not self.user_pool_id:
            raise ValueError("user_pool_id is required when auth_type is 'oauth'")


@dataclass
class UpdateMCPRequest:
    """MCP 업데이트 요청"""
    description: Optional[str] = None
    team_tags: Optional[List[str]] = None
    targets: Optional[List[TargetInfo]] = None  # For internal-create MCP updates
    image_tag: Optional[str] = None  # For internal-deploy MCP updates
    # For external MCP (endpoint type) updates
    endpoint_url: Optional[str] = None
    auth_type: Optional[str] = None  # "no_auth" | "oauth"
    oauth_provider_arn: Optional[str] = None  # AgentCore Identity OAuth2 Credential Provider ARN
    user_pool_id: Optional[str] = None  # Legacy
    # For internal MCP (Deploy & Create) - Semantic Search
    enable_semantic_search: Optional[bool] = None


@dataclass
class MCPStatusRequest:
    """MCP 상태 변경 요청"""
    status: str  # "enabled" | "disabled"
