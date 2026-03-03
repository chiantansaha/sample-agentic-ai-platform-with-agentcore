"""MCP Domain Entities"""
from abc import ABC, abstractmethod
from typing import List, Optional
from ..value_objects import (
    MCPId, MCPType, Status, Tool,
    AuthConfig, DeploymentConfig, APITarget, ExternalAuthType
)
from app.shared.utils.timestamp import now_timestamp


class MCP(ABC):
    """MCP 추상 엔티티"""
    
    def __init__(
        self,
        id: MCPId,
        name: str,
        description: str,
        type: MCPType,
        team_tag_ids: List[str],
        status: Status = Status.ENABLED,
        version: str = "v1"
    ):
        self._id = id
        self._name = name
        self._description = description
        self._type = type
        self._status = status
        self._version = version
        self._team_tag_ids = team_tag_ids
        self._tool_list: List[Tool] = []
        self._created_at: int = now_timestamp()
        self._updated_at: int = now_timestamp()
        self._endpoint = ""
    
    # Properties
    @property
    def id(self) -> MCPId:
        return self._id
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return self._description
    
    @property
    def type(self) -> MCPType:
        return self._type
    
    @property
    def status(self) -> Status:
        return self._status
    
    @property
    def version(self) -> str:
        return self._version
    
    @property
    def endpoint(self) -> str:
        return self._endpoint
    
    @property
    def tool_list(self) -> List[Tool]:
        return self._tool_list.copy()
    
    @property
    def team_tag_ids(self) -> List[str]:
        return self._team_tag_ids.copy()
    
    @property
    def created_at(self) -> int:
        return self._created_at

    @property
    def updated_at(self) -> int:
        return self._updated_at
    
    # Business Methods
    def enable(self) -> None:
        """MCP 활성화"""
        if self._status == Status.ENABLED:
            raise ValueError("MCP is already enabled")
        self._status = Status.ENABLED
        self._updated_at = now_timestamp()

    def disable(self) -> None:
        """MCP 비활성화"""
        if self._status == Status.DISABLED:
            raise ValueError("MCP is already disabled")
        self._status = Status.DISABLED
        self._updated_at = now_timestamp()

    def update_basic_info(self, description: str, team_tag_ids: List[str]) -> None:
        """기본 정보 업데이트"""
        self._description = description
        self._team_tag_ids = team_tag_ids
        self._updated_at = now_timestamp()

    def add_tool(self, tool: Tool) -> None:
        """도구 추가"""
        self._tool_list.append(tool)
        self._updated_at = now_timestamp()

    def clear_tools(self) -> None:
        """도구 목록 초기화"""
        self._tool_list = []
        self._updated_at = now_timestamp()

    def set_endpoint(self, endpoint: str) -> None:
        """엔드포인트 설정"""
        self._endpoint = endpoint
        self._updated_at = now_timestamp()

    def increment_version(self) -> None:
        """버전 증가 (v1 -> v2, v2 -> v3, ...)"""
        try:
            current_num = int(self._version.replace('v', ''))
            self._version = f"v{current_num + 1}"
        except ValueError:
            # 버전 형식이 잘못된 경우 v1으로 초기화
            self._version = "v1"
        self._updated_at = now_timestamp()

    def _restore_timestamps(self, created_at: int, updated_at: int) -> None:
        """타임스탬프 복원 (Repository에서만 사용)"""
        self._created_at = created_at
        self._updated_at = updated_at

    @abstractmethod
    def validate_configuration(self) -> bool:
        """설정 검증 (타입별 구현)"""
        pass


