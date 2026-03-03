"""MCP Domain Services"""
from typing import List, Optional
from .entities import (
    MCP, ExternalMCP, InternalDeployMCP, InternalCreateMCP,
    ExternalEndpointMCP, ExternalContainerMCP
)
from .value_objects import MCPId, MCPType, AuthConfig, DeploymentConfig, APITarget, ExternalAuthType


class MCPFactory:
    """MCP 팩토리"""
    
    @staticmethod
    def create_external_mcp(
        id: MCPId,
        name: str,
        description: str,
        team_tag_ids: List[str],
        server_name: str,
        mcp_config: dict
    ) -> ExternalMCP:
        """외부 MCP 생성 (Multi-MCP Proxy 방식)

        Args:
            server_name: Tool prefix (예: "youtube", "github")
            mcp_config: {command, args, env}
        """
        return ExternalMCP(
            id=id,
            name=name,
            description=description,
            team_tag_ids=team_tag_ids,
            server_name=server_name,
            mcp_config=mcp_config
        )
    
    @staticmethod
    def create_internal_deploy_mcp(
        id: MCPId,
        name: str,
        description: str,
        team_tag_ids: List[str],
        ecr_repository: str,
        image_tag: str,
        deployment_config: DeploymentConfig,
        enable_semantic_search: bool = False
    ) -> InternalDeployMCP:
        """내부 배포 MCP 생성"""
        return InternalDeployMCP(
            id=id,
            name=name,
            description=description,
            team_tag_ids=team_tag_ids,
            ecr_repository=ecr_repository,
            image_tag=image_tag,
            deployment_config=deployment_config,
            enable_semantic_search=enable_semantic_search
        )
    
    @staticmethod
    def create_internal_create_mcp(
        id: MCPId,
        name: str,
        description: str,
        team_tag_ids: List[str],
        selected_api_targets: List[APITarget],
        enable_semantic_search: bool = False
    ) -> InternalCreateMCP:
        """내부 생성 MCP 생성"""
        return InternalCreateMCP(
            id=id,
            name=name,
            description=description,
            team_tag_ids=team_tag_ids,
            selected_api_targets=selected_api_targets,
            enable_semantic_search=enable_semantic_search
        )

    @staticmethod
    def create_external_endpoint_mcp(
        id: MCPId,
        name: str,
        description: str,
        team_tag_ids: List[str],
        endpoint_url: str,
        auth_type: ExternalAuthType = ExternalAuthType.NO_AUTH,
        oauth_provider_arn: Optional[str] = None,
        user_pool_id: Optional[str] = None
    ) -> ExternalEndpointMCP:
        """외부 MCP (Endpoint URL 타입) 생성

        Args:
            endpoint_url: MCP 서버 엔드포인트 URL (예: https://knowledge-mcp.global.api.aws/)
            auth_type: 인증 방식 (no_auth | oauth)
            oauth_provider_arn: OAuth 사용 시 AgentCore Identity OAuth2 Credential Provider ARN
            user_pool_id: (Legacy) OAuth 사용 시 Cognito User Pool ID
        """
        return ExternalEndpointMCP(
            id=id,
            name=name,
            description=description,
            team_tag_ids=team_tag_ids,
            endpoint_url=endpoint_url,
            auth_type=auth_type,
            oauth_provider_arn=oauth_provider_arn,
            user_pool_id=user_pool_id
        )

    @staticmethod
    def create_external_container_mcp(
        id: MCPId,
        name: str,
        description: str,
        team_tag_ids: List[str],
        ecr_repository: str,
        image_tag: str,
        auth_type: ExternalAuthType = ExternalAuthType.NO_AUTH,
        user_pool_id: Optional[str] = None,
        environment: Optional[dict] = None
    ) -> ExternalContainerMCP:
        """외부 MCP (Container Image 타입) 생성

        Args:
            ecr_repository: ECR 리포지토리 이름
            image_tag: 이미지 태그
            auth_type: 인증 방식 (no_auth | oauth)
            user_pool_id: OAuth 사용 시 Cognito User Pool ID
            environment: 컨테이너 환경변수
        """
        return ExternalContainerMCP(
            id=id,
            name=name,
            description=description,
            team_tag_ids=team_tag_ids,
            ecr_repository=ecr_repository,
            image_tag=image_tag,
            auth_type=auth_type,
            user_pool_id=user_pool_id,
            environment=environment
        )


