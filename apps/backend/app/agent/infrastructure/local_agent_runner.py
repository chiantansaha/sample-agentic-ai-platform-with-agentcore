"""로컬에서 Strands Agent를 실행하는 모듈

세션 제한:
- 사용자당 1개 세션만 허용
- 새 Prepare 요청 시 기존 세션 자동 종료
- 메모리 최적화를 위한 정책
"""
import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from strands import Agent
from app.playground.infrastructure.code_generator.agent_code_generator import AgentCodeGenerator

logger = logging.getLogger(__name__)


class LocalAgentRunner:
    """로컬 Agent 실행 및 관리"""

    def __init__(self):
        self._sessions: Dict[str, Agent] = {}
        self._last_activity: Dict[str, datetime] = {}
        self._user_sessions: Dict[str, str] = {}  # user_id -> session_id 매핑
        self.code_generator = AgentCodeGenerator()

    async def create_agent(
        self,
        agent_id: str,
        user_id: str,
        system_prompt: str,
        model: str,
        mcp_ids: list[str],
        kb_ids: list[str],
    ) -> str:
        """Agent 생성 및 세션 ID 반환

        사용자당 1개 세션 제한:
        - 동일 user_id의 기존 세션이 있으면 자동 종료
        """
        # 기존 세션 정리 (사용자당 1개 제한)
        if user_id in self._user_sessions:
            old_session_id = self._user_sessions[user_id]
            self.cleanup_session(old_session_id)
            logger.info(f"Cleaned up old session for user {user_id}: {old_session_id}")

        session_id = f"local-{user_id}-{agent_id}-{uuid.uuid4().hex[:8]}"

        # MCP 설정 조회 (async)
        mcp_servers = await self._get_mcp_configs(mcp_ids)

        # KB 설정 조회 (async)
        kb_configs = await self._get_kb_configs(kb_ids)

        # Agent 설정
        agent_config = {
            "agent_id": agent_id,
            "agent_name": f"local-agent-{agent_id}",
            "version": "local",
            "model_id": model,
            "system_prompt": system_prompt,
            "temperature": 0.7,
            "max_tokens": 4096,
            "knowledge_bases": kb_configs,
            "mcp_servers": mcp_servers,
            "tools": [],
        }

        # Jinja2 템플릿으로 코드 생성 (로컬 테스트 모드)
        generated_files = self.code_generator.generate(
            agent_config=agent_config,
            session_bucket=None,
            session_prefix=None,
            local_testing=True,
        )

        agent_code = generated_files["agent.py"]

        # Agent 인스턴스 생성 (KB tools 포함)
        kb_tools_code = generated_files.get("kb_tools.py")
        agent = self._load_agent_from_code(agent_code, kb_tools_code)

        # 세션 저장
        self._sessions[session_id] = agent
        self._last_activity[session_id] = datetime.now()
        self._user_sessions[user_id] = session_id  # 사용자-세션 매핑 저장

        logger.info(f"Local agent created: {session_id}")
        return session_id

    def _load_agent_from_code(self, agent_code: str, kb_tools_code: str = None) -> Agent:
        """생성된 코드에서 Agent 인스턴스 추출

        Args:
            agent_code: agent.py 코드
            kb_tools_code: kb_tools.py 코드 (KB가 있는 경우)
        """
        import sys
        import types

        # kb_tools 모듈을 먼저 로드 (agent.py에서 import하기 전에)
        if kb_tools_code:
            kb_tools_module = types.ModuleType("kb_tools")
            exec(kb_tools_code, kb_tools_module.__dict__)
            sys.modules["kb_tools"] = kb_tools_module
            logger.info("kb_tools module loaded into sys.modules")

        namespace = {}
        exec(agent_code, namespace)

        get_or_create_agent = namespace.get("get_or_create_agent")
        if not get_or_create_agent:
            raise ValueError("get_or_create_agent function not found in generated code")

        # session_id=None으로 호출하면 새 Agent 인스턴스 반환
        agent = get_or_create_agent(session_id=None)

        # DEBUG: Tool registry 로깅
        if hasattr(agent, 'tool_registry') and agent.tool_registry:
            try:
                all_specs = agent.tool_registry.get_all_tool_specs()
                tool_names = [spec.get('name', 'unknown') for spec in all_specs]
                logger.info(f"[DEBUG] Agent tool registry - {len(tool_names)} tools: {tool_names}")
            except Exception as e:
                logger.warning(f"[DEBUG] Could not inspect tool specs: {e}")
        else:
            logger.warning("[DEBUG] Agent has no tool_registry or it's empty")

        return agent

    async def _get_kb_configs(self, kb_ids: list[str]) -> List[dict]:
        """KB ID로부터 KB 설정 조회

        Returns:
            Agent Code Generator의 knowledge_bases 형식:
            [
                {
                    "id": "kb-xxx",
                    "name": "KB 이름",
                    "knowledge_base_id": "Bedrock KB ID"
                }, ...
            ]
        """
        if not kb_ids:
            return []

        from app.knowledge_bases.infrastructure.repositories.dynamodb_kb_repository import DynamoDBKBRepository

        kb_repo = DynamoDBKBRepository()
        configs = []

        for kb_id in kb_ids:
            try:
                kb = await kb_repo.find_by_id(kb_id)

                if not kb:
                    logger.warning(f"KB not found: {kb_id}")
                    continue

                configs.append({
                    "id": kb.id.value if hasattr(kb.id, 'value') else kb.id,
                    "name": kb.name,
                    "knowledge_base_id": kb.bedrock_kb_id
                })
                logger.info(f"KB config added: {kb.name} (bedrock_kb_id: {kb.bedrock_kb_id})")

            except Exception as e:
                logger.error(f"Failed to get KB config for {kb_id}: {e}")
                continue

        logger.info(f"Loaded {len(configs)} KB configs from {len(kb_ids)} KB IDs")
        return configs

    async def _get_mcp_configs(self, mcp_ids: list[str]) -> List[dict]:
        """MCP ID로부터 MCP 설정 조회

        MCP 타입별 변환 로직:
        - ExternalEndpointMCP: endpoint_url 사용, auth_type에 따라 인증 설정
        - ExternalContainerMCP: runtime_url 사용 (배포된 경우)
        - ExternalMCP (Legacy): mcp_config 사용 (stdio 방식)
        - InternalDeployMCP: runtime_url 사용
        - InternalCreateMCP: endpoint (gateway) 사용

        Returns:
            Agent Code Generator의 mcp_servers 형식:
            [
                {
                    "name": "server_name",
                    "transport": "http" | "sse" | "stdio",
                    "url": "http://...",
                    "headers": {...},        # HTTP 인증 헤더 (선택)
                    "auth_type": "iam" | "no_auth" | "oauth",  # 인증 타입
                    "command": "uvx",        # stdio 방식
                    "args": [...]            # stdio 방식
                }, ...
            ]
        """
        if not mcp_ids:
            return []

        from app.mcp.infrastructure.mcp_repository_impl import DynamoDBMCPRepository
        from app.mcp.domain.entities import (
            ExternalMCP, ExternalEndpointMCP, ExternalContainerMCP,
            InternalDeployMCP, InternalCreateMCP
        )
        from app.mcp.domain.value_objects import MCPId, Status, ExternalAuthType

        mcp_repo = DynamoDBMCPRepository()
        configs = []

        for mcp_id in mcp_ids:
            try:
                mcp = await mcp_repo.find_by_id(MCPId(mcp_id))

                if not mcp:
                    logger.warning(f"MCP not found: {mcp_id}")
                    continue

                if mcp.status != Status.ENABLED:
                    logger.info(f"MCP {mcp_id} is disabled, skipping")
                    continue

                config = self._convert_mcp_to_config(mcp)
                if config:
                    configs.append(config)
                    logger.info(f"MCP config added: {mcp.name} ({type(mcp).__name__})")

            except Exception as e:
                logger.error(f"Failed to get MCP config for {mcp_id}: {e}")
                continue

        logger.info(f"Loaded {len(configs)} MCP configs from {len(mcp_ids)} MCP IDs")
        return configs

    def _convert_mcp_to_config(self, mcp) -> Optional[dict]:
        """MCP 엔티티를 Agent Code Generator용 config로 변환"""
        from app.mcp.domain.entities import (
            ExternalMCP, ExternalEndpointMCP, ExternalContainerMCP,
            InternalDeployMCP, InternalCreateMCP
        )
        from app.mcp.domain.value_objects import ExternalAuthType

        # ExternalEndpointMCP: URL 직접 연결
        # 로컬 테스트에서는 Gateway 대신 원본 endpoint_url 사용 (IAM 인증 불가)
        if isinstance(mcp, ExternalEndpointMCP):
            logger.info(f"[DEBUG] ExternalEndpointMCP: name={mcp.name}, gateway_id={mcp.gateway_id}, endpoint={mcp.endpoint}, endpoint_url={mcp.endpoint_url}")
            if not mcp.endpoint_url:
                logger.warning(f"ExternalEndpointMCP {mcp.name} has no endpoint_url")
                return None

            # 로컬 테스트 환경에서는 Gateway 없이 원본 URL로 직접 연결
            # (Gateway는 IAM 인증 필요하므로 로컬에서 사용 불가)
            config = {
                "name": self._sanitize_name(mcp.name),
                "transport": "http",
                "url": mcp.endpoint_url,  # 항상 원본 endpoint_url 사용
                "auth_type": "no_auth",   # 로컬 테스트에서는 IAM 인증 불가
            }

            if mcp.gateway_id:
                logger.info(f"[DEBUG] Gateway exists ({mcp.gateway_id}) but using endpoint_url for local testing (IAM auth not available)")
            else:
                logger.info(f"[DEBUG] No gateway_id for {mcp.name}")

            logger.info(f"[DEBUG] Final config for {mcp.name}: {config}")
            return config

        # ExternalContainerMCP: Runtime URL 사용
        # 로컬 테스트에서는 IAM 인증 불가
        if isinstance(mcp, ExternalContainerMCP):
            if not mcp.runtime_url:
                logger.warning(f"ExternalContainerMCP {mcp.name} has no runtime_url (not deployed?)")
                return None

            return {
                "name": self._sanitize_name(mcp.name),
                "transport": "http",
                "url": mcp.runtime_url,
                "auth_type": "no_auth",  # 로컬 테스트에서는 IAM 인증 불가
            }

        # ExternalMCP (Legacy): stdio 방식 (Multi-MCP Proxy)
        # 로컬 테스트에서는 IAM 인증 불가
        if isinstance(mcp, ExternalMCP):
            # mcp_config에서 command, args 추출
            if mcp.command:
                return {
                    "name": mcp.server_name or self._sanitize_name(mcp.name),
                    "transport": "stdio",
                    "command": mcp.command,
                    "args": mcp.args or [],
                }
            # Runtime URL이 있으면 HTTP 방식
            elif mcp.runtime_url:
                return {
                    "name": mcp.server_name or self._sanitize_name(mcp.name),
                    "transport": "http",
                    "url": mcp.runtime_url,
                    "auth_type": "no_auth",  # 로컬 테스트에서는 IAM 인증 불가
                }
            else:
                logger.warning(f"ExternalMCP {mcp.name} has no command or runtime_url")
                return None

        # InternalDeployMCP: Gateway endpoint 사용 (IAM 인증)
        # Agent → Gateway: IAM 인증 (inbound)
        # Gateway → Runtime: Cognito JWT (outbound, Gateway가 내부적으로 처리)
        if isinstance(mcp, InternalDeployMCP):
            if not mcp.endpoint:
                logger.warning(f"InternalDeployMCP {mcp.name} has no endpoint (gateway not created?)")
                return None

            logger.info(f"InternalDeployMCP {mcp.name} uses Gateway endpoint with IAM auth")
            return {
                "name": self._sanitize_name(mcp.name),
                "transport": "http",
                "url": mcp.endpoint,
                "auth_type": "iam",  # Gateway inbound는 IAM 인증
            }

        # InternalCreateMCP: Gateway endpoint 사용 (IAM 인증)
        # Agent → Gateway: IAM 인증 (inbound)
        if isinstance(mcp, InternalCreateMCP):
            if not mcp.endpoint:
                logger.warning(f"InternalCreateMCP {mcp.name} has no endpoint (gateway not created?)")
                return None

            logger.info(f"InternalCreateMCP {mcp.name} uses Gateway endpoint with IAM auth (SigV4)")
            return {
                "name": self._sanitize_name(mcp.name),
                "transport": "http",
                "url": mcp.endpoint,
                "auth_type": "iam",  # Gateway는 IAM 인증 필요
            }

        logger.warning(f"Unknown MCP type: {type(mcp).__name__}")
        return None

    def _sanitize_name(self, name: str) -> str:
        """MCP 이름을 Python 변수명으로 사용 가능하도록 정제

        Jinja2 템플릿에서 _mcp_{{ server.name }}로 변수명 생성하므로
        공백, 특수문자를 언더스코어로 치환
        """
        import re
        # 알파벳, 숫자, 언더스코어만 허용
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        # 숫자로 시작하면 앞에 언더스코어 추가
        if sanitized and sanitized[0].isdigit():
            sanitized = '_' + sanitized
        return sanitized.lower()

    def get_agent(self, session_id: str) -> Optional[Agent]:
        """세션 ID로 Agent 조회 (활동 시간 갱신)"""
        if session_id in self._sessions:
            self._last_activity[session_id] = datetime.now()
            return self._sessions[session_id]
        return None

    def cleanup_session(self, session_id: str):
        """세션 정리"""
        if session_id in self._sessions:
            del self._sessions[session_id]
        if session_id in self._last_activity:
            del self._last_activity[session_id]

        # 사용자-세션 매핑에서도 제거
        for user_id, sid in list(self._user_sessions.items()):
            if sid == session_id:
                del self._user_sessions[user_id]
                break

        logger.info(f"Session cleaned up: {session_id}")

    def cleanup_expired_sessions(self, timeout_minutes: int = 30):
        """만료된 세션 자동 정리"""
        now = datetime.now()
        expired_sessions = []

        for session_id, last_activity in self._last_activity.items():
            if now - last_activity > timedelta(minutes=timeout_minutes):
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            logger.info(f"Cleaning up expired session: {session_id}")
            self.cleanup_session(session_id)

        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")


# 싱글톤 인스턴스
local_agent_runner = LocalAgentRunner()
