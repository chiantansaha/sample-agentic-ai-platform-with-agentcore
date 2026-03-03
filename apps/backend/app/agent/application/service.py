"""Agent Application Service"""
import asyncio
import logging
from typing import List

from ..domain.repositories import AgentRepository
from ..domain.repositories.agent_version_repository import AgentVersionRepository
from ..domain.services.agent_version_service import AgentVersionService
from ..domain.value_objects import LLMModel, Instruction
from ..dto.request import CreateAgentRequest, UpdateAgentRequest
from ..dto.response import AgentResponse, AgentListResponse, ResourceInfo
from .mapper import AgentMapper
from ..exception.exceptions import AgentNotFoundException

from app.config import settings

logger = logging.getLogger(__name__)


class AgentApplicationService:
    """Agent Use Cases"""
    
    def __init__(self, agent_repository: AgentRepository, version_repository: AgentVersionRepository = None):
        self.agent_repository = agent_repository
        self.version_repository = version_repository
        self.version_service = AgentVersionService(version_repository) if version_repository else None
        self.mapper = AgentMapper()
    
    async def create_agent(self, request: CreateAgentRequest, user_id: str) -> AgentResponse:
        """Agent 생성"""
        agent = self.mapper.to_entity(request, user_id)
        saved_agent = await self.agent_repository.save(agent)

        # 초기 버전 생성
        if self.version_service:
            await self.version_service.create_new_version(saved_agent, "Initial version", user_id)
            await self.agent_repository.save(saved_agent)  # 버전 업데이트 반영

        # 비동기로 이미지 빌드 트리거 (Playground에서 재사용 가능하도록)
        version_str = str(saved_agent.current_version)
        asyncio.create_task(
            self._trigger_background_build(
                agent_id=saved_agent.id.value,
                version=version_str,
                user_id=user_id,
            )
        )
        logger.info(f"Background build triggered for new agent {saved_agent.id.value} version {version_str}")

        return self.mapper.to_response(saved_agent)
    
    async def get_agent(self, agent_id: str) -> AgentResponse:
        """Agent 상세 조회"""
        agent = await self.agent_repository.find_by_id(agent_id)
        if not agent:
            raise AgentNotFoundException(agent_id)
        
        response = self.mapper.to_response(agent)
        
        # MCP와 KB 상세 정보 추가
        try:
            import boto3

            # boto3 Session을 사용하여 AWS_PROFILE 적용
            if settings.AWS_PROFILE:
                session = boto3.Session(profile_name=settings.AWS_PROFILE, region_name=settings.AWS_REGION)
                dynamodb = session.resource('dynamodb')
            else:
                dynamodb = boto3.resource('dynamodb', region_name=settings.AWS_REGION)

            # MCP 정보 조회 (MCP 테이블은 'id'를 primary key로 사용)
            if agent.mcps:
                mcp_table = dynamodb.Table(settings.DYNAMODB_MCP_TABLE)
                mcps_with_names = []
                for mcp_id in agent.mcps:
                    try:
                        mcp_response = mcp_table.get_item(Key={'id': mcp_id})
                        if 'Item' in mcp_response:
                            mcps_with_names.append(ResourceInfo(
                                id=mcp_id,
                                name=mcp_response['Item'].get('name', mcp_id)
                            ))
                        else:
                            mcps_with_names.append(ResourceInfo(id=mcp_id, name=mcp_id))
                    except Exception as e:
                        print(f"⚠️ Failed to fetch MCP {mcp_id}: {e}")
                        mcps_with_names.append(ResourceInfo(id=mcp_id, name=mcp_id))
                response.mcps = mcps_with_names

            # KB 정보 조회 (KB 테이블은 PK/SK 패턴 사용)
            if agent.knowledge_bases:
                kb_table = dynamodb.Table(settings.DYNAMODB_KB_TABLE)
                kbs_with_names = []
                for kb_id in agent.knowledge_bases:
                    try:
                        kb_response = kb_table.get_item(Key={'PK': f'KB#{kb_id}', 'SK': 'METADATA'})
                        if 'Item' in kb_response:
                            kbs_with_names.append(ResourceInfo(
                                id=kb_id,
                                name=kb_response['Item'].get('Name', kb_id)
                            ))
                        else:
                            kbs_with_names.append(ResourceInfo(id=kb_id, name=kb_id))
                    except Exception as e:
                        print(f"⚠️ Failed to fetch KB {kb_id}: {e}")
                        kbs_with_names.append(ResourceInfo(id=kb_id, name=kb_id))
                response.knowledge_bases = kbs_with_names
        except Exception as e:
            print(f"⚠️ Failed to fetch resource names: {e}")
        
        return response
    
    async def list_agents(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str = None,
        status: str = None,
        team_tags: List[str] = None
    ) -> AgentListResponse:
        """Agent 목록 조회 (검색, 상태, 팀 태그 필터 지원) - 성능 최적화 버전"""

        # 1. Repository에서 status 필터링 (GSI 활용)
        agents, total = self.agent_repository.find_all(page=1, page_size=1000, status=status)

        # 2. 나머지 필터링은 메모리에서 처리 (검색, 팀 태그)
        filtered_agents = agents

        if search:
            search_lower = search.lower()
            filtered_agents = [
                a for a in filtered_agents
                if search_lower in a.name.lower() or
                   (a.description and search_lower in a.description.lower())
            ]

        if team_tags:
            filtered_agents = [
                a for a in filtered_agents
                if any(tag in a.team_tags for tag in team_tags)
            ]

        # 3. 페이지네이션 적용
        total_filtered = len(filtered_agents)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_agents = filtered_agents[start:end]

        return AgentListResponse(
            items=[self.mapper.to_response(a) for a in paginated_agents],
            total=total_filtered,
            page=page,
            page_size=page_size
        )
    
    async def update_agent(self, agent_id: str, request: UpdateAgentRequest, user_id: str) -> AgentResponse:
        """Agent 수정 (자동 버전 생성)"""
        agent = await self.agent_repository.find_by_id(agent_id)
        if not agent:
            raise AgentNotFoundException(agent_id)

        # 변경 내역 감지
        changes = []

        # Description 변경
        if agent.description != request.description:
            changes.append(f"Description updated")

        # LLM Model 변경
        if agent.llm_model.model_id != request.llm_model_id:
            changes.append(f"LLM model changed: {agent.llm_model.model_name} → {request.llm_model_name}")

        # System Prompt 변경
        if agent.instruction.system_prompt != request.system_prompt:
            changes.append(f"System prompt updated")

        # Temperature 변경
        if agent.instruction.temperature != request.temperature:
            changes.append(f"Temperature changed: {agent.instruction.temperature} → {request.temperature}")

        # Max Tokens 변경
        if agent.instruction.max_tokens != request.max_tokens:
            changes.append(f"Max tokens changed: {agent.instruction.max_tokens} → {request.max_tokens}")

        # Knowledge Bases 변경
        old_kbs = set(agent.knowledge_bases or [])
        new_kbs = set(request.knowledge_bases or [])
        if old_kbs != new_kbs:
            added_kbs = new_kbs - old_kbs
            removed_kbs = old_kbs - new_kbs
            if added_kbs:
                changes.append(f"Added {len(added_kbs)} knowledge base(s)")
            if removed_kbs:
                changes.append(f"Removed {len(removed_kbs)} knowledge base(s)")

        # MCPs 변경
        old_mcps = set(agent.mcps or [])
        new_mcps = set(request.mcps or [])
        if old_mcps != new_mcps:
            added_mcps = new_mcps - old_mcps
            removed_mcps = old_mcps - new_mcps
            if added_mcps:
                changes.append(f"Added {len(added_mcps)} MCP(s)")
            if removed_mcps:
                changes.append(f"Removed {len(removed_mcps)} MCP(s)")

        # Team Tags 변경
        old_tags = set(agent.team_tags or [])
        new_tags = set(request.team_tags or [])
        if old_tags != new_tags:
            added_tags = new_tags - old_tags
            removed_tags = old_tags - new_tags
            if added_tags:
                changes.append(f"Added {len(added_tags)} team tag(s)")
            if removed_tags:
                changes.append(f"Removed {len(removed_tags)} team tag(s)")

        # Change log 생성
        change_log = "; ".join(changes) if changes else "Updated agent configuration"

        agent.update(
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
            knowledge_bases=request.knowledge_bases,
            mcps=request.mcps,
            team_tags=request.team_tags,
            updated_by=user_id
        )

        # 새 버전 생성
        if self.version_service:
            await self.version_service.create_new_version(agent, change_log, user_id)

        updated_agent = await self.agent_repository.save(agent)

        # 변경사항이 있으면 비동기로 이미지 빌드 트리거 (Playground에서 재사용 가능하도록)
        if changes:
            version_str = str(updated_agent.current_version)
            asyncio.create_task(
                self._trigger_background_build(
                    agent_id=agent_id,
                    version=version_str,
                    user_id=user_id,
                )
            )
            logger.info(f"Background build triggered for agent {agent_id} version {version_str}")

        return self.mapper.to_response(updated_agent)

    async def _trigger_background_build(self, agent_id: str, version: str, user_id: str):
        """백그라운드에서 Agent 이미지 빌드

        Save 버튼 클릭 시 비동기로 실행되어 사용자는 대기하지 않아도 됨.
        빌드된 이미지는 Playground에서 재사용 가능.
        """
        try:
            from app.playground.application.service import DeploymentService
            from app.agent.infrastructure.repositories.dynamodb_agent_repository import DynamoDBAgentRepository
            from app.knowledge_bases.infrastructure.repositories.dynamodb_kb_repository import DynamoDBKBRepository
            from app.playground.infrastructure.clients.agentcore_client import AgentCoreClient
            from app.playground.infrastructure.code_generator.agent_code_generator import AgentCodeGenerator
            from app.playground.infrastructure.repositories.dynamodb_deployment_repository import DynamoDBDeploymentRepository
            from app.playground.infrastructure.repositories.dynamodb_conversation_repository import DynamoDBConversationRepository

            # 서비스 초기화
            deployment_repo = DynamoDBDeploymentRepository()
            conversation_repo = DynamoDBConversationRepository()
            agent_repo = DynamoDBAgentRepository()
            kb_repo = DynamoDBKBRepository()
            agentcore_client = AgentCoreClient()
            code_generator = AgentCodeGenerator()

            deployment_service = DeploymentService(
                deployment_repository=deployment_repo,
                conversation_repository=conversation_repo,
                agent_repository=agent_repo,
                kb_repository=kb_repo,
                agentcore_client=agentcore_client,
                code_generator=code_generator,
            )

            # 이미지만 빌드 (Runtime 생성은 하지 않음)
            container_uri = await deployment_service.build_agent_image_only(
                agent_id=agent_id,
                version=version,
                user_id=user_id,
            )

            if container_uri:
                logger.info(f"Background build completed for agent {agent_id} version {version}: {container_uri}")
            else:
                logger.warning(f"Background build returned None for agent {agent_id} version {version}")

        except Exception as e:
            logger.error(f"Background build failed for agent {agent_id}: {e}")
            # 빌드 실패해도 사용자에게 에러를 표시하지 않음 (비동기 작업)
    
    async def change_agent_status(self, agent_id: str, enabled: bool) -> AgentResponse:
        """Agent 상태 변경"""
        agent = await self.agent_repository.find_by_id(agent_id)
        if not agent:
            raise AgentNotFoundException(agent_id)
        
        if enabled:
            agent.enable()
        else:
            agent.disable()
        
        updated_agent = await self.agent_repository.save(agent)
        return self.mapper.to_response(updated_agent)
    
    async def get_version_history(self, agent_id: str):
        """Agent 버전 히스토리 조회"""
        if not self.version_service:
            return []
        return await self.version_service.get_version_history(agent_id)

    async def get_agent_stats(self) -> dict:
        """Agent 통계 조회 (Dashboard용)

        Returns:
            dict: {
                'total': int - 저장된 Agent 수 (draft 제외),
                'enabled': int - 활성화된 Agent 수,
                'production': int - Production 상태 Agent 수
            }
        """
        # 전체 Agent 조회
        all_agents, _ = self.agent_repository.find_all(page=1, page_size=10000)

        # draft 제외한 Agent만 필터링 (enabled, disabled, production만 포함)
        saved_agents = [a for a in all_agents if a.status.value != 'draft']

        # enabled 상태 Agent 수
        enabled_count = sum(1 for agent in saved_agents if agent.status.value == 'enabled')

        # production 상태 Agent 수
        production_count = sum(1 for agent in saved_agents if agent.status.value == 'production')

        return {
            "total": len(saved_agents),
            "enabled": enabled_count,
            "production": production_count
        }