class ExternalMCP(MCP):
    """외부 MCP (Multi-MCP Proxy 방식)

    표준 MCP 서버 설정 JSON을 사용하여 외부 MCP를 연동합니다.
    모든 External MCP는 공유 Multi-MCP Proxy Runtime에서 관리됩니다.
    - server_name: Tool prefix로 사용 (예: youtube → youtube__search_videos)
    - mcp_config: MCP 서버 설정 (command, args, env)
    """

    def __init__(
        self,
        id: MCPId,
        name: str,
        description: str,
        team_tag_ids: List[str],
        server_name: str,  # Tool prefix (예: "youtube", "github")
        mcp_config: dict,  # {command, args, env}
        # Legacy fields for backward compatibility
        server_url: Optional[str] = None,
        auth_config: Optional[AuthConfig] = None,
        credential_provider_name: Optional[str] = None,
        config: Optional[dict] = None,
        **kwargs
    ):
        super().__init__(id, name, description, MCPType.EXTERNAL, team_tag_ids, **kwargs)
        self._server_name = server_name
        self._mcp_config = mcp_config  # {command, args, env}
        # Legacy fields (for backward compatibility)
        self._server_url = server_url or ""
        self._auth_config = auth_config or AuthConfig(type="none")
        self._credential_provider_name = credential_provider_name or ""
        self._config = config or {}
        self._gateway_id: Optional[str] = None  # 공유 Gateway ID
        self._runtime_id: Optional[str] = None  # 공유 Runtime ID (Multi-MCP Proxy)
        self._runtime_url: Optional[str] = None  # Runtime 엔드포인트
        self._target_id: Optional[str] = None  # Gateway Target ID

    @property
    def server_name(self) -> str:
        """Server name (Tool prefix)"""
        return self._server_name

    @property
    def mcp_config(self) -> dict:
        """MCP Configuration (command, args, env)"""
        return self._mcp_config.copy() if self._mcp_config else {}

    @property
    def command(self) -> str:
        """MCP command"""
        return self._mcp_config.get('command', '') if self._mcp_config else ''

    @property
    def args(self) -> list:
        """MCP command arguments"""
        return self._mcp_config.get('args', []) if self._mcp_config else []

    @property
    def env(self) -> dict:
        """MCP environment variables"""
        return self._mcp_config.get('env', {}) if self._mcp_config else {}

    # Legacy properties for backward compatibility
    @property
    def server_url(self) -> str:
        """Legacy: Smithery server URL"""
        return self._server_url

    @property
    def auth_config(self) -> AuthConfig:
        """Legacy: 인증 설정"""
        return self._auth_config

    @property
    def credential_provider_name(self) -> str:
        """Legacy: AgentCore Identity의 API Key Credential Provider 이름"""
        return self._credential_provider_name

    @property
    def config(self) -> dict:
        """Legacy: MCP Configuration JSON"""
        return self._config.copy() if self._config else {}

    def set_config(self, config: dict) -> None:
        """Config 설정"""
        self._config = config or {}
        self._updated_at = now_timestamp()

    @property
    def gateway_id(self) -> Optional[str]:
        """공유 Gateway ID"""
        return self._gateway_id

    @property
    def runtime_id(self) -> Optional[str]:
        """전용 Runtime ID"""
        return self._runtime_id

    @property
    def runtime_url(self) -> Optional[str]:
        """Runtime 엔드포인트 URL"""
        return self._runtime_url

    @property
    def target_id(self) -> Optional[str]:
        """Gateway Target ID"""
        return self._target_id

    def set_gateway_id(self, gateway_id: str) -> None:
        """Gateway ID 설정"""
        self._gateway_id = gateway_id
        self._updated_at = now_timestamp()

    def set_runtime_id(self, runtime_id: str) -> None:
        """Runtime ID 설정"""
        self._runtime_id = runtime_id
        self._updated_at = now_timestamp()

    def set_runtime_url(self, runtime_url: str) -> None:
        """Runtime URL 설정"""
        self._runtime_url = runtime_url
        self._updated_at = now_timestamp()

    def set_target_id(self, target_id: str) -> None:
        """Target ID 설정"""
        self._target_id = target_id
        self._updated_at = now_timestamp()

    def test_connection(self) -> bool:
        """연결 테스트 (Mock 구현)"""
        # 실제로는 server_url에 HTTP 요청
        return True

    def validate_auth(self) -> bool:
        """인증 검증 (Legacy)"""
        return True  # 새로운 방식에서는 항상 True

    def validate_configuration(self) -> bool:
        """설정 검증"""
        # server_name과 command가 있어야 함
        return bool(self._server_name) and bool(self.command)


