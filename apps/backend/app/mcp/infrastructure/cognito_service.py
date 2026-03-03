"""Cognito Service for MCP OAuth Authentication

공유 Cognito 인프라를 관리하고 MCP 배포에 재사용할 수 있도록 합니다.
- User Pool (1개 공유)
- Resource Server (scopes 관리)
- M2M Client (Gateway용)
"""

import boto3
import time
from typing import Dict, Optional, Tuple, List
from app.config import settings


class CognitoService:
    """Cognito 인프라 관리 서비스"""

    # 공유 리소스 이름 (config.py에서 가져옴)
    USER_POOL_NAME = settings.COGNITO_USER_POOL_NAME
    RESOURCE_SERVER_ID = settings.COGNITO_RESOURCE_SERVER_ID
    RESOURCE_SERVER_NAME = settings.COGNITO_RESOURCE_SERVER_NAME
    DEFAULT_SCOPES = [
        {"ScopeName": "read", "ScopeDescription": "Read MCP tools"},
        {"ScopeName": "write", "ScopeDescription": "Execute MCP tools"},
        {"ScopeName": "invoke", "ScopeDescription": "Invoke MCP runtime"}
    ]

    def __init__(self):
        self.region = settings.AWS_REGION

        # Build kwargs for boto3 clients, only including credentials if they are non-empty
        # If empty, boto3 will use AWS_PROFILE from environment variables or ~/.aws/credentials
        aws_kwargs = {}
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            aws_kwargs['aws_access_key_id'] = settings.AWS_ACCESS_KEY_ID
            aws_kwargs['aws_secret_access_key'] = settings.AWS_SECRET_ACCESS_KEY

        self.cognito_client = boto3.client(
            'cognito-idp',
            region_name=self.region,
            **aws_kwargs
        )
        self.sts_client = boto3.client('sts', **aws_kwargs)
        self.account_id = self.sts_client.get_caller_identity()["Account"]

        # 캐시된 인프라 정보
        self._user_pool_id: Optional[str] = None
        self._discovery_url: Optional[str] = None

    async def get_or_create_shared_infrastructure(self) -> Dict:
        """공유 Cognito 인프라 조회 또는 생성

        Returns:
            Dict: {
                'user_pool_id': str,
                'discovery_url': str,
                'resource_server_id': str
            }
        """
        print("🔐 Cognito 공유 인프라 확인 중...")

        # 1. User Pool 조회/생성
        user_pool_id = await self._get_or_create_user_pool()

        # 2. Resource Server 조회/생성
        await self._get_or_create_resource_server(user_pool_id)

        # 3. Discovery URL 생성
        discovery_url = f"https://cognito-idp.{self.region}.amazonaws.com/{user_pool_id}/.well-known/openid-configuration"

        self._user_pool_id = user_pool_id
        self._discovery_url = discovery_url

        print(f"✅ Cognito 인프라 준비 완료")
        print(f"   User Pool: {user_pool_id}")
        print(f"   Discovery URL: {discovery_url}")

        return {
            'user_pool_id': user_pool_id,
            'discovery_url': discovery_url,
            'resource_server_id': self.RESOURCE_SERVER_ID
        }

    async def _get_or_create_user_pool(self) -> str:
        """User Pool 조회 또는 생성"""
        print("🔍 User Pool 확인 중...")

        # 기존 User Pool 조회
        response = self.cognito_client.list_user_pools(MaxResults=60)
        for pool in response.get("UserPools", []):
            if pool["Name"] == self.USER_POOL_NAME:
                user_pool_id = pool["Id"]
                print(f"♻️ 기존 User Pool 사용: {user_pool_id}")
                return user_pool_id

        # 새 User Pool 생성
        print("🆕 새 User Pool 생성 중...")
        created = self.cognito_client.create_user_pool(
            PoolName=self.USER_POOL_NAME,
            AutoVerifiedAttributes=['email'],
            UsernameAttributes=['email'],
            Policies={
                'PasswordPolicy': {
                    'MinimumLength': 8,
                    'RequireUppercase': True,
                    'RequireLowercase': True,
                    'RequireNumbers': True,
                    'RequireSymbols': False
                }
            }
        )
        user_pool_id = created["UserPool"]["Id"]

        # 도메인 생성 (OAuth 토큰 엔드포인트에 필요)
        domain_prefix = f"mcp-{user_pool_id.split('_')[1].lower()}"
        try:
            self.cognito_client.create_user_pool_domain(
                Domain=domain_prefix,
                UserPoolId=user_pool_id
            )
            print(f"✅ User Pool 도메인 생성: {domain_prefix}")
        except self.cognito_client.exceptions.InvalidParameterException:
            # 도메인이 이미 존재하는 경우 무시
            pass

        print(f"✅ User Pool 생성 완료: {user_pool_id}")
        return user_pool_id

    async def _get_or_create_resource_server(self, user_pool_id: str) -> str:
        """Resource Server 조회 또는 생성"""
        print("🔍 Resource Server 확인 중...")

        try:
            self.cognito_client.describe_resource_server(
                UserPoolId=user_pool_id,
                Identifier=self.RESOURCE_SERVER_ID
            )
            print(f"♻️ 기존 Resource Server 사용: {self.RESOURCE_SERVER_ID}")
            return self.RESOURCE_SERVER_ID

        except self.cognito_client.exceptions.ResourceNotFoundException:
            print("🆕 새 Resource Server 생성 중...")
            self.cognito_client.create_resource_server(
                UserPoolId=user_pool_id,
                Identifier=self.RESOURCE_SERVER_ID,
                Name=self.RESOURCE_SERVER_NAME,
                Scopes=self.DEFAULT_SCOPES
            )
            print(f"✅ Resource Server 생성 완료: {self.RESOURCE_SERVER_ID}")
            return self.RESOURCE_SERVER_ID

    async def get_or_create_m2m_client(
        self,
        client_name: str,
        scope_names: list = None
    ) -> Tuple[str, str]:
        """M2M (Machine-to-Machine) 클라이언트 조회 또는 생성

        Args:
            client_name: 클라이언트 이름 (예: "mcp-gateway-client")
            scope_names: 스코프 이름 목록 (기본값: ["read", "write", "invoke"])

        Returns:
            Tuple[str, str]: (client_id, client_secret)
        """
        if not self._user_pool_id:
            await self.get_or_create_shared_infrastructure()

        user_pool_id = self._user_pool_id

        print(f"🔍 M2M 클라이언트 확인 중: {client_name}")

        if scope_names is None:
            scope_names = ["read", "write", "invoke"]

        # 기존 클라이언트 조회
        response = self.cognito_client.list_user_pool_clients(
            UserPoolId=user_pool_id,
            MaxResults=60
        )
        for client in response.get("UserPoolClients", []):
            if client["ClientName"] == client_name:
                describe = self.cognito_client.describe_user_pool_client(
                    UserPoolId=user_pool_id,
                    ClientId=client["ClientId"]
                )
                client_id = client["ClientId"]
                client_secret = describe["UserPoolClient"].get("ClientSecret", "")
                print(f"♻️ 기존 M2M 클라이언트 사용: {client_id}")
                return client_id, client_secret

        # 스코프 문자열 생성
        oauth_scopes = [f"{self.RESOURCE_SERVER_ID}/{scope}" for scope in scope_names]

        # 새 M2M 클라이언트 생성
        print("🆕 새 M2M 클라이언트 생성 중...")
        created = self.cognito_client.create_user_pool_client(
            UserPoolId=user_pool_id,
            ClientName=client_name,
            GenerateSecret=True,
            AllowedOAuthFlows=["client_credentials"],
            AllowedOAuthScopes=oauth_scopes,
            AllowedOAuthFlowsUserPoolClient=True,
            SupportedIdentityProviders=["COGNITO"],
            ExplicitAuthFlows=["ALLOW_REFRESH_TOKEN_AUTH"]
        )

        client_id = created["UserPoolClient"]["ClientId"]
        client_secret = created["UserPoolClient"]["ClientSecret"]
        print(f"✅ M2M 클라이언트 생성 완료: {client_id}")

        return client_id, client_secret

    def get_token_endpoint(self, user_pool_id: str = None) -> str:
        """OAuth 토큰 엔드포인트 URL 반환"""
        pool_id = user_pool_id or self._user_pool_id
        if not pool_id:
            raise ValueError("User Pool ID가 설정되지 않았습니다")

        # User Pool 도메인 조회
        response = self.cognito_client.describe_user_pool(UserPoolId=pool_id)
        domain = response["UserPool"].get("Domain")

        if domain:
            return f"https://{domain}.auth.{self.region}.amazoncognito.com/oauth2/token"
        else:
            # 도메인이 없으면 기본 형식 사용
            domain_prefix = f"mcp-{pool_id.split('_')[1].lower()}"
            return f"https://{domain_prefix}.auth.{self.region}.amazoncognito.com/oauth2/token"

    def get_discovery_url(self, user_pool_id: str = None) -> str:
        """OpenID Connect Discovery URL 반환"""
        pool_id = user_pool_id or self._user_pool_id
        if not pool_id:
            raise ValueError("User Pool ID가 설정되지 않았습니다")

        return f"https://cognito-idp.{self.region}.amazonaws.com/{pool_id}/.well-known/openid-configuration"

    async def get_access_token(
        self,
        client_id: str,
        client_secret: str,
        scopes: list = None
    ) -> Dict:
        """OAuth2 액세스 토큰 획득 (client_credentials flow)

        Args:
            client_id: M2M 클라이언트 ID
            client_secret: 클라이언트 시크릿
            scopes: 요청할 스코프 목록

        Returns:
            Dict: 토큰 정보 {'access_token': str, 'expires_in': int, ...}
        """
        import requests

        if scopes is None:
            scopes = [f"{self.RESOURCE_SERVER_ID}/read",
                     f"{self.RESOURCE_SERVER_ID}/write",
                     f"{self.RESOURCE_SERVER_ID}/invoke"]

        token_url = self.get_token_endpoint()

        response = requests.post(
            token_url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": " ".join(scopes)
            }
        )

        response.raise_for_status()
        return response.json()

    async def list_all_user_pools(self) -> List[Dict]:
        """AWS 계정 내 모든 Cognito User Pool 목록 조회

        Returns:
            List[Dict]: [
                {
                    'id': str,  # User Pool ID
                    'name': str,  # User Pool 이름
                    'domain': str,  # User Pool 도메인 (있는 경우)
                    'discovery_url': str,  # OpenID Connect Discovery URL
                    'created_at': str  # 생성일
                }
            ]
        """
        print("🔍 AWS 계정 내 모든 User Pool 조회 중...")

        all_pools = []
        next_token = None

        while True:
            if next_token:
                response = self.cognito_client.list_user_pools(
                    MaxResults=60,
                    NextToken=next_token
                )
            else:
                response = self.cognito_client.list_user_pools(MaxResults=60)

            for pool in response.get("UserPools", []):
                pool_id = pool["Id"]
                pool_name = pool["Name"]
                created_at = pool.get("CreationDate")

                # 도메인 조회 (추가 API 호출 필요)
                domain = None
                try:
                    pool_detail = self.cognito_client.describe_user_pool(UserPoolId=pool_id)
                    domain = pool_detail["UserPool"].get("Domain")
                except Exception:
                    pass

                discovery_url = f"https://cognito-idp.{self.region}.amazonaws.com/{pool_id}/.well-known/openid-configuration"

                all_pools.append({
                    'id': pool_id,
                    'name': pool_name,
                    'domain': domain,
                    'discovery_url': discovery_url,
                    'created_at': created_at.isoformat() if created_at else None
                })

            next_token = response.get("NextToken")
            if not next_token:
                break

        print(f"✅ 총 {len(all_pools)}개 User Pool 조회 완료")
        return all_pools

    async def get_user_pool_oauth_config(self, user_pool_id: str) -> Dict:
        """특정 User Pool의 OAuth 설정 조회 (JWT Authorizer용)

        Args:
            user_pool_id: Cognito User Pool ID

        Returns:
            Dict: {
                'user_pool_id': str,
                'discovery_url': str,
                'token_endpoint': str,
                'domain': str
            }
        """
        print(f"🔍 User Pool OAuth 설정 조회: {user_pool_id}")

        pool_detail = self.cognito_client.describe_user_pool(UserPoolId=user_pool_id)
        domain = pool_detail["UserPool"].get("Domain")

        discovery_url = f"https://cognito-idp.{self.region}.amazonaws.com/{user_pool_id}/.well-known/openid-configuration"

        token_endpoint = None
        if domain:
            token_endpoint = f"https://{domain}.auth.{self.region}.amazoncognito.com/oauth2/token"

        return {
            'user_pool_id': user_pool_id,
            'discovery_url': discovery_url,
            'token_endpoint': token_endpoint,
            'domain': domain
        }

    def get_shared_user_pool_id(self) -> Optional[str]:
        """공유 User Pool ID 반환 (캐시된 값)"""
        return self._user_pool_id

    def get_shared_discovery_url(self) -> Optional[str]:
        """공유 Discovery URL 반환 (캐시된 값)"""
        return self._discovery_url
