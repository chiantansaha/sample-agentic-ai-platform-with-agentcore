"""MCP Infrastructure Repositories - DynamoDB Implementation"""

import json
from decimal import Decimal
from typing import List, Optional, Dict, Any

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from app.config import settings
from app.shared.utils.timestamp import parse_timestamp_value, now_timestamp
from ..domain.entities import (
    MCP, ExternalMCP, InternalDeployMCP, InternalCreateMCP,
    ExternalEndpointMCP, ExternalContainerMCP
)
from ..domain.repositories import MCPRepository
from ..domain.value_objects import MCPId, MCPType, Status, AuthConfig, DeploymentConfig, APITarget, ExternalAuthType, ToolEndpoint
from .dynamodb_client import dynamodb_client


class DynamoDBMCPRepository(MCPRepository):
    """DynamoDB implementation of MCP repository"""

    def __init__(self):
        self.table_name = settings.DYNAMODB_MCP_TABLE

    @property
    def table(self):
        """Get MCP table"""
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

    def _mcp_to_item(self, mcp: MCP) -> Dict[str, Any]:
        """Convert MCP entity to DynamoDB item"""
        item = {
            'id': mcp.id.value,
            'name': mcp.name,
            'description': mcp.description,
            'type': mcp.type.value,
            'status': mcp.status.value,
            'version': mcp.version,
            'endpoint': mcp.endpoint,
            'tool_list': [
                {
                    'name': tool.name,
                    'description': tool.description,
                    'input_schema': tool.input_schema,
                    'endpoints': [
                        {
                            'method': ep.method,
                            'path': ep.path,
                            'summary': ep.summary,
                            'input_schema': ep.input_schema,
                            'responses': ep.responses
                        }
                        for ep in (tool.endpoints or [])
                    ] if tool.endpoints else None,
                    'responses': tool.responses,
                    'method': tool.method,
                    'endpoint': tool.endpoint,
                    'auth_type': tool.auth_type
                }
                for tool in mcp.tool_list
            ],
            'team_tag_ids': mcp.team_tag_ids,
            'created_at': mcp.created_at,
            'updated_at': mcp.updated_at
        }

        # Type-specific fields
        # Note: Check ExternalEndpointMCP and ExternalContainerMCP BEFORE ExternalMCP
        # because they are subclasses of MCP with type=EXTERNAL
        if isinstance(mcp, ExternalEndpointMCP):
            item['sub_type'] = 'endpoint'
            item['endpoint_url'] = mcp.endpoint_url
            item['auth_type'] = mcp.auth_type.value
            item['user_pool_id'] = mcp.user_pool_id
            item['gateway_id'] = mcp.gateway_id
            item['target_id'] = mcp.target_id

        elif isinstance(mcp, ExternalContainerMCP):
            item['sub_type'] = 'container'
            item['ecr_repository'] = mcp.ecr_repository
            item['image_tag'] = mcp.image_tag
            item['auth_type'] = mcp.auth_type.value
            item['user_pool_id'] = mcp.user_pool_id
            item['environment'] = mcp.environment
            item['gateway_id'] = mcp.gateway_id
            item['target_id'] = mcp.target_id
            item['runtime_id'] = mcp.runtime_id
            item['runtime_url'] = mcp.runtime_url

        elif isinstance(mcp, ExternalMCP):
            # Legacy External MCP (Multi-MCP Proxy)
            item['sub_type'] = 'legacy'
            item['server_name'] = mcp.server_name
            item['mcp_config'] = mcp.mcp_config  # {command, args, env}
            # Legacy fields for backward compatibility
            item['server_url'] = mcp.server_url
            item['auth_config'] = {
                'type': mcp.auth_config.type,
                'client_id': mcp.auth_config.client_id,
                'client_secret': mcp.auth_config.client_secret,
                'token_url': mcp.auth_config.token_url,
                'api_key': mcp.auth_config.api_key
            }
            item['credential_provider_name'] = mcp.credential_provider_name
            item['config'] = mcp.config
            item['gateway_id'] = mcp.gateway_id
            item['runtime_id'] = mcp.runtime_id
            item['runtime_url'] = mcp.runtime_url
            item['target_id'] = mcp.target_id

        elif isinstance(mcp, InternalDeployMCP):
            item['ecr_repository'] = mcp.ecr_repository
            item['image_tag'] = mcp.image_tag
            item['deployment_config'] = {
                'resources': mcp.deployment_config.resources,
                'environment': mcp.deployment_config.environment
            }
            item['enable_semantic_search'] = mcp.enable_semantic_search
            item['dedicated_gateway_id'] = mcp.dedicated_gateway_id
            item['runtime_id'] = mcp.runtime_id
            item['runtime_url'] = mcp.runtime_url

        elif isinstance(mcp, InternalCreateMCP):
            # Store only api_id (minimal reference)
            # Full API details (including team_tag_ids) will be fetched from API Catalog on retrieval
            item['selected_api_targets'] = [
                {
                    'id': target.id,
                    'api_id': target.api_id
                }
                for target in mcp.selected_api_targets
            ]
            item['enable_semantic_search'] = mcp.enable_semantic_search
            item['dedicated_gateway_id'] = mcp.dedicated_gateway_id

        # Convert floats to Decimals for DynamoDB
        return self._convert_floats_to_decimals(item)

    def _item_to_mcp(self, item: Dict[str, Any]) -> MCP:
        """Convert DynamoDB item to MCP entity"""
        from ..domain.value_objects import Tool

        # Convert Decimals to float
        item = self._convert_decimals(item)

        # Common fields
        mcp_id = MCPId(item['id'])
        name = item['name']
        description = item['description']
        mcp_type = MCPType(item['type'])
        status = Status(item['status'])
        team_tag_ids = item.get('team_tag_ids', [])

        # Create appropriate MCP type
        if mcp_type == MCPType.EXTERNAL:
            sub_type = item.get('sub_type', 'legacy')

            if sub_type == 'endpoint':
                # ExternalEndpointMCP
                auth_type_str = item.get('auth_type', 'no_auth')
                auth_type = ExternalAuthType(auth_type_str) if auth_type_str else ExternalAuthType.NO_AUTH
                mcp = ExternalEndpointMCP(
                    id=mcp_id,
                    name=name,
                    description=description,
                    team_tag_ids=team_tag_ids,
                    endpoint_url=item.get('endpoint_url', ''),
                    auth_type=auth_type,
                    user_pool_id=item.get('user_pool_id'),
                    status=status
                )
                if item.get('gateway_id'):
                    mcp.set_gateway_id(item['gateway_id'])
                if item.get('target_id'):
                    mcp.set_target_id(item['target_id'])

            elif sub_type == 'container':
                # ExternalContainerMCP
                auth_type_str = item.get('auth_type', 'no_auth')
                auth_type = ExternalAuthType(auth_type_str) if auth_type_str else ExternalAuthType.NO_AUTH
                mcp = ExternalContainerMCP(
                    id=mcp_id,
                    name=name,
                    description=description,
                    team_tag_ids=team_tag_ids,
                    ecr_repository=item.get('ecr_repository', ''),
                    image_tag=item.get('image_tag', ''),
                    auth_type=auth_type,
                    user_pool_id=item.get('user_pool_id'),
                    environment=item.get('environment', {}),
                    status=status
                )
                if item.get('gateway_id'):
                    mcp.set_gateway_id(item['gateway_id'])
                if item.get('target_id'):
                    mcp.set_target_id(item['target_id'])
                if item.get('runtime_id'):
                    mcp.set_runtime_id(item['runtime_id'])
                if item.get('runtime_url'):
                    mcp.set_runtime_url(item['runtime_url'])

            else:
                # Legacy ExternalMCP (Multi-MCP Proxy)
                auth_config_data = item.get('auth_config', {})
                mcp = ExternalMCP(
                    id=mcp_id,
                    name=name,
                    description=description,
                    team_tag_ids=team_tag_ids,
                    # New format (Multi-MCP Proxy)
                    server_name=item.get('server_name', ''),
                    mcp_config=item.get('mcp_config', {}),  # {command, args, env}
                    # Legacy fields for backward compatibility
                    server_url=item.get('server_url', ''),
                    auth_config=AuthConfig(
                        type=auth_config_data.get('type', 'none'),
                        client_id=auth_config_data.get('client_id'),
                        client_secret=auth_config_data.get('client_secret'),
                        token_url=auth_config_data.get('token_url'),
                        api_key=auth_config_data.get('api_key')
                    ),
                    credential_provider_name=item.get('credential_provider_name', ''),
                    config=item.get('config', {}),
                    status=status
                )
                if item.get('gateway_id'):
                    mcp.set_gateway_id(item['gateway_id'])
                if item.get('runtime_id'):
                    mcp.set_runtime_id(item['runtime_id'])
                if item.get('runtime_url'):
                    mcp.set_runtime_url(item['runtime_url'])
                if item.get('target_id'):
                    mcp.set_target_id(item['target_id'])

        elif mcp_type == MCPType.INTERNAL_DEPLOY:
            deployment_config_data = item.get('deployment_config', {})
            mcp = InternalDeployMCP(
                id=mcp_id,
                name=name,
                description=description,
                team_tag_ids=team_tag_ids,
                ecr_repository=item.get('ecr_repository', ''),
                image_tag=item.get('image_tag', ''),
                deployment_config=DeploymentConfig(
                    resources=deployment_config_data.get('resources', {}),
                    environment=deployment_config_data.get('environment', {})
                ),
                enable_semantic_search=item.get('enable_semantic_search', False),
                status=status
            )
            if item.get('dedicated_gateway_id'):
                mcp.set_dedicated_gateway_id(item['dedicated_gateway_id'])
            if item.get('runtime_id'):
                mcp.set_runtime_id(item['runtime_id'])
            if item.get('runtime_url'):
                mcp.set_runtime_url(item['runtime_url'])

        elif mcp_type == MCPType.INTERNAL_CREATE:
            # Load minimal API target references (api_id only)
            # Full API details (including team_tag_ids) will be fetched from API Catalog in Service layer
            api_targets = []
            for target_data in item.get('selected_api_targets', []):
                # Create APITarget with minimal data - full data populated in service layer
                api_targets.append(APITarget(
                    id=target_data['id'],
                    name='',  # Will be populated from API Catalog
                    api_id=target_data['api_id'],
                    method='',  # Will be populated from API Catalog
                    auth_type='',  # Will be populated from API Catalog
                    team_tag_ids=[],  # Will be populated from API Catalog
                    openapi_schema=None,  # Will be populated from API Catalog
                    endpoint=None  # Will be populated from API Catalog
                ))

            mcp = InternalCreateMCP(
                id=mcp_id,
                name=name,
                description=description,
                team_tag_ids=team_tag_ids,
                selected_api_targets=api_targets,
                enable_semantic_search=item.get('enable_semantic_search', False),
                status=status
            )
            if item.get('dedicated_gateway_id'):
                mcp.set_dedicated_gateway_id(item['dedicated_gateway_id'])
        else:
            raise ValueError(f"Unknown MCP type: {mcp_type}")

        # Set common fields
        if item.get('endpoint'):
            mcp.set_endpoint(item['endpoint'])

        # Restore version (버전 복원)
        if item.get('version'):
            mcp._version = item['version']

        # Restore tool_list
        for tool_data in item.get('tool_list', []):
            # Restore endpoints if present
            endpoints = None
            if tool_data.get('endpoints'):
                endpoints = [
                    ToolEndpoint(
                        method=ep['method'],
                        path=ep['path'],
                        summary=ep['summary'],
                        input_schema=ep['input_schema'],
                        responses=ep.get('responses')
                    )
                    for ep in tool_data['endpoints']
                ]

            tool = Tool(
                name=tool_data['name'],
                description=tool_data['description'],
                input_schema=tool_data['input_schema'],
                endpoints=endpoints,
                responses=tool_data.get('responses'),
                method=tool_data.get('method'),
                endpoint=tool_data.get('endpoint'),
                auth_type=tool_data.get('auth_type')
            )
            mcp.add_tool(tool)

        # Restore timestamps (created_at과 updated_at 복원)
        # 하위 호환: ISO 문자열 또는 timestamp 모두 처리
        created_at = parse_timestamp_value(item.get('created_at')) or 0
        updated_at = parse_timestamp_value(item.get('updated_at')) or 0
        mcp._restore_timestamps(created_at, updated_at)

        return mcp

    async def save(self, mcp: MCP) -> None:
        """Save MCP to DynamoDB"""
        item = self._mcp_to_item(mcp)
        self.table.put_item(Item=item)

    async def find_by_id(self, mcp_id: MCPId) -> Optional[MCP]:
        """Find MCP by ID"""
        response = self.table.get_item(Key={'id': mcp_id.value})

        if 'Item' not in response:
            return None

        return self._item_to_mcp(response['Item'])

    async def find_all(self) -> List[MCP]:
        """Find all MCPs"""
        response = self.table.scan()

        mcps = []
        for item in response.get('Items', []):
            mcps.append(self._item_to_mcp(item))

        return mcps

    async def find_by_status(self, status: Status) -> List[MCP]:
        """Find MCPs by status"""
        response = self.table.scan(
            FilterExpression='#status = :status',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={':status': status.value}
        )

        mcps = []
        for item in response.get('Items', []):
            mcps.append(self._item_to_mcp(item))

        return mcps

    async def find_by_type(self, mcp_type: MCPType) -> List[MCP]:
        """Find MCPs by type"""
        response = self.table.scan(
            FilterExpression='#type = :type',
            ExpressionAttributeNames={'#type': 'type'},
            ExpressionAttributeValues={':type': mcp_type.value}
        )

        mcps = []
        for item in response.get('Items', []):
            mcps.append(self._item_to_mcp(item))

        return mcps

    async def find_by_name(self, name: str) -> Optional[MCP]:
        """Find MCP by name"""
        response = self.table.scan(
            FilterExpression='#name = :name',
            ExpressionAttributeNames={'#name': 'name'},
            ExpressionAttributeValues={':name': name}
        )

        items = response.get('Items', [])
        if not items:
            return None

        return self._item_to_mcp(items[0])

    async def delete(self, mcp_id: MCPId) -> None:
        """Delete MCP by ID"""
        self.table.delete_item(Key={'id': mcp_id.value})

    async def update_status(self, mcp_id: MCPId, status: Status) -> None:
        """MCP 상태만 업데이트 (부분 업데이트)"""
        self.table.update_item(
            Key={'id': mcp_id.value},
            UpdateExpression='SET #status = :status, updated_at = :updated_at',
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':status': status.value,
                ':updated_at': now_timestamp()
            }
        )


# Repository factory function
def get_mcp_repository() -> MCPRepository:
    """Get MCP repository instance"""
    return DynamoDBMCPRepository()