class InternalDeployMCP(MCP):
    """내부 배포 MCP (컨테이너)"""

    def __init__(
        self,
        id: MCPId,
        name: str,
        description: str,
        team_tag_ids: List[str],
        ecr_repository: str,
        image_tag: str,
        deployment_config: DeploymentConfig,
        enable_semantic_search: bool = False,
        **kwargs
    ):
        super().__init__(id, name, description, MCPType.INTERNAL_DEPLOY, team_tag_ids, **kwargs)
        self._ecr_repository = ecr_repository
        self._image_tag = image_tag
        self._deployment_config = deployment_config
        self._enable_semantic_search = enable_semantic_search
        self._dedicated_gateway_id: Optional[str] = None
        self._runtime_id: Optional[str] = None
        self._runtime_url: Optional[str] = None

    @property
    def ecr_repository(self) -> str:
        return self._ecr_repository

    @property
    def image_tag(self) -> str:
        return self._image_tag

    @property
    def deployment_config(self) -> DeploymentConfig:
        return self._deployment_config

    @property
    def enable_semantic_search(self) -> bool:
        return self._enable_semantic_search

    @property
    def dedicated_gateway_id(self) -> Optional[str]:
        return self._dedicated_gateway_id

    @property
    def runtime_id(self) -> Optional[str]:
        return self._runtime_id

    @property
    def runtime_url(self) -> Optional[str]:
        return self._runtime_url

    def set_dedicated_gateway_id(self, gateway_id: str) -> None:
        """전용 Gateway ID 설정"""
        self._dedicated_gateway_id = gateway_id
        self._updated_at = now_timestamp()

    def set_runtime_id(self, runtime_id: str) -> None:
        """Runtime ID 설정"""
        self._runtime_id = runtime_id
        self._updated_at = now_timestamp()

    def set_runtime_url(self, runtime_url: str) -> None:
        """Runtime URL 설정"""
        self._runtime_url = runtime_url
        self._updated_at = now_timestamp()

    def update_image_tag(self, image_tag: str) -> None:
        """이미지 태그 업데이트"""
        self._image_tag = image_tag
        self._updated_at = now_timestamp()

    def update_enable_semantic_search(self, enable: bool) -> None:
        """Semantic Search 설정 업데이트"""
        self._enable_semantic_search = enable
        self._updated_at = now_timestamp()

    def validate_ecr_image(self) -> bool:
        """ECR 이미지 존재 검증 (Mock 구현)"""
        # 실제로는 ECR API 호출
        return True

    def validate_configuration(self) -> bool:
        """설정 검증"""
        return (self._ecr_repository and
                self._image_tag and
                self.validate_ecr_image())


class InternalCreateMCP(MCP):
    """내부 생성 MCP (API)"""

    def __init__(
        self,
        id: MCPId,
        name: str,
        description: str,
        team_tag_ids: List[str],
        selected_api_targets: List[APITarget],
        enable_semantic_search: bool = False,
        **kwargs
    ):
        super().__init__(id, name, description, MCPType.INTERNAL_CREATE, team_tag_ids, **kwargs)
        self._selected_api_targets = selected_api_targets
        self._enable_semantic_search = enable_semantic_search
        self._dedicated_gateway_id: Optional[str] = None

    @property
    def selected_api_targets(self) -> List[APITarget]:
        return self._selected_api_targets.copy()

    @property
    def enable_semantic_search(self) -> bool:
        return self._enable_semantic_search

    @property
    def dedicated_gateway_id(self) -> Optional[str]:
        return self._dedicated_gateway_id
    
    def set_dedicated_gateway_id(self, gateway_id: str) -> None:
        """전용 Gateway ID 설정"""
        self._dedicated_gateway_id = gateway_id
        self._updated_at = now_timestamp()

    def add_api_target(self, api_target: APITarget) -> None:
        """API 타겟 추가"""
        self._selected_api_targets.append(api_target)
        self._updated_at = now_timestamp()

    def remove_api_target(self, api_id: str) -> None:
        """API 타겟 제거"""
        self._selected_api_targets = [
            target for target in self._selected_api_targets
            if target.api_id != api_id
        ]
        self._updated_at = now_timestamp()

    def update_targets(self, api_targets: List[APITarget]) -> None:
        """API 타겟 전체 교체"""
        self._selected_api_targets = api_targets
        self._updated_at = now_timestamp()

    def update_enable_semantic_search(self, enable: bool) -> None:
        """Semantic Search 설정 업데이트"""
        self._enable_semantic_search = enable
        self._updated_at = now_timestamp()

    def validate_configuration(self) -> bool:
        """설정 검증"""
        return len(self._selected_api_targets) > 0


