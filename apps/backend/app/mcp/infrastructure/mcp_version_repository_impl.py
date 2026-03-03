"""MCP Version Repository DynamoDB Implementation"""
from typing import List, Optional
from decimal import Decimal

from app.config import settings
from app.shared.utils.timestamp import parse_timestamp_value
from app.mcp.infrastructure.dynamodb_client import dynamodb_client
from app.mcp.domain.repositories.mcp_version_repository import MCPVersionRepository
from app.mcp.domain.value_objects import (
    MCPVersion,
    MCPType,
    Status,
    Tool,
    AuthConfig,
    APITarget
)


class DynamoDBMCPVersionRepository(MCPVersionRepository):
    """DynamoDB implementation of MCP Version repository"""

    def __init__(self):
        self.table_name = settings.DYNAMODB_MCP_VERSIONS_TABLE

    @property
    def table(self):
        """Get MCP versions table"""
        return dynamodb_client.get_table(self.table_name)

    def _convert_decimals(self, obj):
        """Convert Decimal objects to float recursively"""
        if isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._convert_decimals(value) for key, value in obj.items()}
        elif isinstance(obj, Decimal):
            return float(obj)
        return obj

    def _convert_floats_to_decimals(self, obj):
        """Convert float objects to Decimal recursively for DynamoDB"""
        if isinstance(obj, list):
            return [self._convert_floats_to_decimals(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._convert_floats_to_decimals(value) for key, value in obj.items()}
        elif isinstance(obj, float):
            return Decimal(str(obj))
        return obj

    def _version_to_item(self, version: MCPVersion) -> dict:
        """Convert MCPVersion to DynamoDB item"""
        item = {
            'mcp_id': version.mcp_id,
            'version': version.version,
            'endpoint': version.endpoint,
            'description': version.description,
            'change_log': version.change_log,
            'status': version.status.value,
            'tool_list': [
                {
                    'name': tool.name,
                    'description': tool.description,
                    'input_schema': tool.input_schema,
                    'responses': tool.responses,
                    'method': tool.method,
                    'endpoint': tool.endpoint,
                    'auth_type': tool.auth_type,
                }
                for tool in version.tool_list
            ],
            'created_at': version.created_at,
            'created_by': version.created_by,
            'mcp_type': version.mcp_type.value,
            'team_tag_ids': version.team_tag_ids,
        }

        # Add type-specific fields
        if version.server_url:
            item['server_url'] = version.server_url
        if version.auth_config:
            item['auth_config'] = {
                'type': version.auth_config.type,
                'client_id': version.auth_config.client_id,
                'client_secret': version.auth_config.client_secret,
                'token_url': version.auth_config.token_url,
            }
        if version.ecr_repository:
            item['ecr_repository'] = version.ecr_repository
        if version.image_tag:
            item['image_tag'] = version.image_tag
        if version.targets:
            item['targets'] = [
                {
                    'id': target.id,
                    'name': target.name,
                    'api_id': target.api_id,
                    'method': target.method,
                    'auth_type': target.auth_type,
                    'openapi_schema': target.openapi_schema,
                    'endpoint': target.endpoint,
                    'team_tag_ids': target.team_tag_ids or [],
                }
                for target in version.targets
            ]

        return self._convert_floats_to_decimals(item)

    def _item_to_version(self, item: dict) -> MCPVersion:
        """Convert DynamoDB item to MCPVersion"""
        item = self._convert_decimals(item)

        # Parse tool list
        tool_list = []
        for tool_data in item.get('tool_list', []):
            tool_list.append(Tool(
                name=tool_data['name'],
                description=tool_data['description'],
                input_schema=tool_data['input_schema'],
                responses=tool_data.get('responses'),
                method=tool_data.get('method'),
                endpoint=tool_data.get('endpoint'),
                auth_type=tool_data.get('auth_type'),
            ))

        # Parse auth config if exists
        auth_config = None
        if 'auth_config' in item:
            auth_data = item['auth_config']
            auth_config = AuthConfig(
                type=auth_data['type'],
                client_id=auth_data.get('client_id'),
                client_secret=auth_data.get('client_secret'),
                token_url=auth_data.get('token_url'),
            )

        # Parse targets if exists
        targets = None
        if 'targets' in item:
            targets = []
            for target_data in item['targets']:
                targets.append(APITarget(
                    id=target_data['id'],
                    name=target_data['name'],
                    api_id=target_data['api_id'],
                    method=target_data['method'],
                    auth_type=target_data['auth_type'],
                    openapi_schema=target_data.get('openapi_schema'),
                    endpoint=target_data.get('endpoint'),
                    team_tag_ids=target_data.get('team_tag_ids', []),
                ))

        return MCPVersion(
            mcp_id=item['mcp_id'],
            version=item['version'],
            endpoint=item['endpoint'],
            description=item['description'],
            change_log=item['change_log'],
            status=Status(item['status']),
            tool_list=tool_list,
            created_at=parse_timestamp_value(item['created_at']) or 0,
            created_by=item['created_by'],
            mcp_type=MCPType(item['mcp_type']),
            team_tag_ids=item.get('team_tag_ids', []),
            server_url=item.get('server_url'),
            auth_config=auth_config,
            ecr_repository=item.get('ecr_repository'),
            image_tag=item.get('image_tag'),
            targets=targets,
        )

    async def save(self, version: MCPVersion) -> None:
        """버전 저장"""
        item = self._version_to_item(version)
        self.table.put_item(Item=item)

    async def find_by_mcp_id(self, mcp_id: str) -> List[MCPVersion]:
        """MCP ID로 모든 버전 조회 (최신순)"""
        response = self.table.query(
            KeyConditionExpression='mcp_id = :mcp_id',
            ExpressionAttributeValues={
                ':mcp_id': mcp_id
            },
            ScanIndexForward=False  # Sort by version descending
        )

        versions = []
        for item in response.get('Items', []):
            versions.append(self._item_to_version(item))

        return versions

    async def find_by_mcp_id_and_version(self, mcp_id: str, version: str) -> Optional[MCPVersion]:
        """특정 MCP의 특정 버전 조회"""
        response = self.table.get_item(
            Key={
                'mcp_id': mcp_id,
                'version': version
            }
        )

        if 'Item' not in response:
            return None

        return self._item_to_version(response['Item'])

    async def get_latest_version(self, mcp_id: str) -> Optional[MCPVersion]:
        """MCP의 최신 버전 조회"""
        response = self.table.query(
            KeyConditionExpression='mcp_id = :mcp_id',
            ExpressionAttributeValues={
                ':mcp_id': mcp_id
            },
            ScanIndexForward=False,  # Sort by version descending
            Limit=1
        )

        items = response.get('Items', [])
        if not items:
            return None

        return self._item_to_version(items[0])
