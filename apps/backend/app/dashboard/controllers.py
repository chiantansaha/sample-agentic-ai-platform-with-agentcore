"""Dashboard Controllers

각 도메인 서비스에서 통계를 수집하여 Dashboard에 제공합니다.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status

from app.config import settings
from app.middleware.auth import verify_okta_token
from app.mcp.application.service import MCPApplicationService
from app.mcp.presentation.dependencies import get_mcp_service
from app.agent.application.service import AgentApplicationService
from app.agent.infrastructure.repositories import DynamoDBAgentRepository
from app.agent.infrastructure.repositories.dynamodb_agent_version_repository import DynamoDBAgentVersionRepository
from app.agent.infrastructure.repositories.mock_agent_repository import MockAgentRepository
from app.agent.infrastructure.repositories.mock_agent_version_repository import MockAgentVersionRepository
from app.knowledge_bases.application.service import KBApplicationService
from app.knowledge_bases.infrastructure.repositories.dynamodb_kb_repository import DynamoDBKBRepository
from app.knowledge_bases.infrastructure.repositories.dynamodb_version_repository import DynamoDBVersionRepository
from app.knowledge_bases.infrastructure.repositories.mock_kb_repository import MockKBRepository
from app.knowledge_bases.infrastructure.repositories.mock_version_repository import MockVersionRepository

logger = logging.getLogger(__name__)
router = APIRouter()


def _is_mock_mode() -> bool:
    """Mock 모드 여부 확인"""
    return settings.ENVIRONMENT in ("dev", "development", "local")


def get_agent_service() -> AgentApplicationService:
    """Agent Service 의존성 주입"""
    if _is_mock_mode() and not settings.DYNAMODB_AGENT_TABLE:
        logger.info("📦 Using MockAgentRepository (demo mode)")
        agent_repository = MockAgentRepository()
        version_repository = MockAgentVersionRepository()
    else:
        agent_repository = DynamoDBAgentRepository()
        version_repository = DynamoDBAgentVersionRepository()
    return AgentApplicationService(agent_repository, version_repository)


def get_kb_service() -> KBApplicationService:
    """KB Service 의존성 주입"""
    if _is_mock_mode() and not settings.DYNAMODB_KB_TABLE:
        logger.info("📦 Using MockKBRepository (demo mode)")
        kb_repository = MockKBRepository()
        version_repository = MockVersionRepository()
    else:
        kb_repository = DynamoDBKBRepository()
        version_repository = DynamoDBVersionRepository()
    return KBApplicationService(kb_repository, version_repository)


@router.get("/stats", response_model=dict)
async def get_dashboard_stats(
    user: dict = Depends(verify_okta_token),
    mcp_service: MCPApplicationService = Depends(get_mcp_service),
    agent_service: AgentApplicationService = Depends(get_agent_service),
    kb_service: KBApplicationService = Depends(get_kb_service)
):
    """Dashboard 통계 조회

    각 도메인 서비스에서 통계를 수집합니다.
    - MCP: mcp_service.get_mcp_stats()
    - Agent: agent_service.get_agent_stats()
    - KB: kb_service.get_kb_stats()
    """
    try:
        # MCP 통계 (실제 Gateway health 체크 포함)
        mcp_stats = await mcp_service.get_mcp_stats()

        # Agent 통계
        agent_stats = await agent_service.get_agent_stats()

        # KB 통계
        kb_stats = await kb_service.get_kb_stats()

        return {
            "data": {
                "mcps": mcp_stats,
                "agents": agent_stats,
                "knowledgeBases": kb_stats
            },
            "status": 200
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve dashboard stats: {str(e)}"
        )
