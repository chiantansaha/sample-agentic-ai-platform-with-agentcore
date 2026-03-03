"""MCP Client - Temporary implementation until ssminji merge

이 클라이언트는 ssminji 브랜치 merge 전까지 임시로 사용됩니다.
merge 후 실제 MCP Repository로 교체될 예정입니다.

ssminji MCP 응답 구조:
- id, name, description, type, status, version, endpoint
- toolList, teamTagIds
- 타입별 추가 필드: serverUrl, authConfig, ecrRepository, imageTag, selectedApiTargets
"""
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MCPInfo:
    """MCP 정보 (ssminji 브랜치 MCPResponse 구조 기반)"""
    id: str
    name: str
    description: str
    type: str  # 'external' | 'internal-deploy' | 'internal-create'
    status: str  # 'enabled' | 'disabled'
    version: str
    endpoint: str  # Gateway URL
    tool_list: List[Dict[str, Any]]
    team_tag_ids: List[str]

    # 타입별 추가 필드
    server_url: Optional[str] = None
    auth_config: Optional[Dict[str, Any]] = None
    ecr_repository: Optional[str] = None
    image_tag: Optional[str] = None
    selected_api_targets: Optional[List[Dict[str, Any]]] = None


class MCPClient:
    """MCP 조회 클라이언트 (Temporary)

    ssminji 브랜치 merge 전까지 HTTP API를 통해 MCP를 조회합니다.
    merge 후 실제 MCPRepository로 교체됩니다.

    TODO (ssminji merge 후):
    - MCPRepository 사용으로 교체
    - HTTP 호출 대신 DynamoDB 직접 조회
    """

    def __init__(self):
        # 현재는 stub 구현
        # TODO: ssminji merge 후 MCPRepository 주입
        pass

    async def get_mcp(self, mcp_id: str) -> Optional[MCPInfo]:
        """MCP 조회 (ID 기반)

        Args:
            mcp_id: MCP ID (e.g., "mcp-abc123")

        Returns:
            MCPInfo 또는 None (찾지 못한 경우)
        """
        # TODO (ssminji merge 전): HTTP API 호출
        # import httpx
        # async with httpx.AsyncClient() as client:
        #     response = await client.get(f"/api/v1/mcps/{mcp_id}")
        #     if response.status_code == 200:
        #         data = response.json()["data"]
        #         return self._parse_mcp_response(data)

        # TODO (ssminji merge 후): MCPRepository 사용
        # mcp_entity = await self.mcp_repository.find_by_id(mcp_id)
        # if mcp_entity:
        #     return self._entity_to_info(mcp_entity)

        logger.warning(f"MCP not found: {mcp_id} (stub implementation)")
        return None

    async def list_mcps(self, status_filter: Optional[str] = None) -> List[MCPInfo]:
        """MCP 목록 조회

        Args:
            status_filter: 상태 필터 ('enabled' | 'disabled')

        Returns:
            MCP 목록
        """
        # TODO: 구현 필요
        logger.warning("list_mcps not implemented (stub)")
        return []

    def _parse_mcp_response(self, data: Dict[str, Any]) -> MCPInfo:
        """API 응답 → MCPInfo 변환"""
        return MCPInfo(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            type=data["type"],
            status=data["status"],
            version=data["version"],
            endpoint=data["endpoint"],
            tool_list=data.get("toolList", []),
            team_tag_ids=data.get("teamTagIds", []),
            server_url=data.get("serverUrl"),
            auth_config=data.get("authConfig"),
            ecr_repository=data.get("ecrRepository"),
            image_tag=data.get("imageTag"),
            selected_api_targets=data.get("selectedApiTargets")
        )

    def to_mcp_server_config(self, mcp: MCPInfo) -> Dict[str, Any]:
        """MCPInfo → Jinja2 mcp_servers 설정 변환

        AgentCodeGenerator의 agent_config["mcp_servers"] 형식으로 변환:
        {
            "name": "server_name",      # MCP 서버 이름 (prefix)
            "transport": "http",        # http, sse, stdio
            "url": "https://...",       # Gateway endpoint
            "headers": {...}            # 인증 헤더 (optional)
        }

        Args:
            mcp: MCP 정보

        Returns:
            mcp_servers 설정 딕셔너리
        """
        # 서버 이름: 소문자, 공백 → 언더스코어
        server_name = mcp.name.lower().replace(" ", "_").replace("-", "_")

        config = {
            "name": server_name,
            "transport": "http",  # 기본적으로 http (Gateway는 HTTP)
            "url": mcp.endpoint
        }

        # External MCP with OAuth 인증
        if mcp.type == "external" and mcp.auth_config:
            auth_type = mcp.auth_config.get("type")
            if auth_type == "oauth":
                # TODO: OAuth 토큰 획득 로직
                # 현재는 auth_config만 전달
                logger.warning(f"OAuth authentication for {mcp.name} - token acquisition not implemented")
                # config["headers"] = {
                #     "Authorization": f"Bearer {token}"
                # }

        return config
