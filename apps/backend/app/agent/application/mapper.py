"""DTO Mapper"""
from ..domain.entities import Agent
from ..domain.value_objects import AgentId, LLMModel, Instruction
from ..dto.request import CreateAgentRequest
from ..dto.response import AgentResponse, ResourceInfo


class AgentMapper:
    """Agent DTO Mapper"""

    @staticmethod
    def to_entity(request: CreateAgentRequest, user_id: str) -> Agent:
        """Request DTO → Domain Entity"""
        return Agent(
            id=AgentId.generate(),
            name=request.name,
            description=request.description,
            llm_model=LLMModel(
                model_id=request.llm_model_id,
                model_name=request.llm_model_name,
                provider=request.llm_provider
            ),
            instruction=Instruction(
                system_prompt=request.system_prompt,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            ),
            knowledge_bases=request.knowledge_bases or [],
            mcps=request.mcps or [],
            team_tags=request.team_tags or [],
            created_by=user_id,
            updated_by=user_id
        )

    @staticmethod
    def to_response(agent: Agent) -> AgentResponse:
        """Domain Entity → Response DTO

        Note: mcps, knowledge_bases는 ID만 담긴 ResourceInfo로 초기화됨.
        service.py의 get_agent()에서 이름 조회 후 덮어씀.
        """
        # string ID를 ResourceInfo 객체로 변환 (이름은 service에서 채움)
        mcps_info = [
            ResourceInfo(id=mcp_id, name=mcp_id)
            for mcp_id in (agent.mcps or [])
        ]
        kbs_info = [
            ResourceInfo(id=kb_id, name=kb_id)
            for kb_id in (agent.knowledge_bases or [])
        ]

        return AgentResponse(
            id=agent.id.value,
            name=agent.name,
            description=agent.description,
            llm_model={
                "model_id": agent.llm_model.model_id,
                "model_name": agent.llm_model.model_name,
                "provider": agent.llm_model.provider
            },
            instruction={
                "system_prompt": agent.instruction.system_prompt,
                "temperature": agent.instruction.temperature,
                "max_tokens": agent.instruction.max_tokens
            },
            knowledge_bases=kbs_info,
            mcps=mcps_info,
            status=agent.status.value,
            current_version=str(agent.current_version),
            team_tags=agent.team_tags,
            created_at=agent.created_at,
            updated_at=agent.updated_at
        )
