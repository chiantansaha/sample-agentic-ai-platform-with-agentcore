"""로컬에서 Strands Agent를 실행하는 모듈"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional
from strands import Agent
from app.playground.infrastructure.code_generator.agent_code_generator import AgentCodeGenerator

logger = logging.getLogger(__name__)

class LocalAgentRunner:
    """로컬 Agent 실행 및 관리"""
    
    def __init__(self):
        self._sessions: Dict[str, Agent] = {}
        self._last_activity: Dict[str, datetime] = {}
        self.code_generator = AgentCodeGenerator()
    
    def create_agent(
        self,
        agent_id: str,
        user_id: str,
        system_prompt: str,
        model: str,
        mcp_ids: list[str],
        kb_ids: list[str]
    ) -> str:
        """Agent 생성 및 세션 ID 반환"""
        session_id = f"local-{user_id}-{agent_id}-{uuid.uuid4().hex[:8]}"
        
        # Agent 설정
        agent_config = {
            "agent_id": agent_id,
            "agent_name": f"local-agent-{agent_id}",
            "version": "local",
            "model_id": model,
            "system_prompt": system_prompt,
            "temperature": 0.7,
            "max_tokens": 2000,
            "knowledge_bases": [{"id": kb_id} for kb_id in kb_ids],
            "mcp_servers": self._get_mcp_configs(mcp_ids),
            "tools": []
        }
        
        # Jinja2 템플릿으로 코드 생성
        generated_files = self.code_generator.generate(
            agent_config=agent_config,
            session_bucket=None,
            session_prefix=None,
            local_testing=True
        )
        
        # Agent 인스턴스 생성
        agent = self._load_agent_from_code(generated_files["agent.py"])
        
        # 세션 저장
        self._sessions[session_id] = agent
        self._last_activity[session_id] = datetime.now()
        
        logger.info(f"Local agent created: {session_id}")
        return session_id
    
    def _load_agent_from_code(self, agent_code: str) -> Agent:
        """생성된 코드에서 Agent 인스턴스 추출"""
        namespace = {}
        exec(agent_code, namespace)
        
        get_or_create_agent = namespace.get("get_or_create_agent")
        if not get_or_create_agent:
            raise ValueError("get_or_create_agent function not found")
        
        return get_or_create_agent(session_id=None)
    
    def _get_mcp_configs(self, mcp_ids: list[str]) -> list[dict]:
        """MCP ID로부터 MCP 설정 조회"""
        # TODO: DynamoDB에서 MCP 정보 조회
        return []
    
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
        logger.info(f"Session cleaned up: {session_id}")
    
    def cleanup_agent_sessions(self, agent_id: str) -> int:
        """특정 Agent의 모든 로컬 세션 정리"""
        sessions_to_remove = []
        
        for session_id in self._sessions.keys():
            # session_id 형식: "local-{user_id}-{agent_id}-{uuid}"
            if f"-{agent_id}-" in session_id:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            logger.info(f"Cleaning up session for updated agent {agent_id}: {session_id}")
            self.cleanup_session(session_id)
        
        return len(sessions_to_remove)
    
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

# 싱글톤 인스턴스
local_agent_runner = LocalAgentRunner()
