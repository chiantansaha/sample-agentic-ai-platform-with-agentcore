"""FastAPI application entry point"""
import asyncio
import logging

# 로그 레벨을 INFO로 설정 (DEBUG는 너무 많은 로그 생성)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# botocore credentials 로그 비활성화
logging.getLogger('botocore.credentials').setLevel(logging.WARNING)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.mcp.presentation.controller import router as mcp_domain_router
from app.dashboard.controllers import router as dashboard_mcp_router
from app.agent.presentation import controller as agent_controller
from app.agent.presentation import local_chat_controller  # 로컬 채팅 컨트롤러
from app.knowledge_bases.presentation import controller as kb_controller
from app.playground.presentation import controller as playground_controller
from app.config import settings as app_settings

logger = logging.getLogger(__name__)


# 백그라운드 세션 정리 태스크
async def cleanup_local_sessions_task():
    """로컬 Agent 세션 만료 정리 태스크 (10분마다 실행)"""
    from app.agent.infrastructure.local_agent_runner import local_agent_runner

    while True:
        await asyncio.sleep(600)  # 10분마다 실행
        try:
            local_agent_runner.cleanup_expired_sessions(timeout_minutes=30)
        except Exception as e:
            logger.error(f"Failed to cleanup local sessions: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 실행되는 lifespan 이벤트"""
    # Startup
    logger.info("Starting local agent session cleanup task...")
    cleanup_task = asyncio.create_task(cleanup_local_sessions_task())

    yield

    # Shutdown
    logger.info("Stopping local agent session cleanup task...")
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Agentic AI Platform API",
    description="Backend API for Agentic AI Platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
# Resources
app.include_router(agent_controller.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(local_chat_controller.router, prefix="/api/v1/agents", tags=["local-chat"])  # 로컬 채팅
app.include_router(mcp_domain_router, prefix="/api/v1/mcps", tags=["mcps"])  # DDD MCP Router
app.include_router(kb_controller.router, prefix="/api/v1/knowledge-bases", tags=["knowledge-bases"])

# Playground & Dashboard
app.include_router(playground_controller.router, prefix="/api/v1/playground", tags=["playground"])  # DDD Pattern
app.include_router(dashboard_mcp_router, prefix="/api/v1/dashboard", tags=["dashboard"])  # Dashboard MCP Stats


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Agentic AI Platform API",
        "version": "0.1.0",
        "status": "healthy",
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "api_version": "0.1.0",
    }


@app.get("/api/v1/debug/config")
async def debug_config():
    """Debug endpoint to check environment variables"""
    return {
        "ENV_MODE": app_settings.ENV_MODE if hasattr(app_settings, 'ENV_MODE') else None,
        "CODEBUILD_PROJECT_NAME": app_settings.CODEBUILD_PROJECT_NAME,
        "AGENT_BUILD_SOURCE_BUCKET": app_settings.AGENT_BUILD_SOURCE_BUCKET,
        "PLAYGROUND_ECR_REPOSITORY": app_settings.PLAYGROUND_ECR_REPOSITORY,
        "loaded_env_file": app_settings.Config.env_file if hasattr(app_settings.Config, 'env_file') else None
    }
