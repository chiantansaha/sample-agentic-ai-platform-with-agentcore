"""MCP Domain Dependencies"""
import logging
from functools import lru_cache
from typing import Union

from app.config import settings
from ..application.service import MCPApplicationService
from ..domain.services import ECRService, KEISService
from ..infrastructure.mcp_repository_impl import DynamoDBMCPRepository
from ..infrastructure.mcp_version_repository_impl import DynamoDBMCPVersionRepository
from ..infrastructure.mock_mcp_repository import MockMCPRepository
from ..infrastructure.mock_mcp_version_repository import MockMCPVersionRepository
from ..infrastructure.gateway_service_impl import BedrockGatewayService

logger = logging.getLogger(__name__)


def _is_mock_mode() -> bool:
    """Mock 모드 여부 확인"""
    return (
        settings.ENVIRONMENT in ("dev", "development", "local")
        and not settings.DYNAMODB_MCP_TABLE
    )


@lru_cache()
def get_mcp_repository() -> Union[DynamoDBMCPRepository, MockMCPRepository]:
    """MCP Repository 싱글톤"""
    if _is_mock_mode():
        logger.info("📦 Using MockMCPRepository (demo mode)")
        return MockMCPRepository()
    return DynamoDBMCPRepository()


@lru_cache()
def get_version_repository() -> Union[DynamoDBMCPVersionRepository, MockMCPVersionRepository]:
    """MCP Version Repository 싱글톤"""
    if _is_mock_mode():
        logger.info("📦 Using MockMCPVersionRepository (demo mode)")
        return MockMCPVersionRepository()
    return DynamoDBMCPVersionRepository()


@lru_cache()
def get_gateway_service():
    """Gateway Service 싱글톤"""
    return BedrockGatewayService()


@lru_cache()
def get_ecr_service():
    """ECR Service 싱글톤"""
    return ECRService()


@lru_cache()
def get_keis_service():
    """KEIS Service 싱글톤"""
    return KEISService()


def get_mcp_service() -> MCPApplicationService:
    """MCP Application Service 의존성 주입"""
    return MCPApplicationService(
        mcp_repository=get_mcp_repository(),
        version_repository=get_version_repository(),
        gateway_service=get_gateway_service(),
        ecr_service=get_ecr_service(),
        keis_service=get_keis_service()
    )
