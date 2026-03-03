"""Agent Version Service (Domain Service)"""
import uuid

from app.shared.utils.timestamp import now_timestamp
from ..entities import Agent
from ..entities.agent_version import AgentVersion
from ..repositories.agent_version_repository import AgentVersionRepository


class AgentVersionService:
    """Agent 버전 관리 도메인 서비스"""
    
    def __init__(self, version_repository: AgentVersionRepository):
        self.version_repository = version_repository
    
    async def create_new_version(self, agent: Agent, change_log: str, deployed_by: str) -> AgentVersion:
        """Agent 수정 시 자동으로 새 버전 생성"""
        # 새 버전 번호 생성 (마이너 버전 증가)
        new_version = agent.current_version.increment_minor()
        
        # Agent 스냅샷 생성
        snapshot = {
            "llm_model": {
                "model_id": agent.llm_model.model_id,
                "model_name": agent.llm_model.model_name,
                "provider": agent.llm_model.provider
            },
            "instruction": {
                "system_prompt": agent.instruction.system_prompt,
                "temperature": agent.instruction.temperature,
                "max_tokens": agent.instruction.max_tokens
            },
            "knowledge_bases": agent.knowledge_bases,
            "mcps": agent.mcps
        }
        
        # AgentVersion 엔티티 생성
        version = AgentVersion(
            id=str(uuid.uuid4()),
            agent_id=agent.id.value,
            version=new_version,
            change_log=change_log,
            snapshot=snapshot,
            deployed_by=deployed_by,
            deployed_at=now_timestamp()
        )
        
        # 버전 저장
        await self.version_repository.save(version)
        
        # Agent의 현재 버전 업데이트
        agent.increment_version(new_version)
        
        return version
    
    async def get_version_history(self, agent_id: str):
        """Agent 버전 히스토리 조회"""
        return await self.version_repository.find_by_agent_id(agent_id)
