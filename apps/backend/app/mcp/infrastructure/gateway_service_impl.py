"""Bedrock AgentCore Gateway Service Implementation

기본 Gateway 기능과 Internal Create MCP (API 기반) 기능을 제공합니다.
Internal Deploy MCP와 External MCP 기능은 각각 별도 Mixin으로 분리되어 있습니다.
"""
import asyncio
import boto3
import json
import re
import time
from typing import Dict, Any, List, Optional
from ..domain.entities import MCP, InternalCreateMCP, ExternalMCP, ExternalEndpointMCP, ExternalContainerMCP
from ..domain.services import GatewayService
from ..domain.value_objects import Tool, ToolEndpoint, ExternalAuthType
from app.config import settings
from .cognito_service import CognitoService
from .deploy_mcp_service import DeployMCPServiceMixin
from .external_mcp_service import ExternalMCPServiceMixin


# TTL Cache for health check (60 seconds)
class TTLCache:
    """Simple TTL Cache for health check results"""

    def __init__(self, ttl_seconds: int = 60):
        self._cache: Dict[str, tuple] = {}  # {key: (value, expiry_time)}
        self._ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        """Get value if exists and not expired"""
        if key in self._cache:
            value, expiry = self._cache[key]
            if time.time() < expiry:
                return value
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        """Set value with TTL"""
        self._cache[key] = (value, time.time() + self._ttl)

    def invalidate(self, key: str) -> None:
        """Remove key from cache"""
        if key in self._cache:
            del self._cache[key]


