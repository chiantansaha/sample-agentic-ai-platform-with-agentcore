"""Application configuration"""

import os
from typing import List, Optional, Union
from pydantic_settings import BaseSettings
from pydantic import field_validator


# Determine which .env file to use based on ENV_MODE
ENV_MODE = os.getenv("ENV_MODE", "development")
ENV_FILE = f".env.{ENV_MODE}" if ENV_MODE else ".env"


class Settings(BaseSettings):
    """Application settings"""

    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Agentic AI Platform"
    VERSION: str = "0.1.0"

    # CORS Settings - Load from .env file (comma-separated string)
    CORS_ORIGINS: Union[str, List[str]] = ""

    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string or list"""
        if isinstance(v, str):
            if not v or v.strip() == "":
                # Development fallback
                return [
                    "http://localhost:5173",
                    "http://localhost:3000",
                    "http://localhost:80",
                ]
            # Parse comma-separated string
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v

    # Database Settings (for future use)
    DATABASE_URL: str = "postgresql://user:password@localhost/dbname"

    # AWS Settings - Use environment variables or AWS credentials file
    AWS_REGION: str = "us-east-1"
    AWS_PROFILE: str = ""  # AWS profile name
    AWS_ACCESS_KEY_ID: str = ""  # Set via environment variable or AWS credentials
    AWS_SECRET_ACCESS_KEY: str = ""  # Set via environment variable or AWS credentials

    # AgentCore Identity - API Key Credential Provider
    # Provider는 최초 사용 시 자동 생성됨
    APIGEE_API_KEY: str = ""  # API Key 값 (Provider 생성 시 사용)
    APIGEE_KEY_CREDENTIAL_PROVIDER_ARN: str = ""  # 기존 Provider ARN (있으면 재사용)
    _APIGEE_API_KEY_PROVIDER_BASE: str = "apigee-key"  # Base name (환경 suffix 자동 추가)

    # Amadeus API OAuth Settings (for Internal MCP API targets)
    AMADEUS_API_KEY: str = ""
    AMADEUS_API_SECRET: str = ""
    AMADEUS_TOKEN_URL: str = "https://test.api.amadeus.com/v1/security/oauth2/token"
    AMADEUS_OAUTH_CREDENTIAL_PROVIDER_ARN: str = ""  # Auto-created if empty
    _AMADEUS_OAUTH_PROVIDER_BASE: str = "amadeus-oauth-provider"  # Base name

    # Smithery.ai Settings (External MCP)
    SMITHERY_API_KEY: str = ""  # Smithery.ai API Key (시스템 레벨 관리)

    # ECR Settings (for Internal MCP Deploy)
    ECR_REPOSITORY_NAME: str = "aws-agentic-ai-mcp-server-dev"
    ECR_REPOSITORY: str = ""

    # Cognito Settings (for Internal MCP OAuth)
    COGNITO_USER_POOL_NAME: str = "aws-agentic-ai-mcp-pool-dev"
    COGNITO_RESOURCE_SERVER_ID: str = "mcp-api"
    COGNITO_RESOURCE_SERVER_NAME: str = "MCP API Resource Server"

    # AgentCore Settings (Base names - 환경 suffix 자동 추가)
    _OAUTH_PROVIDER_BASE: str = "mcp-oauth-provider"
    _EXTERNAL_MCP_GATEWAY_BASE: str = "external-mcp-gateway"

    # Multi-MCP Proxy Settings (for External MCP)
    MCP_PROXY_REPOSITORY: str = "aws-agentic-ai-mcp-proxy-dev"
    MCP_PROXY_IMAGE_TAG: str = "latest"
    _MCP_PROXY_RUNTIME_BASE: str = "multi_mcp_proxy_runtime"  # Base name
    _MCP_PROXY_TARGET_BASE: str = "multi-mcp-proxy-target"  # Base name
    MCP_PROXY_CONFIG_TABLE: str = "mcp-proxy-config"  # Table name suffix (prefix added automatically)

    # DynamoDB Settings
    TABLE_PREFIX: str = "agentic-ai"
    ENVIRONMENT: str = "local"

    # DynamoDB Settings (원격 AWS DynamoDB 사용)
    DYNAMODB_ENDPOINT: str = ""  # 비어있으면 AWS DynamoDB 사용 (로컬이면 http://localhost:8000)
    DYNAMODB_AGENT_TABLE: str = ""  # .env.{ENV_MODE}에서 설정 필수
    DYNAMODB_KB_TABLE: str = ""
    DYNAMODB_KB_VERSIONS_TABLE: str = ""
    DYNAMODB_TEAMTAG_TABLE: str = ""
    DYNAMODB_PLAYGROUND_TABLE: str = ""
    DYNAMODB_PLAYGROUND_CONVERSATIONS_TABLE: str = ""
    DYNAMODB_MCP_TABLE: str = ""  # MCP 메인 테이블
    DYNAMODB_MCP_VERSIONS_TABLE: str = ""  # MCP 버전 테이블
    DYNAMODB_API_CATALOG_TABLE: str = ""  # API Catalog 테이블

    # Bedrock Settings
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    BEDROCK_KB_ROLE_ARN: str = ""
    # EMBEDDING_MODEL_ARN은 property로 동적 생성 (아래 참조)
    _EMBEDDING_MODEL_ID: str = "amazon.titan-embed-text-v1"  # Foundation model ID

    # S3 Settings
    S3_KB_FILES_BUCKET: str = ""  # Load from .env file

    # OpenSearch Settings
    OPENSEARCH_COLLECTION_ENDPOINT: str = ""
    OPENSEARCH_COLLECTION_ARN: str = ""

    # SQS Settings
    SQS_KB_CREATION_QUEUE_URL: str = ""

    # Lambda Settings
    LAMBDA_KB_CREATION_FUNCTION_NAME: str = "aws-agentic-ai-kb-creation-handler-dev"
    LAMBDA_KB_CREATION_ROLE_ARN: str = ""

    # Authentication Settings
    SKIP_AUTH: bool = True  # Skip JWT authentication (development only)

    # AgentCore Runtime Settings (Playground)
    AGENTCORE_CODE_BUCKET: str = ""
    AGENTCORE_ROLE_ARN: str = ""
    PLAYGROUND_SESSIONS_BUCKET: str = ""
    PLAYGROUND_CONVERSATIONS_TABLE: str = ""
    PLAYGROUND_RUNTIME_ROLE_ARN: str = ""
    PLAYGROUND_ECR_REPOSITORY: str = ""

    # CodeBuild Settings (Production Docker Builds)
    CODEBUILD_PROJECT_NAME: str = ""
    AGENT_BUILD_SOURCE_BUCKET: str = ""
    BASE_IMAGE_URI: str = ""  # Custom base image URI (e.g., 123456.dkr.ecr.us-east-1.amazonaws.com/agentcore-base:latest)

    @property
    def table_name_prefix(self) -> str:
        """Get table name prefix with environment"""
        return f"{self.TABLE_PREFIX}-{self.ENVIRONMENT}"

    # ============================================================
    # AgentCore Resource Names (환경별 자동 생성)
    # ============================================================

    @property
    def APIGEE_API_KEY_PROVIDER_NAME(self) -> str:
        """API Key Provider name with environment suffix"""
        return f"{self._APIGEE_API_KEY_PROVIDER_BASE}-{self.ENVIRONMENT}"

    @property
    def AMADEUS_OAUTH_PROVIDER_NAME(self) -> str:
        """Amadeus OAuth Provider name with environment suffix"""
        return f"{self._AMADEUS_OAUTH_PROVIDER_BASE}-{self.ENVIRONMENT}"

    @property
    def OAUTH_PROVIDER_NAME(self) -> str:
        """Internal MCP OAuth Provider name with environment suffix"""
        return f"{self._OAUTH_PROVIDER_BASE}-{self.ENVIRONMENT}"

    @property
    def EXTERNAL_MCP_GATEWAY_NAME(self) -> str:
        """External MCP Gateway name with environment suffix"""
        return f"{self._EXTERNAL_MCP_GATEWAY_BASE}-{self.ENVIRONMENT}"

    @property
    def MCP_PROXY_RUNTIME_NAME(self) -> str:
        """MCP Proxy Runtime name with environment suffix"""
        return f"{self._MCP_PROXY_RUNTIME_BASE}_{self.ENVIRONMENT}"

    @property
    def MCP_PROXY_TARGET_NAME(self) -> str:
        """MCP Proxy Gateway Target name with environment suffix"""
        return f"{self._MCP_PROXY_TARGET_BASE}-{self.ENVIRONMENT}"

    @property
    def EMBEDDING_MODEL_ARN(self) -> str:
        """Bedrock Embedding Model ARN - dynamically generated from AWS_REGION"""
        return f"arn:aws:bedrock:{self.AWS_REGION}::foundation-model/{self._EMBEDDING_MODEL_ID}"

    class Config:
        # 여러 .env 파일을 순차적으로 읽음 (나중에 읽은 파일이 우선순위 높음)
        # 1. .env (기본값)
        # 2. .env.{ENV_MODE} (환경별 설정, 예: .env.development)
        # 3. .env.{ENV_MODE}.local (로컬 오버라이드, gitignored, 최우선)
        env_file = (
            ".env",                      # 기본값
            ENV_FILE,                    # .env.development or .env.production
            f"{ENV_FILE}.local"          # .env.development.local (로컬용, 최우선)
        )
        env_file_encoding = 'utf-8'
        case_sensitive = True
        extra = "ignore"  # .env 파일의 추가 환경변수 무시


settings = Settings()

# AWS 자격증명을 시스템 환경변수로 설정 (boto3가 사용할 수 있도록)
if settings.AWS_PROFILE:
    os.environ["AWS_PROFILE"] = settings.AWS_PROFILE
    print(f"✅ [CONFIG] AWS_PROFILE set to: {settings.AWS_PROFILE}")
else:
    print("⚠️  [CONFIG] AWS credentials not set - using default credentials")