class ExternalEndpointMCP(MCP):
    """외부 MCP - Endpoint URL 타입

    기존 MCP 서버의 엔드포인트 URL에 직접 연결합니다.
    - endpoint_url: MCP 서버 엔드포인트 (예: https://knowledge-mcp.global.api.aws/)
    - auth_type: 인증 방식 (no_auth: 공용 Cognito, oauth: AgentCore Identity OAuth Provider)
    - oauth_provider_arn: OAuth 사용 시 선택한 AgentCore Identity OAuth2 Credential Provider ARN
    - user_pool_id: (Legacy) OAuth 사용 시 선택한 Cognito User Pool ID
    """

    def __init__(
        self,
        id: MCPId,
        name: str,
        description: str,
        team_tag_ids: List[str],
        endpoint_url: str,
        auth_type: ExternalAuthType = ExternalAuthType.NO_AUTH,
        oauth_provider_arn: Optional[str] = None,
        user_pool_id: Optional[str] = None,  # Legacy, for backward compatibility
        **kwargs
    ):
        super().__init__(id, name, description, MCPType.EXTERNAL, team_tag_ids, **kwargs)
        self._endpoint_url = endpoint_url
        self._auth_type = auth_type
        self._oauth_provider_arn = oauth_provider_arn
        self._user_pool_id = user_pool_id  # Legacy
        self._gateway_id: Optional[str] = None  # 공유 Gateway ID (external-mcp-gateway)
        self._target_id: Optional[str] = None  # Gateway MCP Server Target ID
        self._sub_type = "endpoint"  # External MCP sub-type 구분

    @property
    def endpoint_url(self) -> str:
        """MCP 서버 엔드포인트 URL"""
        return self._endpoint_url

    @property
    def auth_type(self) -> ExternalAuthType:
        """인증 타입"""
        return self._auth_type

    @property
    def oauth_provider_arn(self) -> Optional[str]:
        """OAuth 사용 시 AgentCore Identity OAuth2 Credential Provider ARN"""
        return self._oauth_provider_arn

    @property
    def user_pool_id(self) -> Optional[str]:
        """(Legacy) OAuth 사용 시 Cognito User Pool ID"""
        return self._user_pool_id

    @property
    def gateway_id(self) -> Optional[str]:
        """공유 Gateway ID"""
        return self._gateway_id

    @property
    def target_id(self) -> Optional[str]:
        """Gateway Target ID"""
        return self._target_id

    @property
    def sub_type(self) -> str:
        """External MCP sub-type (endpoint | container)"""
        return self._sub_type

    def set_gateway_id(self, gateway_id: str) -> None:
        """Gateway ID 설정"""
        self._gateway_id = gateway_id
        self._updated_at = now_timestamp()

    def set_target_id(self, target_id: str) -> None:
        """Target ID 설정"""
        self._target_id = target_id
        self._updated_at = now_timestamp()

    def validate_configuration(self) -> bool:
        """설정 검증"""
        if not self._endpoint_url:
            return False
        if not self._endpoint_url.startswith(('http://', 'https://')):
            return False
        # OAuth 선택 시 oauth_provider_arn 또는 user_pool_id 중 하나 필요
        if self._auth_type == ExternalAuthType.OAUTH:
            if not self._oauth_provider_arn and not self._user_pool_id:
                return False
        return True

    def update_endpoint_url(self, endpoint_url: str) -> None:
        """Endpoint URL 업데이트"""
        self._endpoint_url = endpoint_url
        self._updated_at = now_timestamp()

    def update_auth_type(self, auth_type: ExternalAuthType) -> None:
        """인증 타입 업데이트"""
        self._auth_type = auth_type
        self._updated_at = now_timestamp()

    def update_oauth_provider_arn(self, oauth_provider_arn: Optional[str]) -> None:
        """OAuth Provider ARN 업데이트"""
        self._oauth_provider_arn = oauth_provider_arn
        self._updated_at = now_timestamp()

    def update_user_pool_id(self, user_pool_id: Optional[str]) -> None:
        """(Legacy) User Pool ID 업데이트"""
        self._user_pool_id = user_pool_id
        self._updated_at = now_timestamp()


