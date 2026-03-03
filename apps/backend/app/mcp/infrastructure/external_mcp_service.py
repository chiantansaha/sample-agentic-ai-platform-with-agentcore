"""External MCP Service - Multi-MCP Proxy based implementation

단일 Multi-MCP Proxy Runtime이 모든 External MCP를 처리합니다.
- MCP 설정은 DynamoDB에 저장
- Runtime은 시작 시 DynamoDB에서 설정 로드
- 새 External MCP 추가 시 DynamoDB 업데이트 + Runtime 재시작
"""
import asyncio
import json
import re
from typing import Dict, Any, List, Optional

import boto3
from botocore.exceptions import ClientError

from app.config import settings
from ..domain.value_objects import Tool


class ExternalMCPServiceMixin:
    """External MCP 기능을 제공하는 Mixin 클래스

    BedrockGatewayService와 함께 사용됩니다.
    Multi-MCP Proxy 방식으로 모든 External MCP를 단일 Runtime에서 처리합니다.
    """

    # ============================================================
    # DynamoDB Config Management
    # ============================================================

    def _get_mcp_proxy_config_table_name(self) -> str:
        """MCP Proxy 설정 테이블 이름 반환"""
        return f"{settings.TABLE_PREFIX}-{settings.ENVIRONMENT}-{settings.MCP_PROXY_CONFIG_TABLE}"

    async def _ensure_mcp_proxy_config_table(self):
        """MCP Proxy 설정 테이블 생성 (없으면)"""
        table_name = self._get_mcp_proxy_config_table_name()

        # Build kwargs for boto3 client
        aws_kwargs = {'region_name': self.region}
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            aws_kwargs['aws_access_key_id'] = settings.AWS_ACCESS_KEY_ID
            aws_kwargs['aws_secret_access_key'] = settings.AWS_SECRET_ACCESS_KEY

        dynamodb = boto3.client('dynamodb', **aws_kwargs)

        try:
            dynamodb.describe_table(TableName=table_name)
            print(f"✅ MCP Proxy config table exists: {table_name}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f"🆕 Creating MCP Proxy config table: {table_name}")
                dynamodb.create_table(
                    TableName=table_name,
                    KeySchema=[
                        {'AttributeName': 'id', 'KeyType': 'HASH'}
                    ],
                    AttributeDefinitions=[
                        {'AttributeName': 'id', 'AttributeType': 'S'}
                    ],
                    BillingMode='PAY_PER_REQUEST'
                )
                # 테이블 생성 완료 대기
                waiter = dynamodb.get_waiter('table_exists')
                waiter.wait(TableName=table_name)
                print(f"✅ MCP Proxy config table created: {table_name}")
            else:
                raise

    async def _save_mcp_config_to_dynamodb(
        self,
        mcp_id: str,
        server_name: str,
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None
    ):
        """MCP 설정을 DynamoDB에 저장

        Args:
            mcp_id: MCP ID
            server_name: MCP 서버 이름 (tool prefix로 사용)
            command: 실행 명령어 (예: "npx")
            args: 명령어 인자 목록
            env: 환경변수 (선택)
        """
        await self._ensure_mcp_proxy_config_table()

        table_name = self._get_mcp_proxy_config_table_name()
        dynamodb = boto3.resource(
            'dynamodb',
            region_name=self.region,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        table = dynamodb.Table(table_name)

        item = {
            'id': server_name,  # server_name을 PK로 사용 (tool prefix)
            'mcp_id': mcp_id,
            'command': command,
            'args': args,
            'enabled': True
        }
        if env:
            item['env'] = env

        table.put_item(Item=item)
        print(f"✅ MCP config saved to DynamoDB: {server_name}")

    async def _delete_mcp_config_from_dynamodb(self, server_name: str):
        """MCP 설정을 DynamoDB에서 삭제"""
        table_name = self._get_mcp_proxy_config_table_name()
        dynamodb = boto3.resource(
            'dynamodb',
            region_name=self.region,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        table = dynamodb.Table(table_name)
        table.delete_item(Key={'id': server_name})
        print(f"✅ MCP config deleted from DynamoDB: {server_name}")

    # ============================================================
    # Multi-MCP Proxy Runtime Management
    # ============================================================

    async def _get_or_create_multi_mcp_runtime(self, auth_config: Dict[str, Any]) -> tuple:
        """공유 Multi-MCP Proxy Runtime 조회 또는 생성

        Returns:
            tuple: (runtime_id, runtime_endpoint)
        """
        runtime_name = settings.MCP_PROXY_RUNTIME_NAME

        # 기존 Runtime 조회
        try:
            response = self.gateway_client.list_agent_runtimes()
            # API 응답 키가 'runtimeSummaries' 또는 'agentRuntimes'일 수 있음
            runtimes = response.get('runtimeSummaries', []) or response.get('agentRuntimes', [])

            for rt in runtimes:
                rt_name = rt.get('agentRuntimeName') or rt.get('name')
                if rt_name == runtime_name:
                    runtime_id = rt.get('agentRuntimeId')
                    # 상세 정보 조회
                    runtime_details = self.gateway_client.get_agent_runtime(
                        agentRuntimeId=runtime_id
                    )
                    status = runtime_details.get('status')

                    # READY 상태면 바로 사용
                    if status == 'READY':
                        runtime_endpoint = runtime_details.get('agentRuntimeEndpoint', {}).get('url')
                        if runtime_endpoint:
                            print(f"♻️ Using existing Multi-MCP Proxy Runtime: {runtime_id}")
                            return runtime_id, runtime_endpoint

                    # CREATING 상태면 완료 대기
                    if status == 'CREATING':
                        print(f"⏳ Runtime is being created, waiting for READY...")
                        runtime_endpoint = await self._wait_for_runtime_ready(runtime_id)
                        return runtime_id, runtime_endpoint

                    # FAILED 상태면 삭제 후 재생성
                    if status in ['FAILED', 'DELETE_FAILED']:
                        print(f"⚠️ Existing Runtime failed (status: {status}), recreating...")
                        await self._delete_existing_runtime(runtime_name)
                        break

                    # 기타 상태 (UPDATING 등)는 대기
                    print(f"⏳ Runtime status: {status}, waiting...")
                    runtime_endpoint = await self._wait_for_runtime_ready(runtime_id)
                    return runtime_id, runtime_endpoint

        except Exception as e:
            print(f"⚠️ Failed to list runtimes: {e}")

        # 새 Runtime 생성
        print(f"🆕 Creating new Multi-MCP Proxy Runtime: {runtime_name}")
        return await self._create_multi_mcp_proxy_runtime(auth_config)

    async def _create_multi_mcp_proxy_runtime_role(self) -> str:
        """Multi-MCP Proxy Runtime용 IAM 역할 생성 (DynamoDB 권한 포함)"""
        runtime_name = settings.MCP_PROXY_RUNTIME_NAME
        role_name = f'{runtime_name}-runtime-role'
        config_table_name = self._get_mcp_proxy_config_table_name()

        # 권한 정책: ECR + CloudWatch Logs + DynamoDB (설정 로드)
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
                },
                {
                    "Sid": "DynamoDBConfigAccess",
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:Scan",
                        "dynamodb:GetItem",
                        "dynamodb:Query"
                    ],
                    "Resource": f"arn:aws:dynamodb:{self.region}:{self.account_id}:table/{config_table_name}"
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
                Description=f'AgentCore Runtime role for Multi-MCP Proxy (DynamoDB access)'
            )

            # 권한 정책 연결
            self.iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName="MultiMCPProxyRuntimePolicy",
                PolicyDocument=json.dumps(role_policy)
            )

            # IAM 역할 전파 대기
            await asyncio.sleep(10)

            print(f"✅ Multi-MCP Proxy Runtime Role created with DynamoDB access: {role_name}")
            return role['Role']['Arn']

        except Exception as e:
            raise Exception(f"Multi-MCP Proxy Runtime IAM 역할 생성 실패: {str(e)}")

    async def _create_multi_mcp_proxy_runtime(self, auth_config: Dict[str, Any]) -> tuple:
        """Multi-MCP Proxy Runtime 생성

        Args:
            auth_config: JWT 인증 설정

        Returns:
            tuple: (runtime_id, runtime_endpoint)
        """
        runtime_name = settings.MCP_PROXY_RUNTIME_NAME
        ecr_uri = f"{self.account_id}.dkr.ecr.{self.region}.amazonaws.com/{settings.MCP_PROXY_REPOSITORY}:{settings.MCP_PROXY_IMAGE_TAG}"
        config_table_name = self._get_mcp_proxy_config_table_name()

        # Multi-MCP Proxy 전용 Runtime IAM Role 생성 (DynamoDB 권한 포함)
        runtime_role_arn = await self._create_multi_mcp_proxy_runtime_role()

        try:
            # Runtime 생성 (DynamoDB 설정 로드)
            response = self.gateway_client.create_agent_runtime(
                agentRuntimeName=runtime_name,
                agentRuntimeArtifact={
                    'containerConfiguration': {
                        'containerUri': ecr_uri
                    }
                },
                networkConfiguration={"networkMode": "PUBLIC"},
                protocolConfiguration={"serverProtocol": "MCP"},
                authorizerConfiguration=auth_config,
                roleArn=runtime_role_arn,
                description="Multi-MCP Proxy Runtime for all External MCPs",
                environmentVariables={
                    'MCP_CONFIG_DYNAMODB_TABLE': config_table_name,
                    'MCP_CONFIG_AWS_REGION': self.region
                }
            )

            runtime_id = response['agentRuntimeId']

            # Runtime READY 대기
            runtime_endpoint = await self._wait_for_runtime_ready(runtime_id)

            print(f"✅ Multi-MCP Proxy Runtime created: {runtime_id}")
            return runtime_id, runtime_endpoint

        except Exception as e:
            raise Exception(f"Multi-MCP Proxy Runtime 생성 실패: {str(e)}")

    async def _restart_multi_mcp_runtime(self):
        """Multi-MCP Proxy Runtime 재시작 (설정 변경 반영)

        AgentCore Runtime은 immutable하므로 삭제 후 재생성합니다.
        삭제 완료를 충분히 대기한 후 재생성합니다.
        """
        runtime_name = settings.MCP_PROXY_RUNTIME_NAME
        print(f"🔄 Restarting Multi-MCP Proxy Runtime: {runtime_name}")

        # 기존 Runtime 삭제 (완료 대기 포함)
        await self._delete_existing_runtime(runtime_name)

        # 삭제 완료 추가 대기 (AWS 내부 전파 시간)
        print(f"⏳ Waiting for AWS propagation...")
        await asyncio.sleep(10)

        # Cognito 설정 가져오기
        auth_config = await self._get_cognito_auth_config()

        # 새 Runtime 생성 (재시도 로직 포함)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return await self._create_multi_mcp_proxy_runtime(auth_config)
            except Exception as e:
                if "already exists" in str(e).lower() and attempt < max_retries - 1:
                    print(f"⚠️ Runtime still exists, waiting... (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(15)
                else:
                    raise

    # ============================================================
    # External MCP Infrastructure (Main Entry Point)
    # ============================================================

    async def create_external_mcp_infrastructure(self, mcp: 'ExternalMCP') -> str:
        """External MCP 인프라 생성 (Multi-MCP Proxy 방식)

        최적화된 플로우:
        1. MCP 설정을 DynamoDB에 저장
        2. 공유 인프라(Gateway, Runtime, Target) 조회/생성 (최초 1회만)
        3. Runtime 재시작 없이 완료 (sync API로 별도 처리)

        Note: Tools는 sync_external_mcp_runtime() 호출 시 로드됨

        Args:
            mcp: ExternalMCP 엔티티

        Returns:
            str: Gateway ID
        """
        print(f"🚀 Creating External MCP Infrastructure: {mcp.name}")
        print(f"   Server Name: {mcp.server_name}")
        print(f"   Command: {mcp.command}")

        server_name = mcp.server_name
        print(f"   Tool Prefix: {server_name}")

        # 1. DynamoDB에 설정 저장
        print("📋 Step 1: Saving MCP config to DynamoDB...")
        await self._save_mcp_config_to_dynamodb(
            mcp_id=mcp.id.value,
            server_name=server_name,
            command=mcp.command,
            args=mcp.args,
            env=mcp.env if mcp.env else None
        )

        # 2. Cognito OAuth 인프라 준비
        print("📋 Step 2: Setting up Cognito OAuth infrastructure...")
        oauth_provider_arn = await self._get_or_create_oauth_provider()
        cognito_auth_config = await self._get_cognito_auth_config()
        print(f"✅ OAuth infrastructure ready")

        # 3. 공유 Gateway 조회/생성
        print("📋 Step 3: Getting or creating shared External MCP Gateway...")
        gateway_id, gateway_url = await self._get_or_create_external_mcp_gateway(cognito_auth_config)
        mcp.set_gateway_id(gateway_id)
        print(f"✅ Gateway ready: {gateway_id}")

        # 4. Multi-MCP Proxy Runtime 조회/생성 (재시작 안함)
        print("📋 Step 4: Getting or creating Multi-MCP Proxy Runtime...")
        runtime_id, runtime_endpoint = await self._get_or_create_multi_mcp_runtime(cognito_auth_config)
        mcp.set_runtime_id(runtime_id)
        mcp.set_runtime_url(runtime_endpoint)
        print(f"✅ Runtime ready: {runtime_id}")

        # 5. Gateway IAM 권한 추가
        print("📋 Step 5: Updating Gateway IAM permissions...")
        await self._add_external_target_permissions(gateway_id, runtime_id)

        # 6. 공유 Gateway Target 조회/생성
        print("📋 Step 6: Getting or creating shared Gateway Target...")
        target_id = await self._get_or_create_external_mcp_target(
            gateway_id=gateway_id,
            runtime_endpoint=runtime_endpoint,
            oauth_provider_arn=oauth_provider_arn
        )
        mcp.set_target_id(target_id)
        print(f"✅ Shared Target ready: {target_id}")

        # 7. MCP 엔드포인트 설정
        mcp.set_endpoint(gateway_url)

        print(f"🎉 External MCP config saved: {mcp.name}")
        print(f"   ⚠️ Tools will be available after sync (call sync_external_mcp_runtime)")
        return gateway_id

    async def sync_external_mcp_runtime(self) -> dict:
        """External MCP Runtime 동기화 (Runtime 재시작 + Tools 재조회)

        DynamoDB에 저장된 모든 External MCP 설정을 Runtime에 반영하고
        각 MCP의 tools를 조회합니다.

        Returns:
            dict: {server_name: [tools]} 형태의 결과
        """
        print("🔄 Syncing External MCP Runtime...")

        # 1. Cognito 설정 가져오기
        cognito_auth_config = await self._get_cognito_auth_config()

        # 2. Runtime 재시작
        print("📋 Step 1: Restarting Multi-MCP Proxy Runtime...")
        runtime_id, runtime_endpoint = await self._restart_multi_mcp_runtime()
        print(f"✅ Runtime restarted: {runtime_id}")

        # 3. DynamoDB에서 모든 설정 조회
        print("📋 Step 2: Loading configs from DynamoDB...")
        configs = await self._get_all_mcp_configs_from_dynamodb()
        print(f"   Found {len(configs)} MCP configs")

        # 4. 각 서버의 tools 조회
        print("📋 Step 3: Fetching tools from Runtime...")
        print("   ⏳ Waiting 60 seconds for MCP servers to initialize...")
        await asyncio.sleep(60)

        results = {}
        for config in configs:
            server_name = config.get('id')
            if not server_name:
                continue

            print(f"   Fetching tools for: {server_name}")
            try:
                tools = await self._fetch_tools_from_runtime_with_jwt(
                    runtime_endpoint,
                    tool_prefix=server_name,
                    max_retries=5
                )
                results[server_name] = [
                    {"name": t.name, "description": t.description}
                    for t in tools
                ]
                print(f"   ✅ {server_name}: {len(tools)} tools")
            except Exception as e:
                print(f"   ⚠️ {server_name}: Failed - {str(e)}")
                results[server_name] = []

        print(f"🎉 Sync completed: {len(results)} servers processed")
        return {
            "runtime_id": runtime_id,
            "runtime_endpoint": runtime_endpoint,
            "servers": results
        }

    async def _get_all_mcp_configs_from_dynamodb(self) -> list:
        """DynamoDB에서 모든 MCP 설정 조회"""
        table_name = self._get_mcp_proxy_config_table_name()
        dynamodb = boto3.resource(
            'dynamodb',
            region_name=self.region,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        table = dynamodb.Table(table_name)

        response = table.scan(
            FilterExpression='enabled = :enabled',
            ExpressionAttributeValues={':enabled': True}
        )
        return response.get('Items', [])

    # ============================================================
    # Shared Gateway Management
    # ============================================================

    async def _get_or_create_external_mcp_gateway(
        self,
        auth_config: Dict[str, Any] = None  # Deprecated, kept for compatibility
    ) -> tuple:
        """공유 External MCP Gateway 조회 또는 생성 (IAM 인증)

        Note: auth_config 파라미터는 더 이상 사용되지 않습니다 (IAM 인증 사용).

        Returns:
            tuple: (gateway_id, gateway_url)
        """
        gateway_name = settings.EXTERNAL_MCP_GATEWAY_NAME

        # 기존 Gateway 조회
        try:
            gateways = self.gateway_client.list_gateways().get('items', [])
            for gw in gateways:
                if gw['name'] == gateway_name:
                    gateway_id = gw['gatewayId']
                    gateway_details = self.gateway_client.get_gateway(gatewayIdentifier=gateway_id)
                    gateway_url = gateway_details.get('gatewayUrl')
                    print(f"♻️ Using existing External MCP Gateway: {gateway_id}")
                    return gateway_id, gateway_url
        except Exception as e:
            print(f"⚠️ Failed to list gateways: {e}")

        # 새 Gateway 생성 (IAM 인증)
        print(f"🆕 Creating new External MCP Gateway: {gateway_name}")
        gateway_role_arn = await self._create_gateway_role(gateway_name)

        gateway = await self._create_gateway_with_iam(
            gateway_name=gateway_name,
            role_arn=gateway_role_arn,
            description="Shared Gateway for External MCPs (Multi-MCP Proxy)"
        )
        gateway_id = gateway['gatewayId']
        gateway_url = gateway['gatewayUrl']

        await self._wait_for_gateway_ready(gateway_id)

        print(f"✅ External MCP Gateway created: {gateway_id}")
        return gateway_id, gateway_url

    # ============================================================
    # IAM Permission Management
    # ============================================================

    async def _add_external_target_permissions(self, gateway_id: str, runtime_id: str):
        """공유 Gateway에 Runtime 호출 권한 추가"""
        gateway_name = settings.EXTERNAL_MCP_GATEWAY_NAME
        role_name = f"{gateway_name}-role"

        policy_name = f"MultiMCPProxyAccess"
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "bedrock-agentcore:InvokeGatewayTarget",
                        "bedrock-agentcore:GetGatewayTarget"
                    ],
                    "Resource": f"arn:aws:bedrock-agentcore:*:*:gateway/{gateway_id}/*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "bedrock-agentcore:InvokeAgentRuntime"
                    ],
                    "Resource": f"arn:aws:bedrock-agentcore:*:*:runtime/{runtime_id}"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:Scan",
                        "dynamodb:GetItem"
                    ],
                    "Resource": f"arn:aws:dynamodb:{self.region}:{self.account_id}:table/{self._get_mcp_proxy_config_table_name()}"
                }
            ]
        }

        try:
            self.iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName=policy_name,
                PolicyDocument=json.dumps(policy_document)
            )
            print(f"✅ IAM permissions updated for Multi-MCP Proxy")
        except Exception as e:
            print(f"⚠️ Failed to update IAM permissions: {str(e)}")

    # ============================================================
    # External MCP Target Methods
    # ============================================================

    async def _get_or_create_external_mcp_target(
        self,
        gateway_id: str,
        runtime_endpoint: str,
        oauth_provider_arn: str
    ) -> str:
        """공유 External MCP Target 조회 또는 생성

        모든 External MCP가 동일한 Target을 공유합니다.
        Target은 Multi-MCP Proxy Runtime을 가리킵니다.

        Returns:
            str: Target ID
        """
        target_name = settings.MCP_PROXY_TARGET_NAME

        # 기존 Target 조회
        try:
            targets = self.gateway_client.list_gateway_targets(
                gatewayIdentifier=gateway_id
            ).get('items', [])

            for target in targets:
                if target.get('name') == target_name:
                    target_id = target.get('targetId')
                    print(f"♻️ Using existing shared Target: {target_name} (ID: {target_id})")
                    return target_id
        except Exception as e:
            print(f"⚠️ Failed to list targets: {e}")

        # 새 Target 생성
        print(f"🆕 Creating new shared Target: {target_name}")

        scopes = [
            f"{self.cognito_service.RESOURCE_SERVER_ID}/read",
            f"{self.cognito_service.RESOURCE_SERVER_ID}/write",
            f"{self.cognito_service.RESOURCE_SERVER_ID}/invoke"
        ]

        try:
            response = self.gateway_client.create_gateway_target(
                gatewayIdentifier=gateway_id,
                name=target_name,
                description="Shared Target for Multi-MCP Proxy Runtime (all External MCPs)",
                targetConfiguration={
                    'mcp': {
                        'mcpServer': {
                            'endpoint': runtime_endpoint
                        }
                    }
                },
                credentialProviderConfigurations=[{
                    'credentialProviderType': 'OAUTH',
                    'credentialProvider': {
                        'oauthCredentialProvider': {
                            'providerArn': oauth_provider_arn,
                            'scopes': scopes
                        }
                    }
                }]
            )
            target_id = response.get('targetId')
            print(f"✅ Shared Target created: {target_name} (ID: {target_id})")
            return target_id

        except Exception as e:
            raise Exception(f"Shared Target 생성 실패: {str(e)}")

    # ============================================================
    # Tool Fetching
    # ============================================================

    async def _fetch_tools_from_runtime_with_jwt(
        self,
        runtime_endpoint: str,
        tool_prefix: str = None,
        max_retries: int = 5
    ) -> List[Tool]:
        """Runtime endpoint에서 Tool 목록 조회 (JWT 토큰 사용)

        Args:
            runtime_endpoint: Runtime 엔드포인트 URL
            tool_prefix: 필터링할 tool prefix (예: "youtube")
            max_retries: 최대 재시도 횟수

        Returns:
            List[Tool]: MCP Protocol 표준 Tool 목록
        """
        import requests

        print(f"🔍 Fetching tools from Runtime: {runtime_endpoint}")
        if tool_prefix:
            print(f"   Filtering by prefix: {tool_prefix}__")

        try:
            client_id, client_secret = await self.cognito_service.get_or_create_m2m_client(
                client_name="mcp-gateway-oauth-client"
            )

            token_response = await self.cognito_service.get_access_token(
                client_id=client_id,
                client_secret=client_secret
            )
            access_token = token_response.get('access_token')

            if not access_token:
                raise Exception("Failed to obtain access token")

            payload = {
                "jsonrpc": "2.0",
                "id": "list-tools",
                "method": "tools/list"
            }

            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/event-stream',
                'Authorization': f'Bearer {access_token}'
            }

            tools = []
            for attempt in range(max_retries):
                response = requests.post(
                    runtime_endpoint,
                    headers=headers,
                    data=json.dumps(payload),
                    timeout=60
                )

                response.raise_for_status()

                content_type = response.headers.get('Content-Type', '')
                if 'text/event-stream' in content_type:
                    result = self._parse_sse_response(response.text)
                else:
                    result = response.json()

                if 'result' not in result or 'tools' not in result['result']:
                    if attempt < max_retries - 1:
                        print(f"⏳ Waiting for Runtime... (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(15)  # 15초 대기 (MCP 서버 초기화 시간 고려)
                        continue
                    raise Exception(f"Invalid response: {result}")

                tools_data = result['result']['tools']
                print(f"   📋 Total tools from Runtime: {len(tools_data)}")
                if tools_data and tool_prefix:
                    print(f"   📋 Looking for prefix: '{tool_prefix}__'")
                    sample_names = [t['name'] for t in tools_data[:5]]
                    print(f"   📋 Sample tool names: {sample_names}")

                for tool_data in tools_data:
                    tool_name = tool_data['name']

                    # prefix 필터링 (Multi-MCP Proxy는 server__tool 형식)
                    if tool_prefix:
                        if not tool_name.startswith(f"{tool_prefix}__"):
                            continue
                        # prefix 제거하여 원래 tool 이름으로 저장
                        original_name = tool_name.split("__", 1)[1] if "__" in tool_name else tool_name
                    else:
                        original_name = tool_name

                    tool = Tool(
                        name=original_name,
                        description=tool_data.get('description', ''),
                        input_schema=tool_data.get('inputSchema', {})
                    )
                    tools.append(tool)
                    print(f"✅ Fetched tool: {original_name}")

                if tools:
                    break
                elif attempt < max_retries - 1:
                    print(f"⏳ No matching tools for prefix '{tool_prefix}', waiting... (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(15)  # 15초 대기 (MCP 서버 초기화 시간 고려)

            print(f"🎉 Total tools fetched: {len(tools)}")
            return tools

        except Exception as e:
            print(f"❌ Failed to fetch tools: {str(e)}")
            raise Exception(f"Runtime Tool 조회 실패: {str(e)}")

    def _parse_sse_response(self, sse_text: str) -> dict:
        """SSE 응답 파싱"""
        for line in sse_text.strip().split('\n'):
            if line.startswith('data: '):
                return json.loads(line[6:])
        return json.loads(sse_text)
