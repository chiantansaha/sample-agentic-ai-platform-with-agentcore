"""Mock MCP Repository for Demo Mode"""
from typing import List, Optional, Dict, Any

from app.shared.mock_data import MOCK_MCPS
from ..domain.repositories import MCPRepository
from ..domain.entities import (
    MCP, ExternalMCP, InternalDeployMCP, InternalCreateMCP,
    ExternalEndpointMCP, ExternalContainerMCP
)
from ..domain.value_objects import (
    MCPId, MCPType, Status, AuthConfig, DeploymentConfig,
    APITarget, ExternalAuthType, Tool
)


class MockMCPRepository(MCPRepository):
    """Mock MCP Repository - 메모리 기반 데모용 구현"""

    def __init__(self):
        # Mock 데이터를 메모리에 로드
        self._mcps: Dict[str, MCP] = {}
        for mcp_data in MOCK_MCPS:
            mcp = self._dict_to_mcp(mcp_data)
            self._mcps[mcp.id.value] = mcp

    def _dict_to_mcp(self, data: Dict[str, Any]) -> MCP:
        """Dict -> MCP Entity 변환"""
        mcp_id = MCPId(data["id"])
        mcp_type = MCPType(data["type"])
        status = Status(data["status"])

        if mcp_type == MCPType.EXTERNAL:
            sub_type = data.get("sub_type", "endpoint")

            if sub_type == "endpoint":
                auth_type = ExternalAuthType(data.get("auth_type", "no_auth"))
                mcp = ExternalEndpointMCP(
                    id=mcp_id,
                    name=data["name"],
                    description=data["description"],
                    team_tag_ids=data.get("team_tag_ids", []),
                    endpoint_url=data.get("endpoint_url", ""),
                    auth_type=auth_type,
                    status=status
                )
            elif sub_type == "container":
                auth_type = ExternalAuthType(data.get("auth_type", "no_auth"))
                mcp = ExternalContainerMCP(
                    id=mcp_id,
                    name=data["name"],
                    description=data["description"],
                    team_tag_ids=data.get("team_tag_ids", []),
                    ecr_repository=data.get("ecr_repository", ""),
                    image_tag=data.get("image_tag", ""),
                    auth_type=auth_type,
                    status=status
                )
            else:
                # Legacy ExternalMCP
                mcp = ExternalMCP(
                    id=mcp_id,
                    name=data["name"],
                    description=data["description"],
                    team_tag_ids=data.get("team_tag_ids", []),
                    server_name=data.get("server_name", ""),
                    mcp_config=data.get("mcp_config", {}),
                    status=status
                )

        elif mcp_type == MCPType.INTERNAL_DEPLOY:
            mcp = InternalDeployMCP(
                id=mcp_id,
                name=data["name"],
                description=data["description"],
                team_tag_ids=data.get("team_tag_ids", []),
                ecr_repository=data.get("ecr_repository", ""),
                image_tag=data.get("image_tag", ""),
                deployment_config=DeploymentConfig(resources={}, environment={}),
                status=status
            )

        elif mcp_type == MCPType.INTERNAL_CREATE:
            mcp = InternalCreateMCP(
                id=mcp_id,
                name=data["name"],
                description=data["description"],
                team_tag_ids=data.get("team_tag_ids", []),
                selected_api_targets=[],
                status=status
            )
        else:
            raise ValueError(f"Unknown MCP type: {mcp_type}")

        # Set endpoint and version
        if data.get("endpoint"):
            mcp.set_endpoint(data["endpoint"])
        if data.get("version"):
            mcp._version = data["version"]

        # Add tools
        for tool_data in data.get("tool_list", []):
            tool = Tool(
                name=tool_data["name"],
                description=tool_data["description"],
                input_schema=tool_data.get("input_schema", {})
            )
            mcp.add_tool(tool)

        # Restore timestamps
        mcp._restore_timestamps(
            data.get("created_at", 0),
            data.get("updated_at", 0)
        )

        return mcp

    async def save(self, mcp: MCP) -> None:
        """MCP 저장 (메모리)"""
        self._mcps[mcp.id.value] = mcp

    async def find_by_id(self, mcp_id: MCPId) -> Optional[MCP]:
        """ID로 MCP 조회"""
        return self._mcps.get(mcp_id.value)

    async def find_all(self) -> List[MCP]:
        """모든 MCP 조회"""
        return list(self._mcps.values())

    async def find_by_status(self, status: Status) -> List[MCP]:
        """상태별 MCP 조회"""
        return [mcp for mcp in self._mcps.values() if mcp.status == status]

    async def find_by_type(self, mcp_type: MCPType) -> List[MCP]:
        """타입별 MCP 조회"""
        return [mcp for mcp in self._mcps.values() if mcp.type == mcp_type]

    async def find_by_name(self, name: str) -> Optional[MCP]:
        """이름으로 MCP 조회"""
        for mcp in self._mcps.values():
            if mcp.name == name:
                return mcp
        return None

    async def delete(self, mcp_id: MCPId) -> None:
        """MCP 삭제"""
        if mcp_id.value in self._mcps:
            del self._mcps[mcp_id.value]

    async def update_status(self, mcp_id: MCPId, status: Status) -> None:
        """MCP 상태 업데이트"""
        if mcp_id.value in self._mcps:
            mcp = self._mcps[mcp_id.value]
            if status == Status.ENABLED:
                mcp.enable()
            else:
                mcp.disable()