class GatewayService:
    """Gateway 서비스 (Mock 구현)"""

    def __init__(self):
        self._gateway_counter = 1

    async def check_gateway_health(self, gateway_id: str) -> dict:
        """Gateway Health 체크 (BedrockGatewayService에서 override)

        Returns:
            dict: {'healthy': bool, 'status': str, 'message': str}
        """
        raise NotImplementedError("Subclass must implement check_gateway_health")

    async def create_dedicated_gateway(self, mcp: MCP) -> str:
        """전용 Gateway 생성"""
        gateway_id = f"gw-{self._gateway_counter:08x}"
        self._gateway_counter += 1

        # Mock Gateway 엔드포인트 생성
        endpoint = f"https://{gateway_id}.gateway.bedrock-agentcore.ap-northeast-2.amazonaws.com/mcp"
        mcp.set_endpoint(endpoint)

        return gateway_id

    async def update_dedicated_gateway(self, mcp: MCP) -> None:
        """전용 Gateway 업데이트 (Mock - BedrockGatewayService에서 override)"""
        # Mock 구현: 실제로는 BedrockGatewayService에서 AgentCore Gateway API 호출
        print(f"🔄 [Mock] Updating Gateway for MCP: {mcp.name}")
        if isinstance(mcp, InternalCreateMCP):
            print(f"   - Description: {mcp.description}")
            print(f"   - {len(mcp.selected_api_targets)} API targets")
            for target in mcp.selected_api_targets:
                print(f"   - {target.name}: {target.method} {target.endpoint}")
        pass

    async def add_to_shared_gateway(self, mcp: ExternalMCP) -> str:
        """공유 Gateway에 추가"""
        shared_gateway_id = "gw-shared01"
        endpoint = f"https://{shared_gateway_id}.gateway.bedrock-agentcore.ap-northeast-2.amazonaws.com/mcp"
        mcp.set_endpoint(endpoint)
        mcp.set_gateway_id(shared_gateway_id)

        return shared_gateway_id

    async def create_deploy_mcp_infrastructure(self, mcp: InternalDeployMCP) -> str:
        """Internal Deploy MCP 인프라 생성 (Mock - BedrockGatewayService에서 override)"""
        print(f"🚀 [Mock] Creating Deploy MCP Infrastructure for: {mcp.name}")
        gateway_id = f"gw-{self._gateway_counter:08x}"
        self._gateway_counter += 1
        endpoint = f"https://{gateway_id}.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"
        mcp.set_endpoint(endpoint)
        return gateway_id

    async def update_deploy_mcp_infrastructure(self, mcp: InternalDeployMCP) -> None:
        """Internal Deploy MCP 인프라 업데이트 (Mock - BedrockGatewayService에서 override)

        Image tag 변경 시 Runtime 재생성, Gateway Target 업데이트
        """
        print(f"🔄 [Mock] Updating Deploy MCP Infrastructure for: {mcp.name}")
        print(f"   - ECR Repository: {mcp.ecr_repository}")
        print(f"   - Image Tag: {mcp.image_tag}")
        pass

    async def create_external_mcp_infrastructure(self, mcp: ExternalMCP) -> str:
        """External MCP 인프라 생성 (Mock - BedrockGatewayService에서 override)

        Smithery Proxy Runtime + 공유 Gateway Target 생성
        """
        print(f"🚀 [Mock] Creating External MCP Infrastructure for: {mcp.name}")
        print(f"   - Smithery URL: {mcp.server_url}")
        gateway_id = f"gw-external-shared"
        endpoint = f"https://{gateway_id}.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"
        mcp.set_endpoint(endpoint)
        mcp.set_gateway_id(gateway_id)
        mcp.set_runtime_id("runtime-mock")
        mcp.set_runtime_url("https://runtime-mock.bedrock-agentcore.us-east-1.amazonaws.com")
        mcp.set_target_id("target-mock")
        return gateway_id

    async def create_external_endpoint_target(self, mcp) -> tuple:
        """External Endpoint MCP Target 생성 (Mock - BedrockGatewayService에서 override)

        기존 MCP 서버 엔드포인트에 직접 연결하는 Gateway Target을 생성합니다.
        Returns: (gateway_id, target_id, tools)
        """
        print(f"🚀 [Mock] Creating External Endpoint Target for: {mcp.name}")
        gateway_id = "gw-external-shared"
        target_id = f"target-{mcp.name}"
        return gateway_id, target_id, []

    async def update_external_endpoint_target(self, mcp) -> None:
        """External Endpoint MCP Target 업데이트 (Mock - BedrockGatewayService에서 override)

        기존 Target을 삭제하고 새로운 설정으로 재생성합니다.
        """
        print(f"🔄 [Mock] Updating External Endpoint Target for: {mcp.name}")
        pass


