"""Internal Deploy MCP Service - Container/Runtime based MCP

BedrockGatewayService를 상속받아 Internal Deploy MCP 기능을 구현합니다.
- ECR 이미지 기반 Runtime 생성
- JWT/OAuth 인증
- MCP Server Target 관리
"""
import asyncio
import json
import urllib.parse
from typing import Dict, Any, List, AsyncGenerator

import requests

from app.config import settings
from ..domain.value_objects import Tool
from ..dto.progress import ProgressStep, ProgressStatus


class DeployMCPServiceMixin:
    """Internal Deploy MCP 기능을 제공하는 Mixin 클래스

    BedrockGatewayService와 함께 사용됩니다.
    """

    # ============================================================
    # Cognito OAuth Infrastructure Methods
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

        return {
            'customJWTAuthorizer': {
                'discoveryUrl': discovery_url,
                'allowedClients': [client_id]
            }
        }

    # ============================================================
    # Runtime Management Methods
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

            # TODO: 나중에 거버넌스로 권한 정책 정의 필요
            # 현재는 MCP 서버가 다양한 AWS 서비스 접근이 필요하므로 Admin 권한 부여
            self.iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn="arn:aws:iam::aws:policy/AdministratorAccess"
            )

            # IAM 역할 전파 대기
            await asyncio.sleep(10)

            return role['Role']['Arn']

        except Exception as e:
            raise Exception(f"Runtime IAM 역할 생성 실패: {str(e)}")

    def _sanitize_runtime_name(self, name: str) -> str:
        """Runtime 이름을 AWS 규칙에 맞게 변환

        AWS AgentCore Runtime naming constraint:
        - Pattern: [a-zA-Z][a-zA-Z0-9_]{0,47}
        - Must start with a letter
        - Only letters, numbers, and underscores allowed (NO hyphens)
        - Max 48 characters
        """
        sanitized = name.replace('-', '_')
        sanitized = ''.join(c for c in sanitized if c.isalnum() or c == '_')
        if sanitized and not sanitized[0].isalpha():
            sanitized = 'r_' + sanitized
        return sanitized[:48]

    async def _delete_existing_runtime(self, runtime_name: str, max_wait: int = 60):
        """기존 Runtime 삭제 및 완료 대기"""
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

            print(f"🗑️  Deleting existing runtime: {runtime_name} (ID: {runtime_id})")
            self.gateway_client.delete_agent_runtime(agentRuntimeId=runtime_id)

            for attempt in range(max_wait // 5):
                await asyncio.sleep(5)
                try:
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
        for attempt in range(max_attempts):
            try:
                response = self.gateway_client.get_agent_runtime(agentRuntimeId=runtime_id)
                status = response.get('status')

                if status == 'READY':
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
    # Deploy MCP Infrastructure Methods
    # ============================================================

    async def create_deploy_mcp_infrastructure(self, mcp: 'InternalDeployMCP') -> str:
        """Internal Deploy MCP 인프라 생성 (Cognito OAuth + Runtime + Gateway + Target)

        Args:
            mcp: InternalDeployMCP 엔티티

        Returns:
            str: Gateway ID
        """
        from ..domain.entities import InternalDeployMCP

        print(f"🚀 Creating Deploy MCP Infrastructure: {mcp.name}")

        # 1. Cognito OAuth 인프라 준비 (공유)
        print("📋 Step 1: Setting up Cognito OAuth infrastructure...")
        oauth_provider_arn = await self._get_or_create_oauth_provider()
        cognito_auth_config = await self._get_cognito_auth_config()
        print(f"✅ OAuth infrastructure ready")

        # 2. Runtime IAM Role 생성
        print("📋 Step 2: Creating Runtime IAM Role...")
        runtime_role_arn = await self._create_runtime_role(f"{mcp.name}-{settings.ENVIRONMENT}")
        print(f"✅ Runtime Role created: {runtime_role_arn}")

        # 3. AgentCore Runtime 생성 (JWT Authorizer 포함)
        print("📋 Step 3: Creating AgentCore Runtime with JWT auth...")
        runtime_id, runtime_endpoint = await self._create_agent_runtime_with_jwt(
            mcp_name=mcp.name,  # Don't add environment here - it's added in _create_agent_runtime_with_jwt
            ecr_repository=mcp.ecr_repository,
            image_tag=mcp.image_tag,
            role_arn=runtime_role_arn,
            auth_config=cognito_auth_config
        )
        print(f"✅ Runtime created: {runtime_id}")
        print(f"   Endpoint: {runtime_endpoint}")

        # 4. MCP 엔티티에 Runtime 정보 설정
        mcp.set_runtime_id(runtime_id)
        mcp.set_runtime_url(runtime_endpoint)

        # 5. Gateway IAM Role 생성
        print("📋 Step 4: Creating Gateway IAM Role...")
        gateway_name = f"{mcp.name}-gateway-{settings.ENVIRONMENT}"
        gateway_role_arn = await self._create_gateway_role(gateway_name)
        print(f"✅ Gateway Role created: {gateway_role_arn}")

        # 6. Gateway 생성 (IAM Authorizer)
        print("📋 Step 5: Creating AgentCore Gateway with IAM auth...")
        gateway = await self._create_gateway_with_iam(
            gateway_name=gateway_name,
            role_arn=gateway_role_arn,
            description=mcp.description,
            enable_semantic_search=mcp.enable_semantic_search
        )
        gateway_id = gateway['gatewayId']
        gateway_url = gateway['gatewayUrl']
        print(f"✅ Gateway created: {gateway_id}")
        print(f"   URL: {gateway_url}")

        # 7. IAM 권한 수정
        await self._fix_deploy_iam_permissions(gateway_id, gateway_role_arn, runtime_id)

        # 8. Gateway READY 대기
        print("📋 Step 6: Waiting for Gateway to be ready...")
        await self._wait_for_gateway_ready(gateway_id)
        print("✅ Gateway is ready")

        # 9. MCP Server Target 생성 (OAuth credential provider 사용)
        print("📋 Step 7: Creating MCP Server Target with OAuth...")
        await self._create_mcp_server_target_with_oauth(
            gateway_id=gateway_id,
            mcp_name=mcp.name,
            runtime_endpoint=runtime_endpoint,
            oauth_provider_arn=oauth_provider_arn,
            description=mcp.description
        )
        print("✅ MCP Server Target created")

        # 10. Tools 조회 (MCP Protocol) - IAM Sigv4 인증 사용
        print("📋 Step 8: Fetching tools from MCP Server...")
        try:
            tools = await self._fetch_tools_from_gateway_with_iam(gateway_url)
            for tool in tools:
                mcp.add_tool(tool)
            print(f"✅ Tools fetched: {len(tools)} tools")
        except Exception as e:
            print(f"⚠️ Failed to fetch tools (MCP Server may not be ready): {str(e)}")

        # 11. MCP 엔드포인트 설정
        mcp.set_endpoint(gateway_url)

        print(f"🎉 Deploy MCP Infrastructure completed: {mcp.name}")
        return gateway_id

    async def create_deploy_mcp_infrastructure_stream(
        self,
        mcp: 'InternalDeployMCP'
    ) -> AsyncGenerator[ProgressStep, None]:
        """Internal Deploy MCP 인프라 생성 (SSE 스트리밍 버전)

        각 단계별 진행 상황을 ProgressStep으로 yield합니다.

        Args:
            mcp: InternalDeployMCP 엔티티

        Yields:
            ProgressStep: 각 단계의 진행 상황
        """
        from ..domain.entities import InternalDeployMCP

        total_steps = 8

        def make_progress(step: int, title: str, desc: str, status: ProgressStatus, details: str = None) -> ProgressStep:
            return ProgressStep(
                step=step,
                total_steps=total_steps,
                title=title,
                description=desc,
                status=status,
                details=details
            )

        try:
            print(f"🚀 Creating Deploy MCP Infrastructure (stream): {mcp.name}")

            # Step 1: Cognito OAuth 인프라 준비 (공유)
            yield make_progress(1, "Setting up OAuth", "Cognito OAuth 인프라 준비 중...", ProgressStatus.IN_PROGRESS)
            print("📋 Step 1: Setting up Cognito OAuth infrastructure...")
            oauth_provider_arn = await self._get_or_create_oauth_provider()
            cognito_auth_config = await self._get_cognito_auth_config()
            print(f"✅ OAuth infrastructure ready")
            yield make_progress(1, "Setting up OAuth", "OAuth 인프라 준비 완료", ProgressStatus.COMPLETED)

            # Step 2: Runtime IAM Role 생성
            yield make_progress(2, "Creating Runtime Role", "Runtime IAM 역할 생성 중...", ProgressStatus.IN_PROGRESS)
            print("📋 Step 2: Creating Runtime IAM Role...")
            runtime_role_arn = await self._create_runtime_role(f"{mcp.name}-{settings.ENVIRONMENT}")
            print(f"✅ Runtime Role created: {runtime_role_arn}")
            yield make_progress(2, "Creating Runtime Role", "Runtime IAM 역할 생성 완료", ProgressStatus.COMPLETED, runtime_role_arn)

            # Step 3: AgentCore Runtime 생성 (JWT Authorizer 포함)
            yield make_progress(3, "Creating Runtime", "AgentCore Runtime 생성 중... (약 1-2분 소요)", ProgressStatus.IN_PROGRESS)
            print("📋 Step 3: Creating AgentCore Runtime with JWT auth...")
            runtime_id, runtime_endpoint = await self._create_agent_runtime_with_jwt(
                mcp_name=mcp.name,  # Don't add environment here - it's added in _create_agent_runtime_with_jwt
                ecr_repository=mcp.ecr_repository,
                image_tag=mcp.image_tag,
                role_arn=runtime_role_arn,
                auth_config=cognito_auth_config
            )
            print(f"✅ Runtime created: {runtime_id}")
            print(f"   Endpoint: {runtime_endpoint}")
            yield make_progress(3, "Creating Runtime", "AgentCore Runtime 생성 완료", ProgressStatus.COMPLETED, runtime_id)

            # MCP 엔티티에 Runtime 정보 설정
            mcp.set_runtime_id(runtime_id)
            mcp.set_runtime_url(runtime_endpoint)

            # Step 4: Gateway IAM Role 생성
            yield make_progress(4, "Creating Gateway Role", "Gateway IAM 역할 생성 중...", ProgressStatus.IN_PROGRESS)
            print("📋 Step 4: Creating Gateway IAM Role...")
            gateway_name = f"{mcp.name}-gateway-{settings.ENVIRONMENT}"
            gateway_role_arn = await self._create_gateway_role(gateway_name)
            print(f"✅ Gateway Role created: {gateway_role_arn}")
            yield make_progress(4, "Creating Gateway Role", "Gateway IAM 역할 생성 완료", ProgressStatus.COMPLETED, gateway_role_arn)

            # Step 5: Gateway 생성 (IAM Authorizer)
            yield make_progress(5, "Creating Gateway", "AgentCore Gateway 생성 중...", ProgressStatus.IN_PROGRESS)
            print("📋 Step 5: Creating AgentCore Gateway with IAM auth...")
            gateway = await self._create_gateway_with_iam(
                gateway_name=gateway_name,
                role_arn=gateway_role_arn,
                description=mcp.description,
                enable_semantic_search=mcp.enable_semantic_search
            )
            gateway_id = gateway['gatewayId']
            gateway_url = gateway['gatewayUrl']
            print(f"✅ Gateway created: {gateway_id}")
            print(f"   URL: {gateway_url}")
            yield make_progress(5, "Creating Gateway", "AgentCore Gateway 생성 완료", ProgressStatus.COMPLETED, gateway_id)

            # IAM 권한 수정
            await self._fix_deploy_iam_permissions(gateway_id, gateway_role_arn, runtime_id)

            # Step 6: Gateway READY 대기
            yield make_progress(6, "Waiting for Gateway", "Gateway 준비 대기 중...", ProgressStatus.IN_PROGRESS)
            print("📋 Step 6: Waiting for Gateway to be ready...")
            await self._wait_for_gateway_ready(gateway_id)
            print("✅ Gateway is ready")
            yield make_progress(6, "Waiting for Gateway", "Gateway 준비 완료", ProgressStatus.COMPLETED)

            # Step 7: MCP Server Target 생성 (OAuth credential provider 사용)
            yield make_progress(7, "Creating Target", "MCP Server Target 생성 중...", ProgressStatus.IN_PROGRESS)
            print("📋 Step 7: Creating MCP Server Target with OAuth...")
            await self._create_mcp_server_target_with_oauth(
                gateway_id=gateway_id,
                mcp_name=mcp.name,
                runtime_endpoint=runtime_endpoint,
                oauth_provider_arn=oauth_provider_arn,
                description=mcp.description
            )
            print("✅ MCP Server Target created")
            yield make_progress(7, "Creating Target", "MCP Server Target 생성 완료", ProgressStatus.COMPLETED)

            # Step 8: Tools 조회 (MCP Protocol) - IAM Sigv4 인증 사용
            yield make_progress(8, "Fetching Tools", "MCP 서버에서 도구 목록 조회 중...", ProgressStatus.IN_PROGRESS)
            print("📋 Step 8: Fetching tools from MCP Server...")
            try:
                tools = await self._fetch_tools_from_gateway_with_iam(gateway_url)
                for tool in tools:
                    mcp.add_tool(tool)
                print(f"✅ Tools fetched: {len(tools)} tools")
                yield make_progress(8, "Fetching Tools", f"{len(tools)}개 도구 조회 완료", ProgressStatus.COMPLETED, f"{len(tools)} tools")
            except Exception as e:
                print(f"⚠️ Failed to fetch tools (MCP Server may not be ready): {str(e)}")
                yield make_progress(8, "Fetching Tools", "도구 조회 완료 (0개)", ProgressStatus.COMPLETED, "0 tools")

            # MCP 엔드포인트 설정
            mcp.set_endpoint(gateway_url)
            mcp.set_dedicated_gateway_id(gateway_id)

            print(f"🎉 Deploy MCP Infrastructure completed: {mcp.name}")

        except Exception as e:
            print(f"❌ Deploy MCP Infrastructure failed: {str(e)}")
            yield make_progress(0, "Error", "인프라 생성 중 오류 발생", ProgressStatus.FAILED, str(e))
            raise

    async def update_deploy_mcp_infrastructure(self, mcp: 'InternalDeployMCP') -> None:
        """Internal Deploy MCP 인프라 업데이트 (Image Tag 변경 시)"""
        print(f"🔄 Updating Deploy MCP Infrastructure: {mcp.name}")
        print(f"   - ECR Repository: {mcp.ecr_repository}")
        print(f"   - New Image Tag: {mcp.image_tag}")

        gateway_name = f"{mcp.name}-gateway-{settings.ENVIRONMENT}"

        try:
            # 1. 기존 Gateway 정보 조회
            print("📋 Step 1: Finding existing Gateway...")
            gateways = self.gateway_client.list_gateways().get('items', [])
            gateway_id = None
            for gw in gateways:
                if gw['name'] == gateway_name:
                    gateway_id = gw['gatewayId']
                    break

            if not gateway_id:
                raise Exception(f"Gateway not found: {gateway_name}")

            gateway_details = self.gateway_client.get_gateway(gatewayIdentifier=gateway_id)
            gateway_url = gateway_details.get('gatewayUrl')
            print(f"✅ Gateway found: {gateway_id}, URL: {gateway_url}")

            # 2. 기존 Runtime 정보 조회
            print("📋 Step 2: Finding existing Runtime...")

            # Use stored runtime_id if available, otherwise search by name
            runtime_id = mcp.runtime_id
            if runtime_id:
                print(f"   Using stored runtime_id: {runtime_id}")
            else:
                # Fallback: search by name (for backward compatibility)
                runtime_name = self._sanitize_runtime_name(f"{mcp.name}_runtime_{settings.ENVIRONMENT}")
                print(f"   Searching by runtime name: {runtime_name}")
                runtimes = self.gateway_client.list_agent_runtimes().get('agentRuntimes', [])
                for runtime in runtimes:
                    if runtime.get('agentRuntimeName') == runtime_name:
                        runtime_id = runtime['agentRuntimeId']
                        break

            if not runtime_id:
                raise Exception(f"Runtime not found for MCP: {mcp.name}")

            runtime_info = self.gateway_client.get_agent_runtime(agentRuntimeId=runtime_id)
            print(f"✅ Runtime found: {runtime_id}")

            # 3. Runtime 업데이트 (새 이미지로)
            print("📋 Step 3: Updating Runtime with new image...")
            new_ecr_uri = f"{self.account_id}.dkr.ecr.{self.region}.amazonaws.com/{mcp.ecr_repository}:{mcp.image_tag}"
            print(f"   New image URI: {new_ecr_uri}")

            update_response = self.gateway_client.update_agent_runtime(
                agentRuntimeId=runtime_id,
                agentRuntimeArtifact={
                    'containerConfiguration': {
                        'containerUri': new_ecr_uri
                    }
                },
                roleArn=runtime_info['roleArn'],
                networkConfiguration=runtime_info.get('networkConfiguration', {'networkMode': 'PUBLIC'}),
                description=mcp.description or f"MCP Server Runtime for {mcp.name} (JWT auth)"
            )
            print(f"✅ Runtime update initiated, status: {update_response.get('status')}")

            # 4. Runtime READY 대기
            print("📋 Step 4: Waiting for Runtime to be ready...")
            runtime_endpoint = await self._wait_for_runtime_ready(runtime_id)
            print(f"✅ Runtime is ready")
            print(f"   Endpoint: {runtime_endpoint}")

            # 5. MCP 엔티티에 Runtime 정보 설정
            mcp.set_runtime_id(runtime_id)
            mcp.set_runtime_url(runtime_endpoint)

            # 6. Tools 재조회 (IAM Sigv4 인증 사용)
            print("📋 Step 5: Fetching tools from updated Runtime...")
            mcp.clear_tools()
            try:
                await asyncio.sleep(10)
                tools = await self._fetch_tools_from_gateway_with_iam(gateway_url)
                for tool in tools:
                    mcp.add_tool(tool)
                print(f"✅ Tools fetched: {len(tools)} tools")
            except Exception as e:
                print(f"⚠️ Failed to fetch tools: {str(e)}")

            print(f"🎉 Deploy MCP Infrastructure update completed: {mcp.name}")

        except Exception as e:
            print(f"❌ Deploy MCP Infrastructure update failed: {str(e)}")
            raise Exception(f"Deploy MCP 인프라 업데이트 실패: {str(e)}")

    # ============================================================
    # Gateway/Runtime Methods (IAM Gateway + JWT Runtime)
    # ============================================================

    async def _create_agent_runtime_with_jwt(
        self,
        mcp_name: str,
        ecr_repository: str,
        image_tag: str,
        role_arn: str,
        auth_config: Dict[str, Any]
    ) -> tuple:
        """AgentCore Runtime 생성 (JWT Authorizer 포함)"""
        runtime_name = self._sanitize_runtime_name(f"{mcp_name}_runtime_{settings.ENVIRONMENT}")
        ecr_uri = f"{self.account_id}.dkr.ecr.{self.region}.amazonaws.com/{ecr_repository}:{image_tag}"

        try:
            await self._delete_existing_runtime(runtime_name)

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
                roleArn=role_arn,
                description=f"MCP Server Runtime for {mcp_name} (JWT auth)"
            )

            runtime_id = response['agentRuntimeId']
            runtime_endpoint = await self._wait_for_runtime_ready(runtime_id)

            return runtime_id, runtime_endpoint

        except Exception as e:
            raise Exception(f"AgentCore Runtime (JWT) 생성 실패: {str(e)}")

    async def _create_gateway_with_iam(
        self,
        gateway_name: str,
        role_arn: str,
        description: str,
        auth_config: Dict[str, Any] = None,  # Deprecated, kept for compatibility
        enable_semantic_search: bool = False
    ) -> Dict[str, Any]:
        """Gateway 생성 (IAM Authorizer)

        Note: auth_config 파라미터는 더 이상 사용되지 않습니다 (IAM 인증 사용).
        기존 호출 코드와의 호환성을 위해 파라미터는 유지하지만 무시됩니다.
        """
        try:
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

    async def _fix_deploy_iam_permissions(self, gateway_id: str, role_arn: str, runtime_id: str):
        """Gateway가 Target 및 Runtime을 호출할 수 있도록 IAM 권한 추가"""
        role_name = role_arn.split("/")[-1]

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
                }
            ]
        }

        try:
            self.iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName="GatewayTargetAndRuntimeAccess",
                PolicyDocument=json.dumps(policy_document)
            )
        except Exception as e:
            raise Exception(f"IAM 권한 수정 실패: {str(e)}")

    async def _create_mcp_server_target_with_oauth(
        self,
        gateway_id: str,
        mcp_name: str,
        runtime_endpoint: str,
        oauth_provider_arn: str,
        description: str = None
    ):
        """MCP Server Target 생성 (OAuth credential provider 사용)"""
        target_name = f"{mcp_name}-target-{settings.ENVIRONMENT}"
        target_description = description or f"MCP Server target for {mcp_name}"

        scopes = [
            f"{self.cognito_service.RESOURCE_SERVER_ID}/read",
            f"{self.cognito_service.RESOURCE_SERVER_ID}/write",
            f"{self.cognito_service.RESOURCE_SERVER_ID}/invoke"
        ]

        try:
            response = self.gateway_client.create_gateway_target(
                gatewayIdentifier=gateway_id,
                name=target_name,
                description=target_description,
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
            print(f"✅ MCP Server Target (OAuth) created: {target_name} (ID: {target_id})")
            return target_id
        except Exception as e:
            raise Exception(f"MCP Server Target (OAuth) 생성 실패: {str(e)}")

    # ============================================================
    # IAM Tool Fetching Methods (for IAM-authenticated Gateways)
    # ============================================================

    async def _fetch_tools_from_gateway_with_iam(self, gateway_url: str, max_retries: int = 5) -> List[Tool]:
        """Gateway에서 Tool 목록 조회 (IAM Sigv4 인증)"""
        from botocore.auth import SigV4Auth
        from botocore.awsrequest import AWSRequest
        import botocore.session

        print(f"🔍 Fetching tools from gateway (IAM Sigv4): {gateway_url}")

        try:
            payload = {
                "jsonrpc": "2.0",
                "id": "list-tools",
                "method": "tools/list"
            }
            payload_str = json.dumps(payload)

            # Create AWS request for Sigv4 signing
            session = botocore.session.get_session()
            credentials = session.get_credentials()

            tools = []
            for attempt in range(max_retries):
                # Create and sign the request
                aws_request = AWSRequest(
                    method='POST',
                    url=gateway_url,
                    data=payload_str,
                    headers={
                        'Content-Type': 'application/json',
                        'Host': gateway_url.split('/')[2]
                    }
                )
                SigV4Auth(credentials, 'bedrock-agentcore', self.region).add_auth(aws_request)

                # Make the request with signed headers
                response = requests.post(
                    gateway_url,
                    headers=dict(aws_request.headers),
                    data=payload_str,
                    timeout=60
                )

                response.raise_for_status()
                result = response.json()

                if 'result' not in result:
                    raise Exception(f"Invalid MCP Protocol response: {result}")

                if 'tools' not in result['result']:
                    raise Exception(f"No tools in response: {result}")

                tools_data = result['result']['tools']

                if tools_data:
                    for tool_data in tools_data:
                        raw_name = tool_data['name']
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
                    break
                else:
                    if attempt < max_retries - 1:
                        print(f"⏳ Tools empty, waiting for Target propagation... (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(10)
                    else:
                        print(f"⚠️ No tools found after {max_retries} attempts")

            print(f"🎉 Total tools fetched: {len(tools)}")
            return tools

        except Exception as e:
            print(f"❌ Failed to fetch tools: {str(e)}")
            raise Exception(f"Gateway Tool 조회 실패 (IAM): {str(e)}")

    # ============================================================
    # JWT Tool Fetching Methods (for JWT-authenticated Runtimes)
    # ============================================================

    async def _fetch_tools_from_gateway_with_jwt(self, gateway_url: str, max_retries: int = 5) -> List[Tool]:
        """Gateway에서 Tool 목록 조회 (JWT 토큰 사용) - Legacy, use _fetch_tools_from_gateway_with_iam instead"""
        print(f"🔍 Fetching tools from gateway (JWT): {gateway_url}")

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

                if 'result' not in result:
                    raise Exception(f"Invalid MCP Protocol response: {result}")

                if 'tools' not in result['result']:
                    raise Exception(f"No tools in response: {result}")

                tools_data = result['result']['tools']

                if tools_data:
                    for tool_data in tools_data:
                        raw_name = tool_data['name']
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
                    break
                else:
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

    async def _fetch_tools_from_runtime_with_jwt(self, runtime_endpoint: str, max_retries: int = 5, tool_prefix: str = None) -> List[Tool]:
        """Runtime endpoint에서 직접 Tool 목록 조회 (JWT 토큰 사용)

        Args:
            runtime_endpoint: Runtime 엔드포인트 URL
            max_retries: 최대 재시도 횟수
            tool_prefix: 필터링할 tool prefix (예: "youtube") - Multi-MCP Proxy용
        """
        print(f"🔍 Fetching tools from Runtime (direct): {runtime_endpoint}")
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

                if 'result' not in result:
                    raise Exception(f"Invalid MCP Protocol response: {result}")

                if 'tools' not in result['result']:
                    raise Exception(f"No tools in response: {result}")

                tools_data = result['result']['tools']

                if tools_data:
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
                    break
                else:
                    if attempt < max_retries - 1:
                        print(f"⏳ Tools empty, waiting for Runtime... (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(10)
                    else:
                        print(f"⚠️ No tools found after {max_retries} attempts")

            print(f"🎉 Total tools fetched from Runtime: {len(tools)}")
            return tools

        except Exception as e:
            print(f"❌ Failed to fetch tools from Runtime: {str(e)}")
            raise Exception(f"Runtime Tool 조회 실패 (JWT): {str(e)}")

    def _parse_sse_response(self, sse_text: str) -> dict:
        """SSE (Server-Sent Events) 응답 파싱"""
        for line in sse_text.strip().split('\n'):
            if line.startswith('data: '):
                json_str = line[6:]
                return json.loads(json_str)
        return json.loads(sse_text)
