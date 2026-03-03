"""Mock Agent Repository for Demo Mode"""
from typing import Optional, List, Tuple, Dict, Any

from app.shared.mock_data import MOCK_AGENTS
from ...domain.repositories import AgentRepository
from ...domain.entities import Agent
from ...domain.value_objects import AgentId, LLMModel, Instruction, Version, AgentStatus


class MockAgentRepository(AgentRepository):
    """Mock Agent Repository - 메모리 기반 데모용 구현"""

    def __init__(self):
        # Mock 데이터를 메모리에 로드
        self._agents: Dict[str, Agent] = {}
        for agent_data in MOCK_AGENTS:
            agent = self._dict_to_agent(agent_data)
            self._agents[agent.id.value] = agent

    def _dict_to_agent(self, data: Dict[str, Any]) -> Agent:
        """Dict -> Agent Entity 변환"""
        llm_data = data["llm_model"]
        instruction_data = data["instruction"]

        return Agent(
            id=AgentId(data["id"]),
            name=data["name"],
            description=data["description"],
            llm_model=LLMModel(
                model_id=llm_data["model_id"],
                model_name=llm_data["model_name"],
                provider=llm_data["provider"]
            ),
            instruction=Instruction(
                system_prompt=instruction_data["system_prompt"],
                temperature=instruction_data["temperature"],
                max_tokens=instruction_data["max_tokens"]
            ),
            knowledge_bases=data.get("knowledge_bases", []),
            mcps=data.get("mcps", []),
            status=AgentStatus(data["status"]),
            current_version=Version.from_string(data["current_version"]),
            team_tags=data.get("team_tags", []),
            created_at=data.get("created_at", 0),
            updated_at=data.get("updated_at", 0),
            created_by=data.get("created_by", "demo-user"),
            updated_by=data.get("updated_by", "demo-user")
        )

    async def save(self, agent: Agent) -> Agent:
        """Agent 저장"""
        self._agents[agent.id.value] = agent
        return agent

    async def find_by_id(self, agent_id: str) -> Optional[Agent]:
        """ID로 Agent 조회"""
        return self._agents.get(agent_id)

    def find_all(self, page: int = 1, page_size: int = 20, status: str = None) -> Tuple[List[Agent], int]:
        """Agent 목록 조회 (페이징)"""
        agents = list(self._agents.values())

        # Status 필터
        if status:
            agents = [a for a in agents if a.status.value == status]

        total = len(agents)

        # 페이징
        start = (page - 1) * page_size
        end = start + page_size
        paged_agents = agents[start:end]

        return paged_agents, total

    async def find_enabled_agents(self) -> List[Agent]:
        """활성화된 Agent 목록 조회"""
        return [a for a in self._agents.values() if a.status == AgentStatus.ENABLED]