class BedrockGatewayService(DeployMCPServiceMixin, ExternalMCPServiceMixin, GatewayService):
    """Bedrock AgentCore Gateway 실제 구현

    Mixins:
        - DeployMCPServiceMixin: Internal Deploy MCP (Container) 기능
        - ExternalMCPServiceMixin: External MCP (Smithery) 기능
    """

    def __init__(self):
        self.region = settings.AWS_REGION

        # Build kwargs for boto3 clients, only including credentials if they are non-empty
        # If empty, boto3 will use AWS_PROFILE from environment variables or ~/.aws/credentials
        aws_kwargs = {}
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            aws_kwargs['aws_access_key_id'] = settings.AWS_ACCESS_KEY_ID
            aws_kwargs['aws_secret_access_key'] = settings.AWS_SECRET_ACCESS_KEY

        self.iam_client = boto3.client('iam', **aws_kwargs)
        self.gateway_client = boto3.client(
            'bedrock-agentcore-control',
            region_name=self.region,
            **aws_kwargs
        )
        self.sts_client = boto3.client('sts', **aws_kwargs)
        self.account_id = self.sts_client.get_caller_identity()["Account"]
        self.credential_provider_arn = settings.APIGEE_KEY_CREDENTIAL_PROVIDER_ARN

        # Cognito 서비스 (공유 인프라)
        self.cognito_service = CognitoService()

        # 캐시된 OAuth Provider ARN
        self._oauth_provider_arn: Optional[str] = None

        # Health check TTL cache (60초)
        self._health_cache = TTLCache(ttl_seconds=60)

    # ============================================================
    # AgentCore Identity (Credential Provider) Methods
    # ============================================================

    async def list_oauth2_credential_providers(self) -> List[Dict[str, Any]]:
        """OAuth2 Credential Provider 목록 조회

        AgentCore Identity의 모든 OAuth2 타입 Credential Provider를 반환합니다.

        Returns:
            List[Dict]: [{
                'arn': str (Provider ARN),
                'name': str (Provider 이름),
                'vendor': str (Provider vendor - CustomOauth2, Google 등),
                'status': str (READY, CREATING 등),
                'createdAt': str (ISO 형식)
            }]
        """
        try:
            print("🔍 Fetching OAuth2 Credential Providers...")
            response = self.gateway_client.list_oauth2_credential_providers()

            providers = []
            for provider in response.get('credentialProviders', []):
                providers.append({
                    'arn': provider.get('credentialProviderArn', ''),
                    'name': provider.get('name', ''),
                    'vendor': provider.get('credentialProviderVendor', 'Unknown'),
                    'status': provider.get('status', 'UNKNOWN'),
                    'createdAt': provider.get('createdAt', '').isoformat() if hasattr(provider.get('createdAt', ''), 'isoformat') else str(provider.get('createdAt', ''))
                })

            print(f"✅ Found {len(providers)} OAuth2 providers")
            return providers

        except Exception as e:
            print(f"❌ Failed to list OAuth2 Credential Providers: {str(e)}")
            raise Exception(f"OAuth2 Credential Provider 목록 조회 실패: {str(e)}")

    # ============================================================
    # Health Check Methods
    # ============================================================

    async def check_gateway_health(self, gateway_id: str) -> dict:
        """Gateway Health 체크 (TTL 캐싱 적용)

        AgentCore Gateway의 status가 READY이면 healthy로 판단합니다.

        Args:
            gateway_id: Gateway ID (예: gw-xxxxxxxx)

        Returns:
            dict: {
                'healthy': bool,
                'status': str (READY, CREATING, UPDATING, FAILED 등),
                'message': str,
                'cached': bool (캐시된 결과인지 여부)
            }
        """
        # 캐시 확인
        cached_result = self._health_cache.get(gateway_id)
        if cached_result is not None:
            return {**cached_result, 'cached': True}

        # 실제 Gateway 상태 조회
        try:
            response = self.gateway_client.get_gateway(gatewayIdentifier=gateway_id)
            status = response.get('status', 'UNKNOWN')

            # READY 상태면 healthy
            if status == 'READY':
                result = {
                    'healthy': True,
                    'status': status,
                    'message': 'Gateway is healthy'
                }
            else:
                result = {
                    'healthy': False,
                    'status': status,
                    'message': f'Gateway status: {status}'
                }

            # 결과 캐싱
            self._health_cache.set(gateway_id, result)

            return {**result, 'cached': False}

        except self.gateway_client.exceptions.ResourceNotFoundException:
            result = {
                'healthy': False,
                'status': 'NOT_FOUND',
                'message': 'Gateway not found'
            }
            # NOT_FOUND도 캐싱 (30초간 반복 조회 방지)
            self._health_cache.set(gateway_id, result)
            return {**result, 'cached': False}

        except Exception as e:
            # 에러 발생 시 캐싱하지 않음 (재시도 허용)
            return {
                'healthy': False,
                'status': 'ERROR',
                'message': f'Failed to check gateway health: {str(e)}',
                'cached': False
            }

    # ============================================================
    # Common Helper Methods
    # ============================================================

    def _get_agentcore_assume_role_policy(self) -> dict:
        """Bedrock AgentCore용 공통 신뢰 정책 생성"""
        return {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock-agentcore.amazonaws.com"
                },
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {
                        "aws:SourceAccount": self.account_id
                    },
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:bedrock-agentcore:{self.region}:{self.account_id}:*"
                    }
                }
            }]
        }

    async def _delete_existing_iam_role(self, role_name: str) -> None:
        """기존 IAM 역할 및 연결된 정책 삭제"""
        try:
            policies = self.iam_client.list_role_policies(RoleName=role_name)
            for policy_name in policies.get('PolicyNames', []):
                self.iam_client.delete_role_policy(RoleName=role_name, PolicyName=policy_name)
            self.iam_client.delete_role(RoleName=role_name)
            await asyncio.sleep(2)
        except self.iam_client.exceptions.NoSuchEntityException:
            pass  # 역할이 없으면 무시

    def _sanitize_runtime_name(self, name: str) -> str:
        """Runtime 이름을 AWS 규칙에 맞게 변환

        AWS AgentCore Runtime naming constraint:
        - Pattern: [a-zA-Z][a-zA-Z0-9_]{0,47}
        - Must start with a letter
        - Only letters, numbers, and underscores allowed (NO hyphens)
        - Max 48 characters
        """
        # Replace hyphens with underscores
        sanitized = name.replace('-', '_')
        # Remove any other special characters
        sanitized = ''.join(c for c in sanitized if c.isalnum() or c == '_')
        # Ensure starts with a letter
        if sanitized and not sanitized[0].isalpha():
            sanitized = 'r_' + sanitized
        # Truncate to 48 characters
        return sanitized[:48]

    # ============================================================
    # Internal Create MCP (API-based) Methods
    # ============================================================

    async def create_dedicated_gateway(self, mcp: MCP, enable_semantic_search: bool = False) -> str:
        """전용 Gateway 생성"""
        gateway_name = f"{mcp.name}-gateway-{settings.ENVIRONMENT}"

        # 1. IAM Role 생성
        role_arn = await self._create_gateway_role(gateway_name)

        # 2. Gateway 생성 (IAM 인증)
        gateway = await self._create_gateway(gateway_name, role_arn, mcp.description, enable_semantic_search=enable_semantic_search)
        gateway_id = gateway['gatewayId']
        gateway_url = gateway['gatewayUrl']

        # 3. IAM 권한 수정 (Gateway가 Target을 호출할 수 있도록)
        await self._fix_iam_permissions(gateway_id, role_arn)

        # 4. Gateway READY 상태 대기 (Target 생성 전 필수)
        await self._wait_for_gateway_ready(gateway_id)

        # 5. InternalCreateMCP인 경우 REST API Targets 생성 및 Tools 추가
        if isinstance(mcp, InternalCreateMCP):
            await self._create_api_targets_and_tools(gateway_id, mcp)

        # 6. MCP에 엔드포인트 설정
        mcp.set_endpoint(gateway_url)

        return gateway_id

    async def _create_gateway_role(self, gateway_name: str) -> str:
        """Gateway용 IAM 역할 생성"""
        role_name = f'{gateway_name}-role'

        # 권한 정책 (Gateway 전용)
        role_policy = {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:*",
                    "bedrock:*",
                    "secretsmanager:GetSecretValue"
                ],
                "Resource": "*"
            }]
        }

        try:
            # 기존 역할 삭제
            await self._delete_existing_iam_role(role_name)

            # 새 역할 생성
            role = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(self._get_agentcore_assume_role_policy()),
                Description=f'AgentCore Gateway execution role for {gateway_name}'
            )

            # 권한 정책 연결
            self.iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName="AgentCorePolicy",
                PolicyDocument=json.dumps(role_policy)
            )

            return role['Role']['Arn']

        except Exception as e:
            raise Exception(f"IAM 역할 생성 실패: {str(e)}")

    async def _create_gateway(self, gateway_name: str, role_arn: str, description: str = None, enable_semantic_search: bool = False) -> Dict[str, Any]:
        """Gateway 생성 (IAM 인증)"""
        try:
            # 기존 Gateway 삭제
            await self._delete_existing_gateway(gateway_name)

            # Gateway description: 사용자가 입력한 MCP description 사용, 없으면 기본값
            gateway_description = description or f'Dedicated Gateway for {gateway_name}'

            # Build protocol configuration
            protocol_config = {}
            if enable_semantic_search:
                protocol_config = {
                    'mcp': {
                        'searchType': 'SEMANTIC'
                    }
                }
                print(f"   Semantic search enabled for gateway: {gateway_name}")

            # Build gateway creation params
            create_params = {
                'name': gateway_name,
                'roleArn': role_arn,
                'protocolType': 'MCP',
                'authorizerType': 'AWS_IAM',
                'description': gateway_description
            }

            # Add protocol configuration if semantic search is enabled
            if protocol_config:
                create_params['protocolConfiguration'] = protocol_config

            # Gateway 생성 (IAM 인증)
            gateway = self.gateway_client.create_gateway(**create_params)

            return gateway

        except Exception as e:
            raise Exception(f"Gateway 생성 실패: {str(e)}")

    async def _fix_iam_permissions(self, gateway_id: str, role_arn: str):
        """Gateway가 Target을 호출할 수 있도록 IAM 권한 추가 (Task 3)"""
        role_name = role_arn.split("/")[-1]

        policy_document = {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:InvokeGatewayTarget",
                    "bedrock-agentcore:GetGatewayTarget"
                ],
                "Resource": f"arn:aws:bedrock-agentcore:*:*:gateway/{gateway_id}/*"
            }]
        }

        try:
            self.iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName="GatewayTargetAccess",
                PolicyDocument=json.dumps(policy_document)
            )
        except Exception as e:
            raise Exception(f"IAM 권한 수정 실패: {str(e)}")

    async def _delete_existing_gateway(self, gateway_name: str):
        """기존 Gateway 삭제"""
        try:
            gateways = self.gateway_client.list_gateways().get('items', [])
            for gw in gateways:
                if gw['name'] == gateway_name:
                    gateway_id = gw['gatewayId']

                    # Target들 먼저 삭제
                    targets = self.gateway_client.list_gateway_targets(
                        gatewayIdentifier=gateway_id
                    ).get('items', [])

                    for target in targets:
                        self.gateway_client.delete_gateway_target(
                            gatewayIdentifier=gateway_id,
                            targetId=target['targetId']
                        )

                    await asyncio.sleep(3)

                    # Gateway 삭제
                    self.gateway_client.delete_gateway(gatewayIdentifier=gateway_id)
                    await asyncio.sleep(3)
                    break
        except Exception:
            pass  # 기존 Gateway 없으면 무시

    async def _wait_for_gateway_ready(self, gateway_id: str, max_attempts: int = 60):
        """Gateway가 READY 상태가 될 때까지 대기"""
        for attempt in range(max_attempts):
            try:
                response = self.gateway_client.get_gateway(gatewayIdentifier=gateway_id)
                status = response['status']

                if status == 'READY':
                    return
                elif status in ['CREATE_FAILED', 'DELETE_FAILED']:
                    raise Exception(f"Gateway 생성 실패: {status}")

                await asyncio.sleep(5)
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise Exception(f"Gateway 상태 확인 실패: {str(e)}")
                await asyncio.sleep(5)

        raise Exception("Gateway READY 상태 대기 시간 초과")

    def _sanitize_api_target_name(self, api_target) -> str:
        """API Target 이름을 AWS 규칙에 맞게 변환

        AWS 정규식 패턴 준수: ([0-9a-zA-Z][-]?){1,100}
        - ASCII 영문자, 숫자, 하이픈만 허용
        - API Catalog의 name 필드가 이미 영문 (예: flight-booking)이므로 직접 사용
        - 혹시 비ASCII 문자가 있으면 endpoint path로 fallback

        Args:
            api_target: APITarget 객체 (name, endpoint, method 속성 포함)

        Returns:
            str: 유효한 AWS Target 이름
        """
        from urllib.parse import urlparse

        # 1차 시도: 원본 이름에서 sanitize (이미 영문이어야 함)
        name = api_target.name.replace(' ', '-').replace('_', '-').lower()
        name = ''.join(c for c in name if c.isascii() and (c.isalnum() or c == '-'))
        name = re.sub(r'-+', '-', name)
        name = name.strip('-')

        # 영문 이름이 유효하면 그대로 사용
        if len(name) >= 3:
            return name[:100]

        # 2차 시도 (fallback): endpoint URL에서 path 추출하여 이름 생성
        endpoint = getattr(api_target, 'endpoint', '') or ''
        method = getattr(api_target, 'method', 'get') or 'get'

        if endpoint:
            try:
                parsed = urlparse(endpoint)
                path_parts = [p for p in parsed.path.split('/') if p]
                if path_parts:
                    path_name = '-'.join(path_parts[-2:]) if len(path_parts) >= 2 else path_parts[-1]
                    path_name = path_name.lower()
                    path_name = ''.join(c for c in path_name if c.isascii() and (c.isalnum() or c == '-'))
                    path_name = re.sub(r'-+', '-', path_name).strip('-')

                    if len(path_name) >= 2:
                        target_name = f"{method.lower()}-{path_name}"
                        return target_name[:100]
            except Exception:
                pass

        # 3차 시도: api_id 사용
        api_id = getattr(api_target, 'api_id', '') or ''
        if api_id:
            short_id = api_id.replace('-', '')[:8]
            return f"{method.lower()}-api-{short_id}"[:100]

        # 최후의 수단: 랜덤 suffix
        import uuid
        suffix = uuid.uuid4().hex[:6]
        return f"{method.lower()}-api-{suffix}"[:100]

    async def _create_api_targets_and_tools(self, gateway_id: str, mcp: InternalCreateMCP):
        """REST API Targets 생성 및 Tools 추가"""
        print(f"🎯 Creating API targets for gateway: {gateway_id}")
        print(f"📊 Number of targets to create: {len(mcp.selected_api_targets)}")

        for api_target in mcp.selected_api_targets:
            # 개선된 이름 생성 로직 사용
            target_name = self._sanitize_api_target_name(api_target)

            print(f"📝 Creating target: {api_target.name} → {target_name}")

            # OpenAPI Schema에서 description 추출
            target_description = api_target.openapi_schema.get('info', {}).get('description', api_target.name)

            # OpenAPI Schema를 JSON 문자열로 변환
            target_config = {
                "mcp": {
                    "openApiSchema": {
                        "inlinePayload": json.dumps(api_target.openapi_schema)
                    }
                }
            }

            try:
                # Determine credential provider based on auth_type
                if api_target.auth_type == "oauth":
                    # Use Amadeus OAuth provider for OAuth-authenticated APIs
                    oauth_provider_arn = await self._get_or_create_amadeus_oauth_provider()
                    credential_config = [{
                        "credentialProviderType": "OAUTH",
                        "credentialProvider": {
                            "oauthCredentialProvider": {
                                "providerArn": oauth_provider_arn,
                                "scopes": []  # Amadeus uses client_credentials with no specific scopes
                            }
                        }
                    }]
                    print(f"🔐 Using OAuth provider for {target_name}: {oauth_provider_arn}")
                else:
                    # Use API_KEY provider for API key authenticated APIs
                    api_key_provider_arn = await self._get_or_create_api_key_provider()
                    credential_config = [{
                        "credentialProviderType": "API_KEY",
                        "credentialProvider": {
                            "apiKeyCredentialProvider": {
                                "providerArn": api_key_provider_arn,
                                "credentialLocation": "HEADER",
                                "credentialParameterName": "apikey"
                            }
                        }
                    }]
                    print(f"🔑 Using API_KEY provider for {target_name}: {api_key_provider_arn}")

                # Target 생성
                response = self.gateway_client.create_gateway_target(
                    gatewayIdentifier=gateway_id,
                    name=target_name,
                    description=target_description,
                    targetConfiguration=target_config,
                    credentialProviderConfigurations=credential_config
                )
                target_id = response.get('targetId')
                print(f"✅ Target created successfully: {target_name} (ID: {target_id})")

                # OpenAPI Schema에서 Tool 생성 (MCP Protocol 표준)
                tools = self._extract_tools_from_openapi(api_target.openapi_schema, target_name)
                for tool in tools:
                    mcp.add_tool(tool)
                    print(f"✅ Added tool: {tool.name}")

            except Exception as e:
                print(f"❌ Target creation failed: {target_name}")
                raise Exception(f"Target 생성 실패 ({target_name}): {str(e)}")

        print(f"🎉 Completed. Total tools: {len(mcp.tool_list)}")

    def _extract_tools_from_openapi(self, openapi_schema: dict, api_name: str) -> List[Tool]:
        """OpenAPI Schema에서 Tool 추출

        하나의 OpenAPI Schema = 하나의 Tool
        여러 paths가 있는 경우 endpoints 배열에 각 endpoint 정보를 담습니다.

        Args:
            openapi_schema: OpenAPI 3.0 Schema
            api_name: API 이름 (Tool name으로 사용, 이미 sanitized된 target name)

        Returns:
            List[Tool]: 단일 Tool을 담은 리스트 (하나의 API = 하나의 Tool)
        """
        # Extract base URL from servers
        base_url = openapi_schema.get('servers', [{}])[0].get('url', '')

        # Extract auth type from security schemes
        auth_type = 'none'
        components = openapi_schema.get('components', {})
        security_schemes = components.get('securitySchemes', {})
        if security_schemes:
            first_scheme = list(security_schemes.values())[0]
            scheme_type = first_scheme.get('type', '').lower()
            if scheme_type == 'oauth2':
                auth_type = 'oauth'
            elif scheme_type == 'apikey':
                auth_type = 'api_key'

        # Tool 기본 정보
        tool_name = api_name
        api_description = openapi_schema.get('info', {}).get('description', '')

        # 모든 paths에서 endpoint 정보 수집
        tool_endpoints = []
        first_input_schema = None
        first_method = None
        first_responses = None

        for path, methods in openapi_schema.get('paths', {}).items():
            for method, operation in methods.items():
                if method.lower() not in ['get', 'post', 'put', 'delete', 'patch']:
                    continue

                # Endpoint summary
                summary = operation.get('summary') or operation.get('description') or f"{method.upper()} {path}"

                # inputSchema 생성 (JSON Schema 형식)
                input_schema = {
                    "type": "object",
                    "properties": {},
                    "required": []
                }

                # Path parameters
                for param in operation.get('parameters', []):
                    if param.get('in') == 'path':
                        param_name = param.get('name')
                        param_schema = param.get('schema', {'type': 'string'})
                        input_schema['properties'][param_name] = {
                            **param_schema,
                            'description': param.get('description', '')
                        }
                        if param.get('required', False):
                            input_schema['required'].append(param_name)

                # Query parameters
                for param in operation.get('parameters', []):
                    if param.get('in') == 'query':
                        param_name = param.get('name')
                        param_schema = param.get('schema', {'type': 'string'})
                        input_schema['properties'][param_name] = {
                            **param_schema,
                            'description': param.get('description', '')
                        }
                        if param.get('required', False):
                            input_schema['required'].append(param_name)

                # Request body
                request_body = operation.get('requestBody')
                if request_body:
                    content = request_body.get('content', {})
                    json_content = content.get('application/json', {})
                    body_schema = json_content.get('schema', {})
                    if body_schema:
                        input_schema['properties']['body'] = body_schema
                        if request_body.get('required', False):
                            input_schema['required'].append('body')

                # Responses
                responses = operation.get('responses', {})

                # ToolEndpoint 생성
                tool_endpoint = ToolEndpoint(
                    method=method.upper(),
                    path=path,
                    summary=summary,
                    input_schema=input_schema,
                    responses=responses if responses else None
                )
                tool_endpoints.append(tool_endpoint)

                # 첫 번째 endpoint 정보 저장 (backward compatibility)
                if first_input_schema is None:
                    first_input_schema = input_schema
                    first_method = method.upper()
                    first_responses = responses

        # Tool이 없으면 빈 리스트 반환
        if not tool_endpoints:
            return []

        # 단일 Tool 생성 (모든 endpoints 포함)
        tool = Tool(
            name=tool_name,
            description=api_description or tool_endpoints[0].summary,
            input_schema=first_input_schema,
            endpoints=tool_endpoints,
            responses=first_responses if first_responses else None,
            method=first_method,
            endpoint=base_url,
            auth_type=auth_type
        )

        return [tool]

    async def _fetch_tools_from_gateway(
        self,
        gateway_url: str,
        max_retries: int = 5,
        target_prefix: str = None
    ) -> List[Tool]:
        """Gateway에서 Tool 목록 조회 (IAM Sigv4 인증)

        Internal Deploy, External MCP에서 사용
        Gateway에 tools/list 요청을 보내고 응답을 파싱하여 Tool 객체 생성

        Args:
            gateway_url: Gateway 엔드포인트 URL
            max_retries: 최대 재시도 횟수 (Target 전파 대기용)
            target_prefix: 필터링할 Target name prefix (공유 Gateway에서 특정 Target의 tools만 가져올 때 사용)

        Returns:
            List[Tool]: MCP Protocol 표준 Tool 목록

        Raises:
            Exception: Gateway 호출 실패 또는 응답 파싱 실패
        """
        print(f"🔍 Fetching tools from gateway (IAM Sigv4): {gateway_url}")
        if target_prefix:
            print(f"   Filtering by target prefix: {target_prefix}___")

        try:
            # MCP Protocol tools/list 요청
            payload = {
                "jsonrpc": "2.0",
                "id": "list-tools",
                "method": "tools/list"
            }

            tools = []
            for attempt in range(max_retries):
                # SigV4 서명으로 Gateway 호출
                response = await self._call_gateway_with_sigv4(gateway_url, payload)

                # 응답 검증
                if 'result' not in response:
                    raise Exception(f"Invalid MCP Protocol response: {response}")

                if 'tools' not in response['result']:
                    raise Exception(f"No tools in response: {response}")

                tools_data = response['result']['tools']

                if tools_data:
                    # Tool 객체 생성
                    for tool_data in tools_data:
                        raw_name = tool_data['name']

                        # target_prefix가 지정된 경우 해당 prefix로 시작하는 tools만 필터링
                        if target_prefix:
                            if not raw_name.startswith(f"{target_prefix}___"):
                                continue

                        # Gateway가 추가한 "{target_name}___" prefix 제거
                        if '___' in raw_name:
                            tool_name = raw_name.split('___', 1)[1]
                        else:
                            tool_name = raw_name

                        tool = Tool(
                            name=tool_name,
                            description=tool_data.get('description', ''),
                            input_schema=tool_data.get('inputSchema', {})
                        )
                        tools.append(tool)
                        print(f"✅ Fetched tool: {raw_name} → {tool_name}")

                    # target_prefix가 지정된 경우 해당 Target의 tools가 있으면 성공
                    if target_prefix and len(tools) > 0:
                        break
                    # target_prefix가 없으면 기존 로직대로 처리
                    elif not target_prefix:
                        break

                # Tools가 비어있거나 target_prefix 필터링 후 비어있으면 재시도
                if len(tools) == 0:
                    if attempt < max_retries - 1:
                        print(f"⏳ Tools empty, waiting for Target propagation... (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(10)
                    else:
                        print(f"⚠️ No tools found after {max_retries} attempts")

            print(f"🎉 Total tools fetched: {len(tools)}")
            return tools

        except Exception as e:
            print(f"❌ Failed to fetch tools from gateway: {str(e)}")
            raise Exception(f"Gateway Tool 조회 실패 (IAM): {str(e)}")

    async def _call_gateway_with_sigv4(self, url: str, payload: dict) -> dict:
        """SigV4 서명으로 Gateway 호출

        AWS Signature Version 4를 사용하여 Gateway에 인증된 요청 전송

        Args:
            url: Gateway 엔드포인트 URL
            payload: MCP Protocol 요청 페이로드

        Returns:
            dict: MCP Protocol 응답

        Raises:
            Exception: HTTP 요청 실패 또는 인증 실패
        """
        import requests
        from botocore.auth import SigV4Auth
        from botocore.awsrequest import AWSRequest

        print(f"🔐 Calling gateway with SigV4: {url}")

        try:
            # AWS 자격 증명 가져오기
            # If credentials are empty, boto3 will use AWS_PROFILE from environment
            session_kwargs = {'region_name': self.region}
            if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                session_kwargs['aws_access_key_id'] = settings.AWS_ACCESS_KEY_ID
                session_kwargs['aws_secret_access_key'] = settings.AWS_SECRET_ACCESS_KEY

            session = boto3.Session(**session_kwargs)
            credentials = session.get_credentials()

            if not credentials:
                raise Exception("AWS credentials not found")

            # HTTP 요청 준비
            request = AWSRequest(
                method='POST',
                url=url,
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'}
            )

            # SigV4 서명 추가
            SigV4Auth(credentials, 'bedrock-agentcore', self.region).add_auth(request)

            # 실제 HTTP 요청
            response = requests.post(
                url,
                headers=dict(request.headers),
                data=request.body,
                timeout=30
            )

            # 응답 확인
            response.raise_for_status()

            result = response.json()
            print(f"✅ Gateway call successful")
            return result

        except requests.exceptions.RequestException as e:
            print(f"❌ HTTP request failed: {str(e)}")
            raise Exception(f"Gateway HTTP 요청 실패: {str(e)}")
        except Exception as e:
            print(f"❌ Gateway call failed: {str(e)}")
            raise Exception(f"Gateway 호출 실패: {str(e)}")

    async def update_dedicated_gateway(self, mcp: MCP) -> None:
        """전용 Gateway 업데이트 (Diff 기반)

        기존 타겟과 새 타겯을 비교하여:
        - 추가된 타겟만 생성
        - 삭제된 타겟만 삭제
        - 기존 타겯은 유지
        """
        if not isinstance(mcp, InternalCreateMCP):
            return

        gateway_name = f"{mcp.name}-gateway-{settings.ENVIRONMENT}"

        print(f"🔄 Updating Gateway: {gateway_name}")
        print(f"   - MCP Description: {mcp.description}")

        try:
            # 1. Gateway 찾기
            gateways = self.gateway_client.list_gateways().get('items', [])
            gateway_id = None
            for gw in gateways:
                if gw['name'] == gateway_name:
                    gateway_id = gw['gatewayId']
                    break

            if not gateway_id:
                raise Exception(f"Gateway not found: {gateway_name}")

            # 2. Gateway 상세 정보 조회 (roleArn 가져오기)
            gateway_details = self.gateway_client.get_gateway(gatewayIdentifier=gateway_id)
            role_arn = gateway_details['roleArn']

            # 3. Gateway description 업데이트
            # Note: update_gateway는 name, roleArn, authorizerType, protocolType을 필수로 요구함
            self.gateway_client.update_gateway(
                gatewayIdentifier=gateway_id,
                name=gateway_name,  # Gateway 이름 유지
                roleArn=role_arn,  # 기존 Gateway의 role 유지
                authorizerType='AWS_IAM',  # 생성 시와 동일한 인증 타입 유지
                protocolType='MCP',  # 생성 시와 동일한 프로토콜 타입 유지
                description=mcp.description or f'Dedicated Gateway for {gateway_name}'
            )
            print(f"✅ Gateway description updated")

            # 4. Gateway READY 상태 대기 (업데이트 완료 후)
            await self._wait_for_gateway_ready(gateway_id)
            print(f"✅ Gateway is ready after update")

            # 5. 기존 Target 목록 조회
            existing_targets = self.gateway_client.list_gateway_targets(
                gatewayIdentifier=gateway_id
            ).get('items', [])

            # 기존 타겯을 api_id로 매핑 (api_id가 없으면 name으로)
            existing_target_map = {}  # api_id 또는 name -> target
            for target in existing_targets:
                # Target name에서 api_id 추출 시도 (naming convention에 따라)
                target_name = target['name']
                existing_target_map[target_name] = target

            print(f"📋 Existing targets: {list(existing_target_map.keys())}")

            # 6. 새 타겯 목록에서 sanitized name 생성
            new_target_names = set()
            new_targets_to_create = []

            for api_target in mcp.selected_api_targets:
                # 개선된 이름 생성 로직 사용 (생성 시와 동일)
                target_name = self._sanitize_api_target_name(api_target)

                new_target_names.add(target_name)

                # 기존에 없는 타겯만 생성 대상에 추가
                if target_name not in existing_target_map:
                    new_targets_to_create.append(api_target)

            print(f"📋 New targets: {new_target_names}")

            # 7. 삭제할 타겟 식별 (기존에 있지만 새 목록에 없는 것)
            targets_to_delete = []
            for target_name, target in existing_target_map.items():
                if target_name not in new_target_names:
                    targets_to_delete.append(target)

            print(f"🗑️  Targets to delete: {[t['name'] for t in targets_to_delete]}")
            print(f"➕ Targets to create: {[t.name for t in new_targets_to_create]}")

            # 8. 삭제할 타겟 삭제
            for target in targets_to_delete:
                try:
                    self.gateway_client.delete_gateway_target(
                        gatewayIdentifier=gateway_id,
                        targetId=target['targetId']
                    )
                    print(f"🗑️  Deleted target: {target['name']}")
                except Exception as e:
                    print(f"⚠️  Failed to delete target {target['name']}: {e}")

            # 9. Gateway READY 상태 대기 (삭제 후)
            if len(targets_to_delete) > 0:
                await self._wait_for_gateway_ready(gateway_id)
                print(f"✅ Gateway is ready after target deletion")

            # 10. 기존 Tool 목록 초기화 (새로 생성할 것들만 반영하기 위해)
            mcp.clear_tools()
            print(f"🧹 Cleared existing tools")

            # 11. 기존 유지 타겟의 Tool 정보 복원 (삭제되지 않은 것들)
            for api_target in mcp.selected_api_targets:
                # 개선된 이름 생성 로직 사용 (생성 시와 동일)
                target_name = self._sanitize_api_target_name(api_target)

                if target_name in existing_target_map and target_name in new_target_names:
                    # 기존 타겯 유지 - Tool 정보 복원
                    tools = self._extract_tools_from_openapi(api_target.openapi_schema, target_name)
                    for tool in tools:
                        mcp.add_tool(tool)
                    print(f"♻️  Retained existing target: {target_name} ({len(tools)} tools)")

            # 12. 새 타겯만 생성
            if len(new_targets_to_create) > 0:
                print(f"🎯 Creating {len(new_targets_to_create)} new targets")
                # 임시로 mcp의 selected_api_targets를 새 타겯만으로 교체
                original_targets = mcp.selected_api_targets
                mcp._selected_api_targets = new_targets_to_create
                await self._create_api_targets_and_tools(gateway_id, mcp)
                # 원래 타겟 목록 복원
                mcp._selected_api_targets = original_targets

            print(f"🎉 Gateway update completed: {gateway_name}")

        except Exception as e:
            print(f"❌ Gateway update failed: {str(e)}")
            raise Exception(f"Gateway 업데이트 실패: {str(e)}")

    async def add_to_shared_gateway(self, mcp: MCP) -> str:
        """공유 Gateway에 추가 (미구현)"""
        raise NotImplementedError("공유 Gateway는 아직 지원하지 않습니다")

    # ============================================================
    # Cognito OAuth Infrastructure Methods (Shared by Mixins)
    # ============================================================

    async def _get_or_create_oauth_provider(self) -> str:
        """공유 OAuth2 Credential Provider 조회 또는 생성

        Returns:
            str: OAuth2 Credential Provider ARN
        """
        if self._oauth_provider_arn:
            return self._oauth_provider_arn

        print("🔐 OAuth2 Credential Provider 확인 중...")

        # 1. Cognito 인프라 준비
        cognito_info = await self.cognito_service.get_or_create_shared_infrastructure()

        # 2. M2M 클라이언트 조회/생성 (Gateway용)
        client_id, client_secret = await self.cognito_service.get_or_create_m2m_client(
            client_name="mcp-gateway-oauth-client"
        )

        # 3. 기존 OAuth Provider 조회
        try:
            providers = self.gateway_client.list_oauth2_credential_providers()
            for provider in providers.get('credentialProviders', []):
                if provider.get('name') == settings.OAUTH_PROVIDER_NAME:
                    self._oauth_provider_arn = provider['credentialProviderArn']
                    print(f"♻️ 기존 OAuth Provider 사용: {self._oauth_provider_arn}")
                    return self._oauth_provider_arn
        except Exception as e:
            print(f"⚠️ OAuth Provider 목록 조회 실패: {e}")

        # 4. 새 OAuth Provider 생성
        print("🆕 새 OAuth2 Credential Provider 생성 중...")
        try:
            response = self.gateway_client.create_oauth2_credential_provider(
                name=settings.OAUTH_PROVIDER_NAME,
                credentialProviderVendor='CustomOauth2',
                oauth2ProviderConfigInput={
                    'customOauth2ProviderConfig': {
                        'oauthDiscovery': {
                            'discoveryUrl': cognito_info['discovery_url']
                        },
                        'clientId': client_id,
                        'clientSecret': client_secret
                    }
                }
            )
            self._oauth_provider_arn = response['credentialProviderArn']
            print(f"✅ OAuth Provider 생성 완료: {self._oauth_provider_arn}")
            return self._oauth_provider_arn

        except Exception as e:
            raise Exception(f"OAuth2 Credential Provider 생성 실패: {str(e)}")

    # ============================================================
    # Amadeus API OAuth Provider (for Internal MCP API targets)
    # ============================================================

    _amadeus_oauth_provider_arn: str = None  # 캐시

    async def _get_or_create_amadeus_oauth_provider(self) -> str:
        """Amadeus API용 OAuth2 Credential Provider 조회 또는 생성

        환경 변수 기반 자동 관리:
        - AMADEUS_OAUTH_CREDENTIAL_PROVIDER_ARN이 설정되어 있으면 그 값 사용
        - 없으면 AMADEUS_API_KEY, AMADEUS_API_SECRET, AMADEUS_TOKEN_URL로 새로 생성

        Returns:
            str: OAuth2 Credential Provider ARN
        """
        # 캐시 확인
        if self._amadeus_oauth_provider_arn:
            return self._amadeus_oauth_provider_arn

        print("🔐 Amadeus OAuth2 Credential Provider 확인 중...")

        # 1. 환경 변수에 ARN이 이미 있는 경우
        if settings.AMADEUS_OAUTH_CREDENTIAL_PROVIDER_ARN:
            # 실제 존재하는지 확인
            try:
                providers = self.gateway_client.list_oauth2_credential_providers()
                for provider in providers.get('credentialProviders', []):
                    if provider.get('credentialProviderArn') == settings.AMADEUS_OAUTH_CREDENTIAL_PROVIDER_ARN:
                        self._amadeus_oauth_provider_arn = settings.AMADEUS_OAUTH_CREDENTIAL_PROVIDER_ARN
                        print(f"♻️ 기존 Amadeus OAuth Provider 사용 (from env): {self._amadeus_oauth_provider_arn}")
                        return self._amadeus_oauth_provider_arn
            except Exception as e:
                print(f"⚠️ OAuth Provider 조회 실패, 새로 생성 시도: {e}")

        # 2. 이름으로 기존 Provider 조회
        try:
            providers = self.gateway_client.list_oauth2_credential_providers()
            for provider in providers.get('credentialProviders', []):
                if provider.get('name') == settings.AMADEUS_OAUTH_PROVIDER_NAME:
                    self._amadeus_oauth_provider_arn = provider['credentialProviderArn']
                    print(f"♻️ 기존 Amadeus OAuth Provider 발견: {self._amadeus_oauth_provider_arn}")
                    return self._amadeus_oauth_provider_arn
        except Exception as e:
            print(f"⚠️ OAuth Provider 목록 조회 실패: {e}")

        # 3. 환경 변수에 API 키가 없으면 에러
        if not settings.AMADEUS_API_KEY or not settings.AMADEUS_API_SECRET:
            raise Exception(
                "Amadeus OAuth Provider를 생성하려면 AMADEUS_API_KEY와 AMADEUS_API_SECRET이 필요합니다. "
                ".env 파일에 설정하거나 AMADEUS_OAUTH_CREDENTIAL_PROVIDER_ARN을 설정하세요."
            )

        # 4. 새 OAuth Provider 생성
        print("🆕 새 Amadeus OAuth2 Credential Provider 생성 중...")
        try:
            response = self.gateway_client.create_oauth2_credential_provider(
                name=settings.AMADEUS_OAUTH_PROVIDER_NAME,
                credentialProviderVendor='CustomOauth2',
                oauth2ProviderConfigInput={
                    'customOauth2ProviderConfig': {
                        'oauthDiscovery': {
                            'authorizationServerMetadata': {
                                'issuer': 'https://test.api.amadeus.com',
                                'authorizationEndpoint': 'https://test.api.amadeus.com/v1/security/oauth2/authorize',
                                'tokenEndpoint': settings.AMADEUS_TOKEN_URL
                            }
                        },
                        'clientId': settings.AMADEUS_API_KEY,
                        'clientSecret': settings.AMADEUS_API_SECRET
                    }
                }
            )
            self._amadeus_oauth_provider_arn = response['credentialProviderArn']
            print(f"✅ Amadeus OAuth Provider 생성 완료: {self._amadeus_oauth_provider_arn}")
            print(f"💡 TIP: .env에 다음을 추가하면 재사용됩니다:")
            print(f"   AMADEUS_OAUTH_CREDENTIAL_PROVIDER_ARN={self._amadeus_oauth_provider_arn}")
            return self._amadeus_oauth_provider_arn

        except Exception as e:
            raise Exception(f"Amadeus OAuth2 Credential Provider 생성 실패: {str(e)}")

    # ============================================================
    # APIGEE API Key Provider (for Internal MCP API targets)
    # ============================================================

    _api_key_provider_arn: str = None  # 캐시

    async def _get_or_create_api_key_provider(self) -> str:
        """API Key Credential Provider 조회 또는 생성

        환경 변수 기반 자동 관리:
        - APIGEE_KEY_CREDENTIAL_PROVIDER_ARN이 설정되어 있으면 그 값 사용
        - 없으면 APIGEE_API_KEY로 새로 생성

        Returns:
            str: API Key Credential Provider ARN
        """
        # 캐시 확인
        if self._api_key_provider_arn:
            return self._api_key_provider_arn

        print("🔐 API Key Credential Provider 확인 중...")

        # 1. 환경 변수에 ARN이 이미 있는 경우
        if settings.APIGEE_KEY_CREDENTIAL_PROVIDER_ARN:
            # 실제 존재하는지 확인
            try:
                providers = self.gateway_client.list_api_key_credential_providers()
                for provider in providers.get('credentialProviders', []):
                    if provider.get('credentialProviderArn') == settings.APIGEE_KEY_CREDENTIAL_PROVIDER_ARN:
                        self._api_key_provider_arn = settings.APIGEE_KEY_CREDENTIAL_PROVIDER_ARN
                        print(f"♻️ 기존 API Key Provider 사용 (from env): {self._api_key_provider_arn}")
                        return self._api_key_provider_arn
            except Exception as e:
                print(f"⚠️ API Key Provider 조회 실패, 새로 생성 시도: {e}")

        # 2. 이름으로 기존 Provider 조회
        try:
            providers = self.gateway_client.list_api_key_credential_providers()
            for provider in providers.get('credentialProviders', []):
                if provider.get('name') == settings.APIGEE_API_KEY_PROVIDER_NAME:
                    self._api_key_provider_arn = provider['credentialProviderArn']
                    print(f"♻️ 기존 API Key Provider 발견: {self._api_key_provider_arn}")
                    return self._api_key_provider_arn
        except Exception as e:
            print(f"⚠️ API Key Provider 목록 조회 실패: {e}")

        # 3. 환경 변수에 API Key가 없으면 에러
        if not settings.APIGEE_API_KEY:
            raise Exception(
                "API Key Provider를 생성하려면 APIGEE_API_KEY가 필요합니다. "
                ".env 파일에 설정하거나 APIGEE_KEY_CREDENTIAL_PROVIDER_ARN을 설정하세요."
            )

        # 4. 새 API Key Provider 생성
        print("🆕 새 API Key Credential Provider 생성 중...")
        try:
            response = self.gateway_client.create_api_key_credential_provider(
                name=settings.APIGEE_API_KEY_PROVIDER_NAME,
                apiKey=settings.APIGEE_API_KEY
            )
            self._api_key_provider_arn = response['credentialProviderArn']
            print(f"✅ API Key Provider 생성 완료: {self._api_key_provider_arn}")
            print(f"💡 TIP: .env에 다음을 추가하면 재사용됩니다:")
            print(f"   APIGEE_KEY_CREDENTIAL_PROVIDER_ARN={self._api_key_provider_arn}")
            return self._api_key_provider_arn

        except Exception as e:
            raise Exception(f"API Key Credential Provider 생성 실패: {str(e)}")

    async def _get_cognito_auth_config(self) -> Dict[str, Any]:
        """Cognito JWT 인증 설정 반환 (Gateway/Runtime용)

        Note: Cognito client_credentials 플로우로 발급된 토큰에는 'aud' 클레임이 없습니다.
        AWS customJWTAuthorizer에서 allowedAudience를 설정하면 'aud' 클레임을 검증하므로,
        Cognito M2M 토큰을 사용할 때는 allowedAudience를 생략하고 allowedClients만 사용합니다.
        """
        # Cognito 인프라가 초기화되지 않은 경우 자동 초기화
        if not self.cognito_service._user_pool_id:
            print("🔐 Cognito 인프라 자동 초기화 중...")
            await self.cognito_service.get_or_create_shared_infrastructure()

        discovery_url = self.cognito_service.get_discovery_url()

        # M2M 클라이언트 ID 가져오기
        client_id, _ = await self.cognito_service.get_or_create_m2m_client(
            client_name="mcp-gateway-oauth-client"
        )

        # Cognito M2M tokens (client_credentials flow):
        # - 'aud' claim: Not present (DO NOT use allowedAudience)
        # - 'client_id' claim: Present (use allowedClients to validate)
        return {
            'customJWTAuthorizer': {
                'discoveryUrl': discovery_url,
                'allowedClients': [client_id]  # M2M 클라이언트 허용 (allowedAudience 생략)
            }
        }

    # ============================================================
    # Runtime Management Methods (Shared by Mixins)
    # ============================================================

    async def _create_runtime_role(self, mcp_name: str) -> str:
        """Runtime용 IAM 역할 생성"""
        role_name = f'{mcp_name}-runtime-role'

        # 권한 정책 (Runtime 전용): ECR 이미지 pull, CloudWatch Logs
        role_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "ecr:GetAuthorizationToken",
                        "ecr:BatchCheckLayerAvailability",
                        "ecr:GetDownloadUrlForLayer",
                        "ecr:BatchGetImage"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    "Resource": "arn:aws:logs:*:*:*"
                }
            ]
        }

        try:
            # 기존 역할 삭제
            await self._delete_existing_iam_role(role_name)

            # 새 역할 생성
            role = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(self._get_agentcore_assume_role_policy()),
                Description=f'AgentCore Runtime execution role for {mcp_name}'
            )

            # 권한 정책 연결
            self.iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName="RuntimePolicy",
                PolicyDocument=json.dumps(role_policy)
            )

            # IAM 역할 전파 대기
            await asyncio.sleep(10)

            return role['Role']['Arn']

        except Exception as e:
            raise Exception(f"Runtime IAM 역할 생성 실패: {str(e)}")

    async def _delete_existing_runtime(self, runtime_name: str, max_wait: int = 60):
        """기존 Runtime 삭제 및 완료 대기

        Args:
            runtime_name: 삭제할 Runtime 이름
            max_wait: 삭제 완료 최대 대기 시간 (초)
        """
        try:
            runtimes = self.gateway_client.list_agent_runtimes().get('agentRuntimes', [])
            runtime_id = None
            for runtime in runtimes:
                if runtime.get('agentRuntimeName') == runtime_name:
                    runtime_id = runtime['agentRuntimeId']
                    break

            if not runtime_id:
                print(f"ℹ️  No existing runtime found: {runtime_name}")
                return

            # Runtime 삭제 요청
            print(f"🗑️  Deleting existing runtime: {runtime_name} (ID: {runtime_id})")
            self.gateway_client.delete_agent_runtime(agentRuntimeId=runtime_id)

            # 삭제 완료 대기 (Runtime이 목록에서 사라질 때까지)
            for attempt in range(max_wait // 5):
                await asyncio.sleep(5)
                try:
                    # Runtime 상태 확인
                    response = self.gateway_client.get_agent_runtime(agentRuntimeId=runtime_id)
                    status = response.get('status')
                    print(f"   Runtime status: {status} (waiting for deletion...)")

                    if status == 'DELETED':
                        print(f"✅ Runtime deleted successfully: {runtime_name}")
                        return
                except self.gateway_client.exceptions.ResourceNotFoundException:
                    print(f"✅ Runtime deleted successfully: {runtime_name}")
                    return
                except Exception as e:
                    if 'not found' in str(e).lower() or 'ResourceNotFoundException' in str(e):
                        print(f"✅ Runtime deleted successfully: {runtime_name}")
                        return
                    print(f"   Waiting for runtime deletion... ({str(e)})")

            print(f"⚠️  Runtime deletion timeout, proceeding anyway: {runtime_name}")

        except Exception as e:
            print(f"⚠️  Failed to delete runtime (may not exist): {str(e)}")

    async def _wait_for_runtime_ready(self, runtime_id: str, max_attempts: int = 120) -> str:
        """Runtime이 READY 상태가 될 때까지 대기

        Returns:
            str: Runtime endpoint URL
        """
        import urllib.parse

        for attempt in range(max_attempts):
            try:
                response = self.gateway_client.get_agent_runtime(agentRuntimeId=runtime_id)
                status = response.get('status')

                if status == 'READY':
                    # Runtime endpoint URL 구성
                    # Format: https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT
                    runtime_arn = response.get('agentRuntimeArn')
                    encoded_arn = urllib.parse.quote(runtime_arn, safe='')
                    runtime_endpoint = f"https://bedrock-agentcore.{self.region}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
                    return runtime_endpoint
                elif status in ['FAILED', 'DELETE_FAILED']:
                    raise Exception(f"Runtime 생성 실패: {status}")

                print(f"   Runtime status: {status} (attempt {attempt + 1}/{max_attempts})")
                await asyncio.sleep(5)
            except Exception as e:
                if "not found" in str(e).lower() or attempt == max_attempts - 1:
                    raise Exception(f"Runtime 상태 확인 실패: {str(e)}")
                await asyncio.sleep(5)

        raise Exception("Runtime READY 상태 대기 시간 초과")

    # ============================================================
    # IAM Gateway Methods (Shared by Mixins)
    # ============================================================

    async def _create_gateway_with_iam(
        self,
        gateway_name: str,
        role_arn: str,
        description: str,
        auth_config: Dict[str, Any] = None,  # Deprecated, kept for compatibility
        enable_semantic_search: bool = False
    ) -> Dict[str, Any]:
        """Gateway 생성 (IAM Authorizer)

        Args:
            gateway_name: Gateway 이름
            role_arn: Gateway IAM 역할 ARN
            description: Gateway 설명
            auth_config: Deprecated - 더 이상 사용되지 않음 (IAM 인증 사용)
            enable_semantic_search: Semantic Search 활성화 여부

        Returns:
            Dict: Gateway 정보 {'gatewayId': str, 'gatewayUrl': str, ...}
        """
        try:
            # 기존 Gateway 삭제
            await self._delete_existing_gateway(gateway_name)

            gateway_description = description or f'Dedicated Gateway for {gateway_name}'

            # Build protocol configuration
            protocol_config = {}
            if enable_semantic_search:
                protocol_config = {
                    'mcp': {
                        'searchType': 'SEMANTIC'
                    }
                }
                print(f"   Semantic search enabled for gateway: {gateway_name}")

            # Build gateway creation params (IAM 인증)
            create_params = {
                'name': gateway_name,
                'roleArn': role_arn,
                'protocolType': 'MCP',
                'authorizerType': 'AWS_IAM',
                'description': gateway_description
            }

            # Add protocol configuration if semantic search is enabled
            if protocol_config:
                create_params['protocolConfiguration'] = protocol_config

            gateway = self.gateway_client.create_gateway(**create_params)

            return gateway

        except Exception as e:
            raise Exception(f"Gateway (IAM) 생성 실패: {str(e)}")

    async def _fetch_tools_from_gateway_with_jwt(
        self,
        gateway_url: str,
        max_retries: int = 5,
        target_prefix: str = None
    ) -> List[Tool]:
        """Gateway에서 Tool 목록 조회 (JWT 토큰 사용)

        Args:
            gateway_url: Gateway 엔드포인트 URL
            max_retries: 최대 재시도 횟수 (Target 전파 대기용)
            target_prefix: 필터링할 Target name prefix (공유 Gateway에서 특정 Target의 tools만 가져올 때 사용)

        Returns:
            List[Tool]: MCP Protocol 표준 Tool 목록
        """
        import requests

        print(f"🔍 Fetching tools from gateway (JWT): {gateway_url}")
        if target_prefix:
            print(f"   Filtering by target prefix: {target_prefix}___")

        try:
            # 1. M2M 클라이언트 정보 가져오기
            client_id, client_secret = await self.cognito_service.get_or_create_m2m_client(
                client_name="mcp-gateway-oauth-client"
            )

            # 2. JWT 토큰 획득
            token_response = await self.cognito_service.get_access_token(
                client_id=client_id,
                client_secret=client_secret
            )
            access_token = token_response.get('access_token')

            if not access_token:
                raise Exception("Failed to obtain access token")

            # 3. MCP Protocol tools/list 요청 (재시도 로직 포함)
            payload = {
                "jsonrpc": "2.0",
                "id": "list-tools",
                "method": "tools/list"
            }

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }

            tools = []
            for attempt in range(max_retries):
                response = requests.post(
                    gateway_url,
                    headers=headers,
                    data=json.dumps(payload),
                    timeout=60
                )

                response.raise_for_status()
                result = response.json()

                # 응답 검증
                if 'result' not in result:
                    raise Exception(f"Invalid MCP Protocol response: {result}")

                if 'tools' not in result['result']:
                    raise Exception(f"No tools in response: {result}")

                tools_data = result['result']['tools']

                if tools_data:
                    # Tool 객체 생성
                    for tool_data in tools_data:
                        # Gateway가 추가한 "{target_name}___" prefix 제거
                        raw_name = tool_data['name']

                        # target_prefix가 지정된 경우 해당 prefix로 시작하는 tools만 필터링
                        if target_prefix:
                            if not raw_name.startswith(f"{target_prefix}___"):
                                continue

                        if '___' in raw_name:
                            tool_name = raw_name.split('___', 1)[1]  # prefix 제거
                        else:
                            tool_name = raw_name

                        tool = Tool(
                            name=tool_name,
                            description=tool_data.get('description', ''),
                            input_schema=tool_data.get('inputSchema', {})
                        )
                        tools.append(tool)
                        print(f"✅ Fetched tool: {raw_name} → {tool_name}")

                    # target_prefix가 지정된 경우 해당 Target의 tools가 있으면 성공
                    if target_prefix and len(tools) > 0:
                        break
                    # target_prefix가 없으면 기존 로직대로 처리
                    elif not target_prefix:
                        break

                # Tools가 비어있거나 target_prefix 필터링 후 비어있으면 재시도
                if len(tools) == 0:
                    if attempt < max_retries - 1:
                        print(f"⏳ Tools empty, waiting for Target propagation... (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(10)
                    else:
                        print(f"⚠️ No tools found after {max_retries} attempts")

            print(f"🎉 Total tools fetched: {len(tools)}")
            return tools

        except Exception as e:
            print(f"❌ Failed to fetch tools: {str(e)}")
            raise Exception(f"Gateway Tool 조회 실패 (JWT): {str(e)}")

    # ============================================================
    # External MCP (Endpoint URL) Methods
    # ============================================================

    async def create_external_endpoint_target(self, mcp: ExternalEndpointMCP) -> tuple:
        """Endpoint URL 타입 External MCP 인프라 생성

        기존 MCP 서버 엔드포인트에 직접 연결하는 Gateway Target을 생성합니다.
        - 공유 Gateway (external-mcp-gateway)에 MCP Server Target 추가
        - no_auth: 공용 Cognito 사용
        - oauth: 선택한 User Pool 사용

        Args:
            mcp: ExternalEndpointMCP 엔티티

        Returns:
            tuple: (gateway_id, target_id)
        """
        print(f"🎯 Creating External Endpoint MCP infrastructure: {mcp.name}")
        print(f"   - Endpoint URL: {mcp.endpoint_url}")
        print(f"   - Auth Type: {mcp.auth_type.value}")

        # 1. OAuth Provider 조회/생성 (Cognito 인프라 초기화 포함)
        oauth_provider_arn = await self._get_or_create_oauth_provider()

        # 2. 공유 Gateway 조회/생성
        gateway_id = await self._get_or_create_external_gateway()

        # 3. Gateway READY 상태 대기
        await self._wait_for_gateway_ready(gateway_id)

        # 4. Gateway URL 조회
        gateway_info = self.gateway_client.get_gateway(gatewayIdentifier=gateway_id)
        gateway_url = gateway_info.get('gatewayUrl', '')

        # 5. Target 이름 생성
        target_name = f"{mcp.name}-mcp-server-target-{settings.ENVIRONMENT}"
        target_name = self._sanitize_target_name(target_name)

        # 6. MCP Server Target 생성
        print(f"📝 Creating MCP Server Target: {target_name}")

        # OAuth scopes 설정
        oauth_scopes = [
            f"{self.cognito_service.RESOURCE_SERVER_ID}/read",
            f"{self.cognito_service.RESOURCE_SERVER_ID}/write",
            f"{self.cognito_service.RESOURCE_SERVER_ID}/invoke"
        ]

        try:
            response = self.gateway_client.create_gateway_target(
                gatewayIdentifier=gateway_id,
                name=target_name,
                description=mcp.description or f'MCP Server Target for {mcp.name}',
                targetConfiguration={
                    'mcp': {
                        'mcpServer': {
                            'endpoint': mcp.endpoint_url
                        }
                    }
                },
                credentialProviderConfigurations=[{
                    'credentialProviderType': 'OAUTH',
                    'credentialProvider': {
                        'oauthCredentialProvider': {
                            'providerArn': oauth_provider_arn,
                            'scopes': oauth_scopes
                        }
                    }
                }]
            )
            target_id = response.get('targetId')

            print(f"✅ MCP Server Target created: {target_id}")
            print(f"   - Gateway URL: {gateway_url}")

            # MCP 엔티티 업데이트
            mcp.set_gateway_id(gateway_id)
            mcp.set_target_id(target_id)
            mcp.set_endpoint(gateway_url)

            # Gateway에서 tools 조회 (IAM Sigv4 인증, Target prefix로 필터링)
            tools = []
            try:
                # Target 생성 후 전파 대기
                await asyncio.sleep(5)

                tools = await self._fetch_tools_from_gateway(
                    gateway_url,
                    target_prefix=target_name
                )
                print(f"✅ Tools fetched: {len(tools)}")

                # MCP 엔티티에 tools 추가
                mcp.clear_tools()
                for tool in tools:
                    mcp.add_tool(tool)
            except Exception as e:
                print(f"⚠️ Failed to fetch tools (will be retried later): {str(e)}")

            return gateway_id, target_id, tools

        except Exception as e:
            print(f"❌ Target creation failed: {str(e)}")
            raise Exception(f"MCP Server Target 생성 실패: {str(e)}")

    async def update_external_endpoint_target(self, mcp: ExternalEndpointMCP) -> None:
        """Endpoint URL 타입 External MCP Target 업데이트

        기존 Target을 삭제하고 새로운 설정으로 재생성합니다.
        - 기존 Target 삭제
        - 새 Target 생성 (변경된 endpoint_url, auth_type 반영)
        - Tools 재조회

        Args:
            mcp: ExternalEndpointMCP 엔티티 (업데이트된 설정 포함)
        """
        print(f"🔄 Updating External Endpoint MCP Target: {mcp.name}")
        print(f"   - Endpoint URL: {mcp.endpoint_url}")
        print(f"   - Auth Type: {mcp.auth_type.value}")

        # 1. 기존 Target 삭제
        if mcp.gateway_id and mcp.target_id:
            try:
                self.gateway_client.delete_gateway_target(
                    gatewayIdentifier=mcp.gateway_id,
                    targetId=mcp.target_id
                )
                print(f"🗑️  Deleted existing target: {mcp.target_id}")
                await asyncio.sleep(3)  # Target 삭제 대기
            except Exception as e:
                print(f"⚠️ Failed to delete existing target (may not exist): {str(e)}")

        # 2. 새 Target 생성
        gateway_id, target_id, tools = await self.create_external_endpoint_target(mcp)

        print(f"✅ External Endpoint MCP Target updated: {target_id}")

    # ============================================================
    # External MCP (Container Image) Methods
    # ============================================================

    async def create_external_container_target(self, mcp: ExternalContainerMCP) -> tuple:
        """Container Image 타입 External MCP 인프라 생성

        ECR 이미지를 Runtime으로 배포 후 Gateway Target으로 연결합니다.
        - Runtime 생성 (ECR 이미지)
        - 공유 Gateway (external-mcp-gateway)에 Runtime Target 추가

        Args:
            mcp: ExternalContainerMCP 엔티티

        Returns:
            tuple: (gateway_id, target_id, runtime_id, runtime_url)
        """
        print(f"🎯 Creating External Container MCP infrastructure: {mcp.name}")
        print(f"   - ECR Repository: {mcp.ecr_repository}")
        print(f"   - Image Tag: {mcp.image_tag}")
        print(f"   - Auth Type: {mcp.auth_type.value}")

        # 1. Cognito 인프라 준비 (Runtime 인증용)
        print("🔐 Preparing Cognito infrastructure...")
        await self.cognito_service.get_or_create_shared_infrastructure()

        # 2. Runtime 생성
        runtime_name = self._sanitize_runtime_name(f"{mcp.name}-runtime-{settings.ENVIRONMENT}")
        print(f"🚀 Creating Runtime: {runtime_name}")

        # 기존 Runtime 삭제
        await self._delete_existing_runtime(runtime_name)

        # Runtime IAM 역할 생성
        runtime_role_arn = await self._create_runtime_role(f"{mcp.name}-{settings.ENVIRONMENT}")

        # JWT 인증 설정
        auth_config = await self._get_cognito_auth_config()

        # 환경변수 설정
        env_vars = mcp.environment.copy() if mcp.environment else {}

        # ECR 이미지 URI 구성
        ecr_uri = f"{self.account_id}.dkr.ecr.{self.region}.amazonaws.com/{mcp.ecr_repository}:{mcp.image_tag}"

        try:
            runtime_response = self.gateway_client.create_agent_runtime(
                agentRuntimeName=runtime_name,
                description=mcp.description or f'Runtime for {mcp.name}',
                roleArn=runtime_role_arn,
                agentRuntimeArtifact={
                    'containerConfiguration': {
                        'containerUri': ecr_uri,
                        'environmentVariables': env_vars
                    }
                },
                networkConfiguration={
                    'networkMode': 'PUBLIC'
                },
                protocolConfiguration={
                    'serverProtocol': 'MCP'
                },
                authorizerConfiguration=auth_config
            )
            runtime_id = runtime_response.get('agentRuntimeId')
            print(f"✅ Runtime created: {runtime_id}")

        except Exception as e:
            raise Exception(f"Runtime 생성 실패: {str(e)}")

        # 3. Runtime READY 대기
        print("⏳ Waiting for Runtime to be ready...")
        runtime_url = await self._wait_for_runtime_ready(runtime_id)
        print(f"✅ Runtime ready: {runtime_url}")

        # 4. 공유 Gateway 조회/생성
        gateway_id = await self._get_or_create_external_gateway()
        await self._wait_for_gateway_ready(gateway_id)

        # 5. Gateway Target 생성 (Runtime 연결)
        target_name = f"{mcp.name}-runtime-target-{settings.ENVIRONMENT}"
        target_name = self._sanitize_target_name(target_name)

        print(f"📝 Creating Runtime Target: {target_name}")

        try:
            # OAuth Provider 조회/생성
            oauth_provider_arn = await self._get_or_create_oauth_provider()

            target_response = self.gateway_client.create_gateway_target(
                gatewayIdentifier=gateway_id,
                name=target_name,
                description=mcp.description or f'Runtime Target for {mcp.name}',
                targetConfiguration={
                    'runtime': {
                        'runtimeUrl': runtime_url
                    }
                },
                credentialProviderConfigurations=[{
                    'credentialProviderType': 'OAUTH2',
                    'credentialProvider': {
                        'oauth2CredentialProvider': {
                            'providerArn': oauth_provider_arn
                        }
                    }
                }]
            )
            target_id = target_response.get('targetId')
            gateway_url = target_response.get('gatewayUrl', '')

            print(f"✅ Runtime Target created: {target_id}")

            # MCP 엔티티 업데이트
            mcp.set_gateway_id(gateway_id)
            mcp.set_target_id(target_id)
            mcp.set_runtime_id(runtime_id)
            mcp.set_runtime_url(runtime_url)
            mcp.set_endpoint(gateway_url)

            return gateway_id, target_id, runtime_id, runtime_url

        except Exception as e:
            print(f"❌ Target creation failed: {str(e)}")
            raise Exception(f"Runtime Target 생성 실패: {str(e)}")

    # ============================================================
    # External MCP Helper Methods
    # ============================================================

    async def _get_or_create_external_gateway(self) -> str:
        """공유 External MCP Gateway 조회 또는 생성

        Returns:
            str: Gateway ID
        """
        gateway_name = settings.EXTERNAL_MCP_GATEWAY_NAME

        print(f"🔍 Checking for external gateway: {gateway_name}")

        # 기존 Gateway 조회
        try:
            gateways = self.gateway_client.list_gateways().get('items', [])
            for gw in gateways:
                if gw['name'] == gateway_name:
                    gateway_id = gw['gatewayId']
                    print(f"♻️ Using existing external gateway: {gateway_id}")
                    return gateway_id
        except Exception as e:
            print(f"⚠️ Error listing gateways: {e}")

        # 새 Gateway 생성
        print(f"🆕 Creating new external gateway: {gateway_name}")

        # Gateway IAM 역할 생성
        role_arn = await self._create_gateway_role(gateway_name)

        # Gateway 생성 (IAM 인증)
        gateway = await self._create_gateway_with_iam(
            gateway_name=gateway_name,
            role_arn=role_arn,
            description='Shared Gateway for External MCPs'
        )

        gateway_id = gateway['gatewayId']
        print(f"✅ External gateway created: {gateway_id}")

        return gateway_id

    async def _get_external_authorizer_config(
        self,
        auth_type: ExternalAuthType,
        user_pool_id: str = None
    ) -> Dict[str, Any]:
        """External MCP Target용 인증 설정 생성

        Args:
            auth_type: 인증 타입 (no_auth | oauth)
            user_pool_id: OAuth 사용 시 User Pool ID

        Returns:
            Dict: Authorizer configuration
        """
        if auth_type == ExternalAuthType.NO_AUTH:
            # 공용 Cognito 사용
            return await self._get_cognito_auth_config()
        else:
            # 사용자 선택 User Pool 사용
            if not user_pool_id:
                raise ValueError("OAuth 인증에는 user_pool_id가 필요합니다")

            # User Pool OAuth 설정 조회
            oauth_config = await self.cognito_service.get_user_pool_oauth_config(user_pool_id)
            discovery_url = oauth_config['discovery_url']

            return {
                'customJWTAuthorizer': {
                    'discoveryUrl': discovery_url
                }
            }

    def _sanitize_target_name(self, name: str, max_length: int = 20) -> str:
        """Target 이름을 AWS 규칙에 맞게 변환

        AWS Gateway Target naming rules:
        - Pattern: ^[a-zA-Z][a-zA-Z0-9-]{0,63}$
        - Must start with a letter
        - Only letters, numbers, and hyphens allowed

        중요: Bedrock Converse API tool name 64자 제한 때문에 target 이름을 짧게 유지해야 함
        - Gateway가 tool 이름 앞에 '{target_name}___' prefix를 추가
        - 예: target_name(20자) + ___(3자) + tool_name(40자) = 63자 (64자 이내)
        - 기본값 20자로 제한하여 tool 이름 여유 확보
        """
        # Replace underscores with hyphens
        sanitized = name.replace('_', '-')
        # Remove any other special characters
        sanitized = ''.join(c for c in sanitized if c.isalnum() or c == '-')
        # Remove consecutive hyphens
        while '--' in sanitized:
            sanitized = sanitized.replace('--', '-')
        # Ensure starts with a letter
        if sanitized and not sanitized[0].isalpha():
            sanitized = 't-' + sanitized
        # Truncate to max_length (default 20 for Bedrock tool name compatibility)
        return sanitized[:max_length].rstrip('-')