class ExternalContainerMCP(MCP):
    """외부 MCP - Container Image 타입

    ECR 이미지를 Runtime으로 배포 후 Gateway Target으로 연결합니다.
    - ecr_repository: ECR 리포지토리 이름
    - image_tag: 이미지 태그
    - auth_type: 인증 방식 (no_auth: 공용 Cognito, oauth: 사용자 선택 User Pool)
    - user_pool_id: OAuth 사용 시 선택한 Cognito User Pool ID
    - environment: 컨테이너 환경변수
    """

    def __init__(
        self,
        id: MCPId,
        name: str,
        description: str,
        team_tag_ids: List[str],
        ecr_repository: str,
        image_tag: str,
        auth_type: ExternalAuthType = ExternalAuthType.NO_AUTH,
        user_pool_id: Optional[str] = None,
        environment: Optional[dict] = None,
        **kwargs
    ):
        super().__init__(id, name, description, MCPType.EXTERNAL, team_tag_ids, **kwargs)
        self._ecr_repository = ecr_repository
        self._image_tag = image_tag
        self._auth_type = auth_type
        self._user_pool_id = user_pool_id
        self._environment = environment or {}
        self._gateway_id: Optional[str] = None  # 공유 Gateway ID (external-mcp-gateway)
        self._target_id: Optional[str] = None  # Gateway Runtime Target ID
        self._runtime_id: Optional[str] = None  # Runtime ID
        self._runtime_url: Optional[str] = None  # Runtime 엔드포인트 URL
        self._sub_type = "container"  # External MCP sub-type 구분

    @property
    def ecr_repository(self) -> str:
        """ECR 리포지토리 이름"""
        return self._ecr_repository

    @property
    def image_tag(self) -> str:
        """이미지 태그"""
        return self._image_tag

    @property
    def auth_type(self) -> ExternalAuthType:
        """인증 타입"""
        return self._auth_type

    @property
    def user_pool_id(self) -> Optional[str]:
        """OAuth 사용 시 Cognito User Pool ID"""
        return self._user_pool_id

    @property
    def environment(self) -> dict:
        """컨테이너 환경변수"""
        return self._environment.copy()

    @property
    def gateway_id(self) -> Optional[str]:
        """공유 Gateway ID"""
        return self._gateway_id

    @property
    def target_id(self) -> Optional[str]:
        """Gateway Target ID"""
        return self._target_id

    @property
    def runtime_id(self) -> Optional[str]:
        """Runtime ID"""
        return self._runtime_id

    @property
    def runtime_url(self) -> Optional[str]:
        """Runtime 엔드포인트 URL"""
        return self._runtime_url

    @property
    def sub_type(self) -> str:
        """External MCP sub-type (endpoint | container)"""
        return self._sub_type

    def set_gateway_id(self, gateway_id: str) -> None:
        """Gateway ID 설정"""
        self._gateway_id = gateway_id
        self._updated_at = now_timestamp()

    def set_target_id(self, target_id: str) -> None:
        """Target ID 설정"""
        self._target_id = target_id
        self._updated_at = now_timestamp()

    def set_runtime_id(self, runtime_id: str) -> None:
        """Runtime ID 설정"""
        self._runtime_id = runtime_id
        self._updated_at = now_timestamp()

    def set_runtime_url(self, runtime_url: str) -> None:
        """Runtime URL 설정"""
        self._runtime_url = runtime_url
        self._updated_at = now_timestamp()

    def update_image_tag(self, image_tag: str) -> None:
        """이미지 태그 업데이트"""
        self._image_tag = image_tag
        self._updated_at = now_timestamp()

    def validate_configuration(self) -> bool:
        """설정 검증"""
        if not self._ecr_repository or not self._image_tag:
            return False
        if self._auth_type == ExternalAuthType.OAUTH and not self._user_pool_id:
            return False
        return True