class ECRService:
    """ECR 서비스"""

    def __init__(self):
        import boto3
        from ...config import settings

        # Build kwargs for boto3 client
        aws_kwargs = {'region_name': settings.AWS_REGION}
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            aws_kwargs['aws_access_key_id'] = settings.AWS_ACCESS_KEY_ID
            aws_kwargs['aws_secret_access_key'] = settings.AWS_SECRET_ACCESS_KEY

        self.ecr_client = boto3.client('ecr', **aws_kwargs)
        self.repository_name = settings.ECR_REPOSITORY_NAME
        self.repository_uri = settings.ECR_REPOSITORY

    async def validate_image_exists(self, repository: str, tag: str) -> bool:
        """ECR 이미지 존재 검증"""
        try:
            response = self.ecr_client.describe_images(
                repositoryName=repository,
                imageIds=[{'imageTag': tag}]
            )
            return len(response.get('imageDetails', [])) > 0
        except Exception as e:
            print(f"Error validating ECR image: {e}")
            return False

    async def list_repositories(self) -> List[dict]:
        """ECR 리포지토리 목록 조회"""
        try:
            response = self.ecr_client.describe_repositories()
            repositories = []
            for repo in response.get('repositories', []):
                repositories.append({
                    'name': repo['repositoryName'],
                    'uri': repo['repositoryUri'],
                    'arn': repo['repositoryArn'],
                    'createdAt': repo['createdAt'].isoformat() if hasattr(repo['createdAt'], 'isoformat') else str(repo['createdAt'])
                })
            # 이름순 정렬
            repositories.sort(key=lambda x: x['name'])
            return repositories
        except Exception as e:
            print(f"Error listing ECR repositories: {e}")
            return []

    async def list_image_tags(self, repository: str = None) -> List[dict]:
        """ECR 이미지 태그 목록 조회"""
        repo_name = repository or self.repository_name
        try:
            response = self.ecr_client.describe_images(
                repositoryName=repo_name,
                maxResults=100,
                filter={'tagStatus': 'TAGGED'}
            )

            images = []
            for image_detail in response.get('imageDetails', []):
                if 'imageTags' in image_detail:
                    for tag in image_detail['imageTags']:
                        images.append({
                            'tag': tag,
                            'digest': image_detail.get('imageDigest', ''),
                            'pushedAt': image_detail.get('imagePushedAt').isoformat() if image_detail.get('imagePushedAt') else '',
                            'sizeInBytes': image_detail.get('imageSizeInBytes', 0),
                            'repositoryName': repo_name
                        })

            # 최신순으로 정렬
            images.sort(key=lambda x: x['pushedAt'], reverse=True)
            return images

        except Exception as e:
            print(f"Error listing ECR image tags: {e}")
            return []

    def get_repository_info(self) -> dict:
        """ECR 레포지토리 정보 조회"""
        try:
            response = self.ecr_client.describe_repositories(
                repositoryNames=[self.repository_name]
            )
            if response['repositories']:
                repo = response['repositories'][0]
                return {
                    'name': repo['repositoryName'],
                    'uri': repo['repositoryUri'],
                    'arn': repo['repositoryArn'],
                    'createdAt': repo['createdAt'].isoformat() if hasattr(repo['createdAt'], 'isoformat') else str(repo['createdAt'])
                }
        except Exception as e:
            print(f"Error fetching repository info: {e}")

        # Fallback
        return {
            'name': self.repository_name,
            'uri': self.repository_uri,
            'arn': '',
            'createdAt': ''
        }


class KEISService:
    """KEIS API 서비스"""

    def __init__(self):
        pass

    async def get_available_apis(self) -> List[APITarget]:
        """사용 가능한 API 목록 조회 (API Catalog 제거로 빈 리스트 반환)"""
        return []
